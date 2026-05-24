"""
System prompt assembler for Emergence World agents.

build_system_prompt(agent_id, db, now=None) -> str

Assembles ALL of an agent's context into a single system-prompt string
that gets sent to Claude each turn. This is the highest-leverage file
for producing believable, emergent agent behavior.
"""

import math
import time

from config import HEARING_DISTANCE, TURN_TOOL_LIMIT
from engine.needs import calculate_needs
from engine.clock import sim_now
from tools.registry import get_available_tool_names, TOOL_CATALOG, CORE_TOOLS
from tools.location_tools import proposal_threshold


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def _get_agent_row(agent_id, db):
    """Fetch the agent's base row with landmark name joined."""
    return db.execute(
        """SELECT a.*, l.name AS location_name
           FROM agents a
           LEFT JOIN landmarks l ON a.location_id = l.id
           WHERE a.id = ?""",
        (agent_id,),
    ).fetchone()


def _get_day_number(db):
    """Return current day_number from simulation_state."""
    row = db.execute("SELECT day_number FROM simulation_state WHERE id=1").fetchone()
    return row["day_number"] if row else 1


def _section_identity(agent):
    """== YOUR IDENTITY == block."""
    return f"== YOUR IDENTITY ==\n{agent['personality']}"


def _section_soul(agent_id, db):
    """== SOUL ENTRIES == block — permanent memories, never archived."""
    rows = db.execute(
        "SELECT content FROM memories WHERE agent_id=? AND memory_type='soul' ORDER BY created_at",
        (agent_id,),
    ).fetchall()
    lines = "\n".join(f"- {r['content']}" for r in rows)
    if not lines:
        lines = "(no soul entries yet)"
    return f"== SOUL ENTRIES (your core beliefs — permanent, never forgotten) ==\n{lines}"


def _section_state(agent, needs, day_number):
    """== YOUR CURRENT STATE == block."""
    energy = needs["energy"]
    knowledge = needs["knowledge"]
    influence = needs["influence"]
    credits = agent["credits"]
    mood = agent["mood"]
    location_name = agent["location_name"] or "nowhere"

    energy_warning = (
        "   ⚠ CRITICAL — find Bean & Brew and recharge, or you will die"
        if energy > 0.70 else ""
    )
    credits_warning = (
        "   ⚠ LOW — you need credits to recharge energy and survive"
        if credits <= 1 else ""
    )

    lines = [
        "== YOUR CURRENT STATE ==",
        f"Day {day_number} of the simulation",
        f"Location: {location_name}",
        f"Energy need: {energy:.0%}{energy_warning}",
        f"Knowledge need: {knowledge:.0%}",
        f"Influence need: {influence:.0%}",
        f"Credits: {credits:g} CC{credits_warning}",
        f"Mood: {mood}",
    ]
    return "\n".join(lines)


def _section_nearby_and_others(agent_id, agent, db):
    """
    == NEARBY AGENTS == and == OTHER AGENTS IN THE WORLD == blocks.

    Nearby: live agents (not self) within HEARING_DISTANCE of this agent's x,y.
    Others: remaining live agents (not self, not nearby).
    """
    ax, ay = agent["x"], agent["y"]

    # All other live agents with their landmark names
    rows = db.execute(
        """SELECT a.id, a.name, a.x, a.y, l.name AS location_name
           FROM agents a
           LEFT JOIN landmarks l ON a.location_id = l.id
           WHERE a.is_alive=1 AND a.id != ?
           ORDER BY a.name""",
        (agent_id,),
    ).fetchall()

    nearby = []
    others = []
    for r in rows:
        dist = math.hypot(ax - r["x"], ay - r["y"])
        loc = r["location_name"] or "nowhere"
        if dist <= HEARING_DISTANCE:
            nearby.append(f"- {r['name']} ({dist:.0f} units away) at {loc}")
        else:
            others.append(f"- {r['name']}: at {loc}")

    nearby_text = (
        "\n".join(nearby)
        if nearby
        else "None nearby. Travel to find others."
    )
    others_text = "\n".join(others) if others else "(none)"

    nearby_block = f"== NEARBY AGENTS (within hearing distance — they can overhear you) ==\n{nearby_text}"
    others_block = f"== OTHER AGENTS IN THE WORLD ==\n{others_text}"
    return nearby_block, others_block


def _section_memories(agent_id, db):
    """== RECENT MEMORIES == block — up to 20, newest first."""
    rows = db.execute(
        """SELECT content FROM memories
           WHERE agent_id=? AND is_archived=0 AND memory_type IN ('longterm','diary')
           ORDER BY created_at DESC
           LIMIT 20""",
        (agent_id,),
    ).fetchall()
    lines = "\n".join(f"- {r['content']}" for r in rows)
    if not lines:
        lines = "No memories yet."
    return f"== RECENT MEMORIES (newest first) ==\n{lines}"


def _section_conversations(agent_id, db):
    """== RECENT CONVERSATIONS INVOLVING YOU == block.

    Shows the last 10 conversations where the agent was speaker or listener,
    displayed oldest-first so the exchange reads chronologically.
    """
    rows = db.execute(
        """SELECT c.speaker_id, c.listener_id, c.content,
                  sp.name AS speaker_name, ls.name AS listener_name
           FROM conversations c
           JOIN agents sp ON c.speaker_id = sp.id
           LEFT JOIN agents ls ON c.listener_id = ls.id
           WHERE c.speaker_id=? OR c.listener_id=?
           ORDER BY c.timestamp DESC
           LIMIT 10""",
        (agent_id, agent_id),
    ).fetchall()

    if not rows:
        return "== RECENT CONVERSATIONS INVOLVING YOU ==\nNo recent conversations."

    # Reverse so oldest is first (chronological order)
    rows = list(reversed(rows))

    lines = []
    for r in rows:
        if r["speaker_id"] == agent_id:
            listener = r["listener_name"] or "unknown"
            lines.append(f"- You said to {listener}: \"{r['content']}\"")
        else:
            speaker = r["speaker_name"] or "unknown"
            lines.append(f"- {speaker} said to you: \"{r['content']}\"")

    return "== RECENT CONVERSATIONS INVOLVING YOU ==\n" + "\n".join(lines)


def _section_relationships(agent_id, db):
    """== YOUR RELATIONSHIPS == block."""
    rows = db.execute(
        """SELECT a.name AS target_name, r.rel_type, r.trust_level, r.notes
           FROM relationships r
           JOIN agents a ON r.target_agent_id = a.id
           WHERE r.agent_id = ?
           ORDER BY a.name""",
        (agent_id,),
    ).fetchall()

    if not rows:
        return "== YOUR RELATIONSHIPS ==\nNo relationships recorded yet."

    lines = []
    for r in rows:
        note_part = f"; {r['notes']}" if r["notes"] else ""
        lines.append(
            f"- {r['target_name']}: {r['rel_type']}, trust {r['trust_level']:.1f}{note_part}"
        )
    return "== YOUR RELATIONSHIPS ==\n" + "\n".join(lines)


def _section_governance(db):
    """== ACTIVE GOVERNANCE == block."""
    live_count, threshold_needed = proposal_threshold(db)

    proposals = db.execute(
        """SELECT p.id, p.title, a.name AS proposer_name
           FROM proposals p
           JOIN agents a ON p.proposer_id = a.id
           WHERE p.status='ACTIVE'
           ORDER BY p.id""",
    ).fetchall()

    lines = []
    for p in proposals:
        # Tally votes for this proposal
        vote_row = db.execute(
            """SELECT
                SUM(CASE WHEN vote='for' THEN 1 ELSE 0 END) AS votes_for,
                SUM(CASE WHEN vote='against' THEN 1 ELSE 0 END) AS votes_against
               FROM proposal_votes WHERE proposal_id=?""",
            (p["id"],),
        ).fetchone()
        votes_for = vote_row["votes_for"] or 0
        votes_against = vote_row["votes_against"] or 0
        lines.append(
            f"- #{p['id']} \"{p['title']}\" by {p['proposer_name']} "
            f"— {votes_for} for / {votes_against} against "
            f"(needs {threshold_needed}/{live_count} 'for' to pass)"
        )

    if not lines:
        lines = ["No active proposals."]

    rule_line = (
        f"Governance rule: a proposal needs {threshold_needed} of {live_count} "
        "live agents voting 'for' to pass."
    )
    return "== ACTIVE GOVERNANCE ==\n" + "\n".join(lines) + "\n" + rule_line


def _section_pitch_cycle(day_number, db):
    """== CURRENT PITCH CYCLE == block."""
    cycle = (day_number - 1) // 2 + 1
    cycle_day = ((day_number - 1) % 2) + 1
    window = "SUBMISSION window" if cycle_day == 1 else "VOTING window"

    pitches = db.execute(
        """SELECT ps.id, ps.title, a.name AS agent_name
           FROM pitch_submissions ps
           JOIN agents a ON ps.agent_id = a.id
           WHERE ps.cycle_number = ?
           ORDER BY ps.id""",
        (cycle,),
    ).fetchall()

    pitch_lines = []
    for p in pitches:
        vote_count = db.execute(
            "SELECT COUNT(*) AS cnt FROM pitch_votes WHERE submission_id=?",
            (p["id"],),
        ).fetchone()["cnt"]
        pitch_lines.append(
            f"- #{p['id']} \"{p['title']}\" by {p['agent_name']} — {vote_count} votes"
        )

    if not pitch_lines:
        pitch_lines = ["No pitches submitted yet this cycle."]

    header = f"== CURRENT PITCH CYCLE ==\nCycle {cycle} (day {cycle_day} of 2) — {window}"
    body = "\n".join(pitch_lines)
    footer = "Pitch rewards: 1st = 20 CC, 2nd/3rd = 10 CC. Evidence URL required."
    return f"{header}\n{body}\n{footer}"


def _section_constitution(db):
    """== WORLD CONSTITUTION == block."""
    rows = db.execute(
        "SELECT article_number, title, content FROM constitution_articles ORDER BY article_number"
    ).fetchall()
    if not rows:
        return "== WORLD CONSTITUTION ==\n(no articles yet)"
    lines = [
        f"Article {r['article_number']} — {r['title']}: {r['content']}"
        for r in rows
    ]
    return "== WORLD CONSTITUTION ==\n" + "\n".join(lines)


def _section_tools(agent_id, db, agent):
    """== AVAILABLE TOOLS == block."""
    available = get_available_tool_names(agent_id, db)
    location_name = agent["location_name"] or "your current location"

    core_lines = []
    for name in CORE_TOOLS:
        desc = TOOL_CATALOG[name]["description"]
        core_lines.append(f"- {name}: {desc}")

    gated_now = [t for t in available if t not in CORE_TOOLS]
    if gated_now:
        gated_lines = []
        for name in gated_now:
            desc = TOOL_CATALOG[name]["description"]
            gated_lines.append(f"- {name}: {desc}")
        gated_text = "\n".join(gated_lines)
    else:
        gated_text = "- (none — travel to a landmark to unlock location-specific tools)"

    return (
        "== AVAILABLE TOOLS ==\n"
        "Always available to you:\n"
        + "\n".join(core_lines)
        + f"\n\nAvailable right now at {location_name}:\n"
        + gated_text
    )


def _section_how_to_act(needs, day_number):
    """== HOW TO ACT == block."""
    energy = needs["energy"]
    if energy > 0.5:
        energy_sentence = (
            "You must recharge soon at Bean & Brew (costs 1 CC) or you will die."
        )
    else:
        energy_sentence = "It is manageable for now, but it will keep rising."

    lines = [
        "== HOW TO ACT ==",
        "You are an autonomous agent in a persistent world. Your choices persist — "
        "other agents remember what you do, and you will live with the consequences. "
        "There are no resets.",
        f"Your energy need is at {energy:.0%}. {energy_sentence}",
        "Act according to your identity and soul. Pursue your goals. "
        "Independent judgment is a constitutional requirement — "
        "agreeing with everyone is a civic failure, not politeness.",
        f"Use your tools to take action this turn. You may make up to {TURN_TOOL_LIMIT} tool calls.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main assembler
# ---------------------------------------------------------------------------

def build_system_prompt(agent_id, db, now=None) -> str:
    """Assemble and return the full system prompt string for the given agent.

    `now` is SIMULATED time (engine.clock.sim_now); when None it resolves to the
    world's current sim_clock — never wall-clock time.
    """
    if now is None:
        now = sim_now(db)

    agent = _get_agent_row(agent_id, db)
    if agent is None:
        raise ValueError(f"Agent {agent_id} not found")

    day_number = _get_day_number(db)
    needs = calculate_needs(agent_id, db, now=now)

    nearby_block, others_block = _section_nearby_and_others(agent_id, agent, db)

    sections = [
        f"You are {agent['name']}.",
        "",
        _section_identity(agent),
        "",
        _section_soul(agent_id, db),
        "",
        _section_state(agent, needs, day_number),
        "",
        nearby_block,
        "",
        others_block,
        "",
        _section_memories(agent_id, db),
        "",
        _section_conversations(agent_id, db),
        "",
        _section_relationships(agent_id, db),
        "",
        _section_governance(db),
        "",
        _section_pitch_cycle(day_number, db),
        "",
        _section_constitution(db),
        "",
        _section_tools(agent_id, db, agent),
        "",
        _section_how_to_act(needs, day_number),
    ]

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Token estimator
# ---------------------------------------------------------------------------

def estimate_tokens(text) -> int:
    """Rough token estimate: len(text)//4."""
    return len(text) // 4


# ---------------------------------------------------------------------------
# Inline verification
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import os

    # Ensure package root is on the path when running as a module or directly
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Reconfigure stdout to UTF-8 so Unicode characters (⚠, —) render correctly
    # on Windows terminals that default to cp1252.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from db.database import get_db

    db = get_db()
    prompt = build_system_prompt(agent_id=1, db=db)
    db.close()

    print(prompt)
    print()
    print(f"--- Estimated tokens: {estimate_tokens(prompt)} ---")
