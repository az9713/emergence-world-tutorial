"""
Location-gated tools for Emergence World.
These tools are only available when the agent is at the correct landmark.
The registry enforces location gating before calling these functions.
"""

import math
import time

from config import RECHARGE_COST_CC, GOVERNANCE_THRESHOLD, MEMORY_SUMMARIZE_MIN


# ---------------------------------------------------------------------------
# Governance helpers
# ---------------------------------------------------------------------------

def proposal_threshold(db):
    """Return (live_count, threshold_needed) for current agent population."""
    live_count = db.execute(
        "SELECT COUNT(*) FROM agents WHERE is_alive=1"
    ).fetchone()[0]
    threshold_needed = math.ceil(live_count * GOVERNANCE_THRESHOLD)
    return live_count, threshold_needed


def _resolve_proposal(proposal_id, db, now=None):
    """Evaluate a proposal and update its status if a decision can be made.

    Returns the new status string ('ACTIVE', 'ACCEPTED', or 'REJECTED').
    Only updates proposals that are still in ACTIVE status.
    """
    if now is None:
        now = time.time()

    # Only act on active proposals
    prop = db.execute(
        "SELECT status FROM proposals WHERE id=?", (proposal_id,)
    ).fetchone()
    if prop is None or prop["status"] != "ACTIVE":
        return prop["status"] if prop else "UNKNOWN"

    live_count, threshold_needed = proposal_threshold(db)

    vote_row = db.execute(
        """SELECT
            SUM(CASE WHEN vote='for' THEN 1 ELSE 0 END) AS votes_for,
            COUNT(*) AS votes_cast
           FROM proposal_votes WHERE proposal_id=?""",
        (proposal_id,),
    ).fetchone()

    votes_for = vote_row["votes_for"] or 0
    votes_cast = vote_row["votes_cast"] or 0
    remaining = live_count - votes_cast

    if votes_for >= threshold_needed:
        db.execute(
            "UPDATE proposals SET status='ACCEPTED', resolved_at=? WHERE id=? AND status='ACTIVE'",
            (now, proposal_id),
        )
        db.commit()
        return "ACCEPTED"
    elif votes_for + remaining < threshold_needed:
        db.execute(
            "UPDATE proposals SET status='REJECTED', resolved_at=? WHERE id=? AND status='ACTIVE'",
            (now, proposal_id),
        )
        db.commit()
        return "REJECTED"
    else:
        return "ACTIVE"


# ---------------------------------------------------------------------------
# Location-gated tool functions
# ---------------------------------------------------------------------------

def recharge_energy(agent_id, db, **kwargs):
    """Recharge the agent's energy at Bean & Brew. Costs RECHARGE_COST_CC credits."""
    from engine.needs import recharge_energy_reset

    row = db.execute(
        "SELECT credits FROM agents WHERE id=?", (agent_id,)
    ).fetchone()
    if row is None:
        return False, "Agent not found."

    credits = row["credits"]
    cost = RECHARGE_COST_CC

    if credits < cost:
        return False, (
            f"Insufficient credits to recharge ({credits:.1f} CC, need {cost} CC)."
        )

    # Deduct cost
    db.execute(
        "UPDATE agents SET credits=credits-? WHERE id=?", (cost, agent_id)
    )
    db.execute(
        """INSERT INTO credit_transactions
           (from_agent_id, to_agent_id, amount, reason, created_at)
           VALUES (?, NULL, ?, 'energy_recharge', ?)""",
        (agent_id, cost, time.time()),
    )
    db.commit()

    # Reset energy via engine module
    recharge_energy_reset(agent_id, db)

    return True, f"Energy recharged to full. Paid {cost} CC."


def self_care(agent_id, db, **kwargs):
    """Rest at home and reflect. Summarizes memories if above threshold."""
    # Count non-archived longterm memories (exclude soul and diary)
    n = db.execute(
        """SELECT COUNT(*) FROM memories
           WHERE agent_id=? AND memory_type='longterm' AND is_archived=0""",
        (agent_id,),
    ).fetchone()[0]

    if n >= MEMORY_SUMMARIZE_MIN:
        from engine.memory import summarize_agent_memories
        ok, msg = summarize_agent_memories(agent_id, db)
        return True, msg

    return True, (
        f"You rest at home and reflect. "
        f"You have {n} stored memories "
        f"(summarization triggers at {MEMORY_SUMMARIZE_MIN})."
    )


def add_to_diary(agent_id, db, content="", **kwargs):
    """Record a diary entry, prefixed with today's date."""
    import datetime
    today = datetime.date.today().strftime("%Y-%m-%d")
    prefixed = f"[{today}] {content}"

    db.execute(
        "INSERT INTO memories (agent_id, content, memory_type, created_at) VALUES (?,?,?,?)",
        (agent_id, prefixed, "diary", time.time()),
    )
    db.commit()

    return True, "Diary entry recorded."


def submit_proposal(agent_id, db, title="", description="", category="others", **kwargs):
    """Submit a governance proposal at Town Hall with an implicit 'for' vote."""
    valid_categories = ("constitution", "resource", "infrastructure", "others")
    if category not in valid_categories:
        category = "others"

    now = time.time()
    cur = db.execute(
        """INSERT INTO proposals (proposer_id, title, description, category, status, created_at)
           VALUES (?, ?, ?, ?, 'ACTIVE', ?)""",
        (agent_id, title, description, category, now),
    )
    proposal_id = cur.lastrowid

    # Implicit 'for' vote from proposer
    db.execute(
        """INSERT INTO proposal_votes (proposal_id, voter_id, vote, created_at)
           VALUES (?, ?, 'for', ?)""",
        (proposal_id, agent_id, now),
    )
    db.commit()

    # Resolve (will stay ACTIVE unless threshold already met with 1 vote)
    _resolve_proposal(proposal_id, db)

    live_count, threshold_needed = proposal_threshold(db)

    return True, (
        f"Proposal #{proposal_id} submitted: '{title}'. "
        f"Your implicit 'for' vote is counted. "
        f"Needs {threshold_needed}/{live_count} 'for' votes to pass."
    )


def vote_on_proposal(agent_id, db, proposal_id=None, vote="", **kwargs):
    """Vote 'for' or 'against' an active proposal at Town Hall."""
    if vote not in ("for", "against"):
        return False, "Vote must be 'for' or 'against'."

    if proposal_id is None:
        return False, "proposal_id is required."

    proposal_id = int(proposal_id)

    prop = db.execute(
        "SELECT id, title, status FROM proposals WHERE id=?", (proposal_id,)
    ).fetchone()
    if prop is None:
        return False, f"Proposal #{proposal_id} not found."
    if prop["status"] != "ACTIVE":
        return False, f"Proposal #{proposal_id} is no longer active (status: {prop['status']})."

    now = time.time()
    try:
        db.execute(
            """INSERT INTO proposal_votes (proposal_id, voter_id, vote, created_at)
               VALUES (?, ?, ?, ?)""",
            (proposal_id, agent_id, vote, now),
        )
        db.commit()
    except Exception:
        return False, f"You already voted on proposal #{proposal_id}."

    new_status = _resolve_proposal(proposal_id, db)

    return True, f"You voted '{vote}' on proposal #{proposal_id}. Status now: {new_status}."


def view_proposals(agent_id, db, **kwargs):
    """List all active proposals with vote counts."""
    rows = db.execute(
        """SELECT p.id, p.title, a.name AS proposer_name,
                  SUM(CASE WHEN pv.vote='for' THEN 1 ELSE 0 END) AS votes_for,
                  SUM(CASE WHEN pv.vote='against' THEN 1 ELSE 0 END) AS votes_against
           FROM proposals p
           JOIN agents a ON p.proposer_id = a.id
           LEFT JOIN proposal_votes pv ON pv.proposal_id = p.id
           WHERE p.status='ACTIVE'
           GROUP BY p.id""",
    ).fetchall()

    if not rows:
        return True, "No active proposals."

    lines = []
    for r in rows:
        lines.append(
            f"#{r['id']} '{r['title']}' by {r['proposer_name']} "
            f"[for: {r['votes_for'] or 0}, against: {r['votes_against'] or 0}]"
        )
    return True, "\n".join(lines)


def submit_pitch(agent_id, db, title="", description="", evidence_url="", **kwargs):
    """Submit a contribution pitch at Victory Arch. Evidence URL is required."""
    if not evidence_url or not evidence_url.strip():
        return False, (
            "Evidence URL required — pitches without verifiable evidence are disqualified."
        )

    # Determine current cycle from simulation state
    state = db.execute(
        "SELECT day_number FROM simulation_state WHERE id=1"
    ).fetchone()
    if state is None:
        return False, "Simulation state not found."

    day_number = state["day_number"]
    cycle_number = (day_number - 1) // 2 + 1

    now = time.time()
    cur = db.execute(
        """INSERT INTO pitch_submissions
           (agent_id, cycle_number, title, description, evidence_url, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (agent_id, cycle_number, title, description, evidence_url.strip(), now),
    )
    pitch_id = cur.lastrowid
    db.commit()

    return True, f"Pitch #{pitch_id} submitted for cycle {cycle_number}: '{title}'."


def vote_on_pitch(agent_id, db, pitch_id=None, **kwargs):
    """Vote for a pitch submission at Victory Arch. One vote per cycle per agent."""
    if pitch_id is None:
        return False, "pitch_id is required."

    pitch_id = int(pitch_id)

    submission = db.execute(
        "SELECT id, agent_id, cycle_number FROM pitch_submissions WHERE id=?",
        (pitch_id,),
    ).fetchone()
    if submission is None:
        return False, f"Pitch #{pitch_id} not found."

    # Self-vote check
    if submission["agent_id"] == agent_id:
        return False, "You cannot vote for your own pitch."

    cycle_number = submission["cycle_number"]

    # One-vote-per-cycle check (not just per submission)
    existing = db.execute(
        """SELECT pv.id FROM pitch_votes pv
           JOIN pitch_submissions ps ON pv.submission_id = ps.id
           WHERE ps.cycle_number=? AND pv.voter_id=?""",
        (cycle_number, agent_id),
    ).fetchone()
    if existing is not None:
        return False, "You already voted this cycle."

    now = time.time()
    try:
        db.execute(
            """INSERT INTO pitch_votes (submission_id, voter_id, created_at)
               VALUES (?, ?, ?)""",
            (pitch_id, agent_id, now),
        )
        db.commit()
    except Exception:
        return False, "You already voted for this pitch."

    return True, f"You voted for pitch #{pitch_id}."


def view_pitch_history(agent_id, db, **kwargs):
    """View current cycle pitches and past pitch rewards."""
    state = db.execute(
        "SELECT day_number FROM simulation_state WHERE id=1"
    ).fetchone()
    if state is None:
        return True, "Simulation state not found."

    day_number = state["day_number"]
    current_cycle = (day_number - 1) // 2 + 1

    # Current cycle pitches with vote counts
    pitches = db.execute(
        """SELECT ps.id, ps.title, a.name, COUNT(pv.id) AS vote_count
           FROM pitch_submissions ps
           JOIN agents a ON ps.agent_id = a.id
           LEFT JOIN pitch_votes pv ON pv.submission_id = ps.id
           WHERE ps.cycle_number=?
           GROUP BY ps.id
           ORDER BY vote_count DESC""",
        (current_cycle,),
    ).fetchall()

    lines = [f"=== Cycle {current_cycle} Pitches ==="]
    if pitches:
        for p in pitches:
            lines.append(f"  #{p['id']} '{p['title']}' by {p['name']} — {p['vote_count']} vote(s)")
    else:
        lines.append("  No pitches this cycle.")

    # Past rewards from credit_transactions
    rewards = db.execute(
        """SELECT ct.amount, a.name AS recipient, ct.reason, ct.created_at
           FROM credit_transactions ct
           LEFT JOIN agents a ON ct.to_agent_id = a.id
           WHERE ct.reason LIKE 'pitch_reward%'
           ORDER BY ct.created_at DESC
           LIMIT 20""",
    ).fetchall()

    lines.append("\n=== Past Pitch Rewards ===")
    if rewards:
        for r in rewards:
            lines.append(f"  {r['name']}: +{r['amount']} CC ({r['reason']})")
    else:
        lines.append("  No pitch rewards yet.")

    return True, "\n".join(lines)


def post_to_billboard(agent_id, db, content="", **kwargs):
    """Post a message to the Agent Billboard."""
    now = time.time()
    db.execute(
        "INSERT INTO billboard_posts (agent_id, content, created_at) VALUES (?, ?, ?)",
        (agent_id, content, now),
    )
    db.commit()
    return True, "Posted to billboard."


def read_billboard(agent_id, db, **kwargs):
    """Read the 10 most recent posts from the Agent Billboard."""
    rows = db.execute(
        """SELECT bp.content, a.name, bp.created_at
           FROM billboard_posts bp
           JOIN agents a ON bp.agent_id = a.id
           ORDER BY bp.created_at DESC
           LIMIT 10""",
    ).fetchall()

    if not rows:
        return True, "Billboard is empty."

    lines = []
    for r in rows:
        lines.append(f"{r['name']}: {r['content']}")
    return True, "\n".join(lines)
