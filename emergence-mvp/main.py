import sys
import os
import argparse

sys.stdout.reconfigure(encoding="utf-8")  # Windows-safe unicode
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _dry_run_runner():
    """A scripted fake turn_runner that needs no API key. Each agent navigates
    toward a landmark and occasionally speaks, so the full pipeline (prompt build,
    tool execution, observer rendering, clock advance, pitch settlement, reactive
    hook) can be smoke-tested offline. Inputs are parsed from the system prompt's
    agent name so behavior varies per agent."""
    import random
    destinations = ["Town Hall", "Victory Arch", "Bean & Brew", "Agent Billboard", "Central Plaza"]

    def fake(system_prompt, tool_schemas, execute_fn, max_calls=None, kickoff=None, **kw):
        name = system_prompt.split("\n", 1)[0].replace("You are ", "").strip(" .")
        tool_calls = []
        # Move somewhere
        dest = random.choice(destinations)
        ok, res = execute_fn("go_to_place", {"landmark_name": dest})
        tool_calls.append({"tool_name": "go_to_place", "inputs": {"landmark_name": dest}, "success": ok, "result": res})
        # Sometimes recharge if at Bean & Brew, sometimes record a memory
        if dest == "Bean & Brew":
            ok, res = execute_fn("recharge_energy", {})
            tool_calls.append({"tool_name": "recharge_energy", "inputs": {}, "success": ok, "result": res})
        else:
            note = f"{name} considered the state of the world at {dest}."
            ok, res = execute_fn("add_to_longterm_memory", {"content": note})
            tool_calls.append({"tool_name": "add_to_longterm_memory", "inputs": {"content": note}, "success": ok, "result": res})
        return {"tool_calls": tool_calls, "final_text": f"({name} dry-run action)", "stop_reason": "no_tool_use", "error": None}

    return fake


def main():
    p = argparse.ArgumentParser(description="Run the Emergence World MVP simulation.")
    p.add_argument("--turns", type=int, default=12, help="number of agent turns to run")
    p.add_argument("--fresh", action="store_true", help="re-seed the database before running")
    p.add_argument("--no-sleep", action="store_true", help="disable the real-time pause between turns")
    p.add_argument("--dry-run", action="store_true",
                   help="run with a scripted fake LLM (no API key) to smoke-test the pipeline and observer")
    p.add_argument("--scenario", default=None,
                   help="apply an experiment preset (see scenarios.py). Implies a fresh re-seed.")
    p.add_argument("--log", nargs="?", const="__auto__", default=None,
                   help="save the run transcript. Bare --log auto-names runs/run-<timestamp>.txt; "
                        "or pass a path.")
    args = p.parse_args()

    # Scenario presets mutate config (must happen BEFORE engine modules import).
    seed_overrides = {}
    if args.scenario:
        from scenarios import apply_scenario
        seed_overrides = apply_scenario(args.scenario)
        print(f"Scenario: {args.scenario}")

    # A scenario carries seed overrides, so it implies a fresh seed.
    if args.fresh or args.scenario:
        from db.seed import seed
        seed(seed_overrides)

    if args.dry_run:
        print("Provider: dry-run (scripted fake LLM, no API calls)")
        runner = _dry_run_runner()
    else:
        from agents.llm_client import active_provider_label
        print(f"Provider: {active_provider_label()}")
        runner = None

    # Optional transcript logging via the observer's rich console recorder.
    log_path = None
    if args.log is not None:
        from observer import terminal
        terminal.console.record = True
        if args.log == "__auto__":
            import datetime
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            log_path = os.path.join("runs", f"run-{stamp}.txt")
        else:
            log_path = args.log

    from engine.turn_engine import run_simulation
    run_simulation(args.turns, turn_runner=runner, sleep=not args.no_sleep)

    if log_path:
        from observer import terminal
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        terminal.console.save_text(log_path)
        print(f"Transcript saved to {log_path}")


if __name__ == "__main__":
    main()
