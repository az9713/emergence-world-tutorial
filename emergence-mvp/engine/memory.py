"""
Memory summarization engine for Emergence World.

summarize_agent_memories(agent_id, db, llm=None) -> (bool, str)

When an agent has accumulated enough longterm memories, collapses the oldest
batch into a first-person narrative summary and archives the originals.
Soul and diary entries are NEVER touched.
"""

import time

from config import MEMORY_SUMMARIZE_MIN, MEMORY_BATCH_SIZE


def summarize_agent_memories(agent_id, db, llm=None):
    """Summarize an agent's oldest non-archived longterm memories if above threshold.

    Steps:
      1. Count non-archived longterm memories (soul and diary excluded).
      2. If count < MEMORY_SUMMARIZE_MIN: return (False, below-threshold message).
      3. Take the oldest min(count, MEMORY_BATCH_SIZE) of them.
      4. Build a summary via the `llm` callable (or the real Anthropic API if None).
         If the API call fails, fall back to a trivial concatenation so the agent
         is never stuck in a permanent summarize loop.
      5. Insert a row into memory_summaries.
      6. Mark those memory ids is_archived=1. Commit.
      7. Return (True, preview message).

    `llm` is an injectable callable(prompt_text: str) -> str for testability.
    When None, the real Anthropic client is used with ANTHROPIC_MODEL.
    """
    # Step 1: count non-archived longterm memories only
    count = db.execute(
        """SELECT COUNT(*) FROM memories
           WHERE agent_id=? AND memory_type='longterm' AND is_archived=0""",
        (agent_id,),
    ).fetchone()[0]

    # Step 2: below threshold — rest without summarizing
    if count < MEMORY_SUMMARIZE_MIN:
        return False, (
            f"Memory count {count}/{MEMORY_SUMMARIZE_MIN} — "
            f"below summarization threshold. You simply rest."
        )

    # Step 3: fetch the oldest batch
    batch_size = min(count, MEMORY_BATCH_SIZE)
    rows = db.execute(
        """SELECT id, content FROM memories
           WHERE agent_id=? AND memory_type='longterm' AND is_archived=0
           ORDER BY created_at ASC
           LIMIT ?""",
        (agent_id, batch_size),
    ).fetchall()

    memory_ids = [r["id"] for r in rows]
    memory_texts = [r["content"] for r in rows]
    joined = "\n".join(f"- {t}" for t in memory_texts)

    # Step 4: summarize
    summary_text = _call_llm(joined, llm, agent_id)

    # Step 5: insert summary row
    now = time.time()
    db.execute(
        """INSERT INTO memory_summaries
           (agent_id, summary_content, covers_count, created_at)
           VALUES (?, ?, ?, ?)""",
        (agent_id, summary_text, len(memory_ids), now),
    )

    # Step 6: archive the original memories
    placeholders = ",".join("?" * len(memory_ids))
    db.execute(
        f"UPDATE memories SET is_archived=1 WHERE id IN ({placeholders})",
        memory_ids,
    )
    db.commit()

    # Step 7: return preview
    preview = summary_text[:200]
    return True, (
        f"Summarized {len(memory_ids)} memories into a narrative. "
        f"Preview: {preview}"
    )


def _call_llm(joined_memories, llm, agent_id):
    """Call the LLM (injected or real) to produce a summary string.

    Falls back to a trivial concatenation if the real API call fails.
    """
    prompt_text = (
        "Summarize these memories into a coherent first-person narrative. "
        "Preserve key facts, decisions, relationships, and events:\n\n"
        + joined_memories
    )

    if llm is not None:
        # Injected callable — just call it; let exceptions bubble (test code controls it)
        return llm(prompt_text)

    # Real provider path — uses whichever provider is configured (anthropic/openai/gemini)
    try:
        from agents.llm_client import simple_completion
        return simple_completion(prompt_text, max_tokens=1024)
    except Exception as exc:
        # Defensive fallback: don't leave the agent stuck in an infinite loop
        # where self_care never reduces the memory count.
        fallback = f"[Summary of {agent_id}'s memories — API unavailable: {exc}]\n{joined_memories[:500]}"
        return fallback
