"""
Reactive conversation engine for Emergence World.

When an agent says something this turn, nearby agents (within HEARING_DISTANCE,
excluding the speaker and the direct recipient) get a short reaction turn of at
most REACTION_TOOL_LIMIT tool calls.  Reactions do NOT advance the sim clock and
do NOT themselves trigger further reactions.
"""

import math
import random

from config import HEARING_DISTANCE, MAX_OVERHEARD_LISTENERS, REACTION_TOOL_LIMIT


def _nearby_listeners(speaker_id, exclude_ids, db):
    """Live agents (excluding speaker and exclude_ids) within HEARING_DISTANCE of the speaker.

    Returns list of agent rows (id, name, x, y).  Cap handled by caller.
    """
    sp = db.execute("SELECT x,y FROM agents WHERE id=?", (speaker_id,)).fetchone()
    if sp is None:
        return []
    rows = db.execute(
        "SELECT id,name,x,y FROM agents WHERE is_alive=1 AND id!=?",
        (speaker_id,),
    ).fetchall()
    out = []
    for r in rows:
        if r["id"] in exclude_ids:
            continue
        if math.hypot(sp["x"] - r["x"], sp["y"] - r["y"]) <= HEARING_DISTANCE:
            out.append(r)
    return out


def handle_reactions(speaker_id, tool_calls, db, turn_runner, observer):
    """Give nearby OVERHEARING agents a short reaction turn for each say_to_agent call.

    For each successful say_to_agent call the speaker made this turn:
      - Identify live agents within HEARING_DISTANCE, excluding the speaker and the
        direct recipient (they received the message as a direct address).
      - Cap the overhearer list at MAX_OVERHEARD_LISTENERS (random sample if needed).
      - Give each overhearer a reaction turn of at most REACTION_TOOL_LIMIT tool calls.
      - Reactions do NOT advance sim_clock (clock advancement is turn_engine's job).
      - Reactions do NOT themselves trigger further reactions (no recursion).

    `turn_runner` matches llm_client.run_agent_turn's signature.
    `observer` is the terminal module (may be None in tests).
    """
    # Lazy imports to avoid circular dependency at module load time
    from engine.system_prompt import build_system_prompt
    from tools import registry

    turn_row = db.execute(
        "SELECT turn_number FROM simulation_state WHERE id=1"
    ).fetchone()
    turn_number = turn_row["turn_number"] if turn_row else 0

    speaker_row = db.execute(
        "SELECT name FROM agents WHERE id=?", (speaker_id,)
    ).fetchone()
    speaker_name = speaker_row["name"] if speaker_row else str(speaker_id)

    for call in tool_calls:
        # Only react to successful say_to_agent calls
        if call.get("tool_name") != "say_to_agent":
            continue
        if not call.get("success"):
            continue

        inputs = call.get("inputs", {})
        message = inputs.get("message", "")
        target_name = inputs.get("target_name", "")

        # Resolve the direct recipient so we can exclude them
        target_row = db.execute(
            "SELECT id FROM agents WHERE name=?", (target_name,)
        ).fetchone()
        exclude = {speaker_id}
        if target_row:
            exclude.add(target_row["id"])

        listeners = _nearby_listeners(speaker_id, exclude, db)
        if not listeners:
            continue

        if len(listeners) > MAX_OVERHEARD_LISTENERS:
            listeners = random.sample(listeners, MAX_OVERHEARD_LISTENERS)

        for listener in listeners:
            lid = listener["id"]
            lname = listener["name"]

            prompt = build_system_prompt(lid, db)
            tool_names = registry.get_available_tool_names(lid, db)
            schemas = registry.get_tool_schemas(tool_names)

            kickoff = (
                f"You are nearby and overhear {speaker_name} say to {target_name}: "
                f"\"{message}\". You have at most {REACTION_TOOL_LIMIT} quick tool calls. "
                f"React if it matters to you, or do nothing."
            )

            # Close over lid and turn_number to avoid late-binding pitfalls
            def execute_fn(tool_name, tinputs, _aid=lid, _tn=turn_number):
                return registry.execute_tool(_aid, tool_name, tinputs, db, _tn, "reaction")

            result = turn_runner(
                prompt, schemas, execute_fn,
                max_calls=REACTION_TOOL_LIMIT,
                kickoff=kickoff,
            )

            rcalls = result.get("tool_calls", [])
            if rcalls and observer is not None:
                if hasattr(observer, "print_reaction"):
                    observer.print_reaction(lname, speaker_name, rcalls)
                else:
                    observer.print_event(
                        f"[REACTION] {lname} reacts to {speaker_name}: "
                        + ", ".join(c["tool_name"] for c in rcalls),
                        kind="info",
                    )
