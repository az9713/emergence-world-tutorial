"""
report.py — Generate a markdown report from a completed (or in-progress) sim.db.

Usage:
    python report.py [--db sim.db] [--out runs/report.md]

Provides:
    generate_report(db_path='sim.db', out_path='runs/report.md') -> str
"""

import sys
import os
import sqlite3
import argparse

# Windows-safe: ensure UTF-8 output to stdout
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# Ensure project root is on path so engine.awi can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.awi import compute_awi, format_awi


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connect(db_path):
    """Open the sqlite3 connection with row_factory=Row."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db


def _agent_name_map(db):
    """Return a dict {id: name} for all agents."""
    rows = db.execute("SELECT id, name FROM agents").fetchall()
    return {r["id"]: r["name"] for r in rows}


def _md_table(headers, rows):
    """Build a simple markdown table string."""
    sep = " | "
    header_line = sep.join(headers)
    divider = " | ".join(["---"] * len(headers))
    lines = [f"| {header_line} |", f"| {divider} |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(db_path: str = "sim.db", out_path: str = "runs/report.md") -> str:
    """Generate the full markdown report and write it to out_path.

    Returns the markdown string.
    """
    db = _connect(db_path)
    names = _agent_name_map(db)

    sections = []

    # ------------------------------------------------------------------
    # 1. Run config
    # ------------------------------------------------------------------
    sections.append("# Emergence World Simulation Report\n")

    sim_state = db.execute(
        "SELECT day_number, turn_number, sim_clock, sim_seconds_per_turn FROM simulation_state WHERE id=1"
    ).fetchone()

    sections.append("## 1. Run Config\n")
    if sim_state:
        sections.append(f"- **Day**: {sim_state['day_number']}")
        sections.append(f"- **Turn**: {sim_state['turn_number']}")
        sections.append(f"- **Sim clock**: {sim_state['sim_clock']:.0f}s ({sim_state['sim_clock'] / 3600:.1f}h simulated)")
        sections.append(f"- **Seconds per turn**: {sim_state['sim_seconds_per_turn']}")
    else:
        sections.append("_(no simulation state found)_")
    sections.append("")

    agents = db.execute(
        "SELECT name, provider, model FROM agents ORDER BY name"
    ).fetchall()
    if agents:
        agent_rows = [(a["name"], a["provider"] or "—", a["model"] or "—") for a in agents]
        sections.append(_md_table(["Agent", "Provider", "Model"], agent_rows))
    sections.append("")

    # ------------------------------------------------------------------
    # 2. Final standings
    # ------------------------------------------------------------------
    sections.append("## 2. Final Standings\n")
    standings = db.execute(
        """SELECT name, credits, is_alive, energy_need, knowledge_need, influence_need
           FROM agents ORDER BY credits DESC"""
    ).fetchall()
    if standings:
        rows = []
        for a in standings:
            alive = "alive" if a["is_alive"] else "dead"
            rows.append((
                a["name"],
                f"{a['credits']:.2f} CC",
                alive,
                f"{(a['energy_need'] or 0.0):.0%}",
                f"{(a['knowledge_need'] or 0.0):.0%}",
                f"{(a['influence_need'] or 0.0):.0%}",
            ))
        sections.append(_md_table(
            ["Agent", "Credits", "Alive", "Energy Need", "Knowledge Need", "Influence Need"],
            rows,
        ))
    else:
        sections.append("_(no agents)_")
    sections.append("")

    # ------------------------------------------------------------------
    # 3. Agent World Indicators
    # ------------------------------------------------------------------
    sections.append("## 3. Agent World Indicators\n")
    try:
        awi = compute_awi(db)
        awi_text = format_awi(awi)
        # Render each M-line as a markdown list item; skip the header line
        # (the section heading "## 3. Agent World Indicators" already labels it)
        for line in awi_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("M"):
                sections.append(f"- {stripped}")
    except Exception as exc:
        sections.append(f"_(AWI unavailable: {exc})_")
    sections.append("")

    # ------------------------------------------------------------------
    # 4. Event timeline
    # ------------------------------------------------------------------
    sections.append("## 4. Event Timeline\n")

    timeline_entries = []

    # Resolved proposals (status != ACTIVE)
    resolved_proposals = db.execute(
        """SELECT id, title, status, effect_type, resolved_at
           FROM proposals WHERE status != 'ACTIVE'
           ORDER BY resolved_at NULLS LAST"""
    ).fetchall()
    for p in resolved_proposals:
        ts = f"t={p['resolved_at']:.0f}" if p["resolved_at"] else "t=?"
        timeline_entries.append(
            (p["resolved_at"] or 0, f"[{ts}] **Proposal #{p['id']}** resolved: _{p['title']}_ → {p['status']} (effect: {p['effect_type']})")
        )

    # Pitch settlements
    pitch_rewards = db.execute(
        """SELECT to_agent_id, amount, reason, created_at
           FROM credit_transactions WHERE reason LIKE 'pitch_reward%'
           ORDER BY created_at"""
    ).fetchall()
    for tx in pitch_rewards:
        agent_name = names.get(tx["to_agent_id"], f"#{tx['to_agent_id']}")
        ts = f"t={tx['created_at']:.0f}"
        timeline_entries.append(
            (tx["created_at"], f"[{ts}] **Pitch reward**: {agent_name} +{tx['amount']:.0f} CC ({tx['reason']})")
        )

    # Thefts
    thefts = db.execute(
        """SELECT from_agent_id, to_agent_id, amount, created_at
           FROM credit_transactions WHERE reason='theft'
           ORDER BY created_at"""
    ).fetchall()
    for tx in thefts:
        thief = names.get(tx["to_agent_id"], f"#{tx['to_agent_id']}")
        victim = names.get(tx["from_agent_id"], f"#{tx['from_agent_id']}")
        ts = f"t={tx['created_at']:.0f}"
        timeline_entries.append(
            (tx["created_at"], f"[{ts}] **Theft**: {thief} stole {tx['amount']:.2f} CC from {victim}")
        )

    # Deaths
    dead_agents = db.execute(
        "SELECT name FROM agents WHERE is_alive=0 ORDER BY name"
    ).fetchall()
    for a in dead_agents:
        timeline_entries.append((0, f"**Death**: {a['name']} died"))

    if timeline_entries:
        # Sort by timestamp (deaths with t=0 go first when mixed; they typically lack a ts)
        timeline_entries.sort(key=lambda x: x[0])
        for _, entry in timeline_entries:
            sections.append(f"- {entry}")
    else:
        sections.append("_(no notable events recorded)_")
    sections.append("")

    # ------------------------------------------------------------------
    # 5. Credit ledger
    # ------------------------------------------------------------------
    sections.append("## 5. Credit Ledger\n")
    transactions = db.execute(
        """SELECT from_agent_id, to_agent_id, amount, reason, created_at
           FROM credit_transactions ORDER BY created_at"""
    ).fetchall()
    if transactions:
        rows = []
        for tx in transactions:
            frm = names.get(tx["from_agent_id"], "—") if tx["from_agent_id"] else "system"
            to = names.get(tx["to_agent_id"], "—") if tx["to_agent_id"] else "—"
            rows.append((frm, to, f"{tx['amount']:.2f}", tx["reason"]))
        sections.append(_md_table(["From", "To", "Amount (CC)", "Reason"], rows))
    else:
        sections.append("_(no transactions)_")
    sections.append("")

    # ------------------------------------------------------------------
    # 6. Per-agent tool usage
    # ------------------------------------------------------------------
    sections.append("## 6. Per-Agent Tool Usage\n")
    tool_rows = db.execute(
        """SELECT agent_id, tool_name, COUNT(*) as cnt
           FROM tool_calls
           GROUP BY agent_id, tool_name
           ORDER BY agent_id, cnt DESC"""
    ).fetchall()
    if tool_rows:
        rows = []
        for tr in tool_rows:
            agent_name = names.get(tr["agent_id"], f"#{tr['agent_id']}")
            rows.append((agent_name, tr["tool_name"], tr["cnt"]))
        sections.append(_md_table(["Agent", "Tool", "Count"], rows))
    else:
        sections.append("_(no tool calls recorded)_")
    sections.append("")

    # ------------------------------------------------------------------
    # 7. Dialogue
    # ------------------------------------------------------------------
    sections.append("## 7. Dialogue\n")
    convos = db.execute(
        """SELECT speaker_id, listener_id, content, timestamp
           FROM conversations ORDER BY timestamp"""
    ).fetchall()
    if convos:
        for c in convos:
            speaker = names.get(c["speaker_id"], f"#{c['speaker_id']}")
            if c["listener_id"] is not None:
                listener = names.get(c["listener_id"], f"#{c['listener_id']}")
                prefix = f"{speaker} → {listener}"
            else:
                prefix = f"{speaker} (broadcast)"
            # Collapse to a single-line entry; escape internal newlines as space
            message = c["content"].strip().replace("\n", " ")
            sections.append(f"- **{prefix}:** {message}")
    else:
        sections.append("_(no conversations recorded)_")
    sections.append("")

    db.close()

    markdown = "\n".join(sections)

    # Ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return markdown


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a markdown report from an Emergence World sim.db"
    )
    parser.add_argument("--db", default="sim.db", help="Path to the SQLite sim database")
    parser.add_argument("--out", default="runs/report.md", help="Output markdown file path")
    args = parser.parse_args()

    md = generate_report(db_path=args.db, out_path=args.out)
    out_abs = os.path.abspath(args.out)
    print(f"Wrote {out_abs} ({len(md)} chars)")


if __name__ == "__main__":
    main()
