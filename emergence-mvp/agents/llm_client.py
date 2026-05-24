"""
LLM client for Emergence World agents — multi-provider.

The foundation model is the only experimental variable in Emergence World, so this
module routes one public entry point — run_agent_turn — to a provider adapter chosen
by config.LLM_PROVIDER ("anthropic" | "openai" | "gemini").

- Anthropic uses the native `anthropic` SDK tool-use loop.
- OpenAI and Gemini share ONE adapter built on the `openai` SDK; Gemini is reached
  through its OpenAI-compatible endpoint (different base_url + api_key).

Every adapter returns the SAME dict shape:
  {"tool_calls":[{"tool_name","inputs","success","result"},...],
   "final_text": str, "stop_reason": "no_tool_use"|"max_calls"|"error", "error": str|None}
"""

import os
import json
import copy

from config import (
    LLM_PROVIDER, TURN_TOOL_LIMIT,
    ANTHROPIC_MODEL, OPENAI_MODEL, GEMINI_MODEL, GEMINI_BASE_URL,
)

try:
    import anthropic
except ImportError:
    anthropic = None

_anthropic_client = None

DEFAULT_KICKOFF = (
    "It is your turn to act in the world. Consider your current state, your goals, "
    "and the situation around you, then take action using your tools. When you are "
    "finished acting for this turn, stop calling tools."
)


def _err(message, tool_calls=None, final_text=""):
    return {
        "tool_calls": tool_calls or [],
        "final_text": final_text,
        "stop_reason": "error",
        "error": message,
    }


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

def get_client():
    """Lazily create and cache the Anthropic client. Raise a clear error if the
    package or API key is missing. (Kept as a stable entry point for callers that
    specifically want Anthropic.)"""
    global _anthropic_client
    if anthropic is None:
        raise RuntimeError("The 'anthropic' package is not installed. Run: pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


def _run_anthropic(system_prompt, tool_schemas, execute_fn, max_calls, kickoff, model, max_tokens):
    try:
        client = get_client()
    except RuntimeError as e:
        return _err(str(e))

    tool_calls, final_text, calls_made, stop_reason, error = [], "", 0, None, None
    messages = [{"role": "user", "content": kickoff}]

    while calls_made < max_calls:
        resp = None
        for attempt in range(2):
            try:
                resp = client.messages.create(
                    model=model, max_tokens=max_tokens, system=system_prompt,
                    tools=tool_schemas, messages=messages,
                )
                break
            except Exception as exc:
                if attempt == 0:
                    continue
                return _err(str(exc), tool_calls, final_text)

        iteration_text = "".join(b.text for b in resp.content if b.type == "text")
        if iteration_text:
            final_text = iteration_text

        tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
        if not tool_use_blocks:
            stop_reason = "no_tool_use"
            break

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in tool_use_blocks:
            if calls_made >= max_calls:
                break
            success, result = execute_fn(block.name, dict(block.input))
            calls_made += 1
            tool_calls.append({"tool_name": block.name, "inputs": dict(block.input),
                               "success": success, "result": str(result)})
            tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                 "content": str(result), "is_error": (not success)})
        messages.append({"role": "user", "content": tool_results})
        if calls_made >= max_calls:
            stop_reason = "max_calls"
            break

    return {"tool_calls": tool_calls, "final_text": final_text,
            "stop_reason": stop_reason or "max_calls", "error": error}


# ---------------------------------------------------------------------------
# OpenAI-compatible (serves both OpenAI and Gemini)
# ---------------------------------------------------------------------------

def _sanitize_schema(schema):
    """Strip JSON-schema keys some OpenAI-compatible endpoints (notably Gemini)
    reject — currently just 'default', which our tool functions handle themselves."""
    s = copy.deepcopy(schema)

    def _strip(node):
        if isinstance(node, dict):
            node.pop("default", None)
            for v in node.values():
                _strip(v)
        elif isinstance(node, list):
            for v in node:
                _strip(v)

    _strip(s)
    return s


def _to_openai_tools(tool_schemas):
    return [{"type": "function",
             "function": {"name": t["name"], "description": t["description"],
                          "parameters": _sanitize_schema(t["input_schema"])}}
            for t in tool_schemas]


def _openai_client(api_key, base_url):
    from openai import OpenAI  # imported lazily so the dep is optional
    return OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)


def _run_openai_compatible(system_prompt, tool_schemas, execute_fn, max_calls, kickoff,
                           model, max_tokens, api_key, base_url, key_name):
    try:
        import openai  # noqa: F401
    except ImportError:
        return _err("The 'openai' package is not installed. Run: pip install openai")
    if not api_key:
        return _err(f"{key_name} environment variable is not set.")

    client = _openai_client(api_key, base_url)
    oai_tools = _to_openai_tools(tool_schemas)
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": kickoff}]
    tool_calls, final_text, calls_made, stop_reason = [], "", 0, None

    while calls_made < max_calls:
        resp = None
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=model, messages=messages, tools=oai_tools,
                    tool_choice="auto", max_tokens=max_tokens,
                )
                break
            except Exception as exc:
                if attempt == 0:
                    continue
                return _err(str(exc), tool_calls, final_text)

        msg = resp.choices[0].message
        if msg.content:
            final_text = msg.content
        if not msg.tool_calls:
            stop_reason = "no_tool_use"
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name,
                                         "arguments": tc.function.arguments}}
                           for tc in msg.tool_calls],
        })
        for tc in msg.tool_calls:
            if calls_made >= max_calls:
                break
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            success, result = execute_fn(tc.function.name, args)
            calls_made += 1
            tool_calls.append({"tool_name": tc.function.name, "inputs": args,
                               "success": success, "result": str(result)})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
        if calls_made >= max_calls:
            stop_reason = "max_calls"
            break

    return {"tool_calls": tool_calls, "final_text": final_text,
            "stop_reason": stop_reason or "max_calls", "error": None}


# ---------------------------------------------------------------------------
# Public entry point — provider router
# ---------------------------------------------------------------------------

def run_agent_turn(system_prompt, tool_schemas, execute_fn, max_calls=None,
                   kickoff=None, model=None, max_tokens=1024, provider=None):
    """Run one agent turn via the configured provider's tool-use loop.

    execute_fn(tool_name, inputs) -> (success, result_str), bound by the caller.
    Returns the standard result dict (see module docstring)."""
    if max_calls is None:
        max_calls = TURN_TOOL_LIMIT
    if kickoff is None:
        kickoff = DEFAULT_KICKOFF
    provider = (provider or LLM_PROVIDER).strip().lower()

    if provider == "anthropic":
        return _run_anthropic(system_prompt, tool_schemas, execute_fn, max_calls,
                              kickoff, model or ANTHROPIC_MODEL, max_tokens)
    if provider == "openai":
        return _run_openai_compatible(system_prompt, tool_schemas, execute_fn, max_calls,
                                      kickoff, model or OPENAI_MODEL, max_tokens,
                                      api_key=os.environ.get("OPENAI_API_KEY"),
                                      base_url=None, key_name="OPENAI_API_KEY")
    if provider == "gemini":
        return _run_openai_compatible(system_prompt, tool_schemas, execute_fn, max_calls,
                                      kickoff, model or GEMINI_MODEL, max_tokens,
                                      api_key=os.environ.get("GEMINI_API_KEY"),
                                      base_url=GEMINI_BASE_URL, key_name="GEMINI_API_KEY")
    return _err(f"Unknown LLM_PROVIDER: {provider!r} (use anthropic | openai | gemini)")


def simple_completion(prompt_text, max_tokens=512, provider=None):
    """Single-shot text completion (no tools) using the active provider.
    Used by memory summarization. Raises RuntimeError on missing package/key."""
    provider = (provider or LLM_PROVIDER).strip().lower()
    if provider == "anthropic":
        client = get_client()
        resp = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=max_tokens,
                                       messages=[{"role": "user", "content": prompt_text}])
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

    if provider == "gemini":
        key, base, model = os.environ.get("GEMINI_API_KEY"), GEMINI_BASE_URL, GEMINI_MODEL
        key_name = "GEMINI_API_KEY"
    else:  # openai
        key, base, model = os.environ.get("OPENAI_API_KEY"), None, OPENAI_MODEL
        key_name = "OPENAI_API_KEY"
    if not key:
        raise RuntimeError(f"{key_name} environment variable is not set.")
    client = _openai_client(key, base)
    resp = client.chat.completions.create(model=model, max_tokens=max_tokens,
                                          messages=[{"role": "user", "content": prompt_text}])
    return resp.choices[0].message.content or ""


def active_provider_label():
    """Human-readable 'provider/model' for the active configuration."""
    p = LLM_PROVIDER
    model = {"anthropic": ANTHROPIC_MODEL, "openai": OPENAI_MODEL, "gemini": GEMINI_MODEL}.get(p, "?")
    return f"{p}/{model}"


if __name__ == "__main__":
    print("llm_client imported OK")
    print("active provider:", active_provider_label())
    # Verify unknown-provider routing returns a clean error dict (no API call).
    r = run_agent_turn("sys", [], lambda n, i: (True, "ok"), provider="bogus")
    print("unknown provider ->", r["stop_reason"], "|", r["error"])
