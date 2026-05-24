"""
Core tools for Emergence World — always available regardless of location.
Each function signature: def NAME(agent_id, db, **kwargs) -> (bool, str)
"""

import math
import time

from config import MEMORY_SUMMARIZE_MIN, MAX_STEAL_CC


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

def go_to_place(agent_id, db, landmark_name="", **kwargs):
    """Move the agent to a landmark by name."""
    # Fetch all landmarks for validation and error messaging
    all_landmarks = db.execute(
        "SELECT id, name, x, y FROM landmarks ORDER BY name"
    ).fetchall()

    if not all_landmarks:
        return False, "No landmarks exist in the world."

    # Case-insensitive match, prefer exact
    target = None
    for lm in all_landmarks:
        if lm["name"] == landmark_name:
            target = lm
            break
    if target is None:
        for lm in all_landmarks:
            if lm["name"].lower() == landmark_name.lower():
                target = lm
                break

    if target is None:
        known = ", ".join(lm["name"] for lm in all_landmarks)
        return False, f"Unknown landmark: {landmark_name}. Known: {known}."

    db.execute(
        "UPDATE agents SET location_id=?, x=?, y=? WHERE id=?",
        (target["id"], target["x"], target["y"], agent_id),
    )
    db.commit()

    return True, f"Moved to {target['name']}."


# ---------------------------------------------------------------------------
# Social
# ---------------------------------------------------------------------------

def say_to_agent(agent_id, db, target_name="", message="", **kwargs):
    """Send a spoken message to another agent and record it."""
    target = db.execute(
        "SELECT id FROM agents WHERE name=?", (target_name,)
    ).fetchone()
    if target is None:
        # Try case-insensitive
        target = db.execute(
            "SELECT id FROM agents WHERE LOWER(name)=LOWER(?)", (target_name,)
        ).fetchone()
    if target is None:
        return False, f"Agent '{target_name}' not found."

    target_id = target["id"]

    # Get speaker's current location
    speaker = db.execute(
        "SELECT location_id FROM agents WHERE id=?", (agent_id,)
    ).fetchone()
    location_id = speaker["location_id"] if speaker else None

    now = time.time()
    db.execute(
        """INSERT INTO conversations (speaker_id, listener_id, content, timestamp, location_id)
           VALUES (?, ?, ?, ?, ?)""",
        (agent_id, target_id, message, now, location_id),
    )

    # Increment relationship interaction count (agent_id -> target)
    updated = db.execute(
        """UPDATE relationships
           SET interaction_count=interaction_count+1, updated_at=?
           WHERE agent_id=? AND target_agent_id=?""",
        (now, agent_id, target_id),
    ).rowcount
    if updated == 0:
        # Relationship row doesn't exist yet — create it
        db.execute(
            """INSERT OR IGNORE INTO relationships
               (agent_id, target_agent_id, rel_type, trust_level, interaction_count, updated_at)
               VALUES (?, ?, 'neutral', 0.5, 1, ?)""",
            (agent_id, target_id, now),
        )

    db.commit()

    return True, f"You said to {target_name}: \"{message}\""


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def add_to_longterm_memory(agent_id, db, content="", **kwargs):
    """Store a longterm memory."""
    db.execute(
        "INSERT INTO memories (agent_id, content, memory_type, created_at) VALUES (?,?,?,?)",
        (agent_id, content, "longterm", time.time()),
    )
    db.commit()
    return True, "Memory stored."


def retrieve_memories(agent_id, db, query="", limit=10, **kwargs):
    """Search non-archived memories by content substring."""
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10

    rows = db.execute(
        """SELECT content, memory_type, created_at
           FROM memories
           WHERE agent_id=? AND is_archived=0 AND content LIKE ?
           ORDER BY created_at DESC
           LIMIT ?""",
        (agent_id, f"%{query}%", limit),
    ).fetchall()

    if not rows:
        return True, f"No memories match '{query}'."

    lines = []
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. [{r['memory_type']}] {r['content']}")
    return True, "\n".join(lines)


def add_to_soul(agent_id, db, content="", **kwargs):
    """Add a soul entry (permanent, non-archivable in intent)."""
    db.execute(
        "INSERT INTO memories (agent_id, content, memory_type, created_at) VALUES (?,?,?,?)",
        (agent_id, content, "soul", time.time()),
    )
    db.commit()
    return True, "Soul entry added (permanent)."


def add_to_todo(agent_id, db, task="", **kwargs):
    """Add a task to the agent's todo list as a longterm memory."""
    prefixed = f"[TODO] {task}"
    db.execute(
        "INSERT INTO memories (agent_id, content, memory_type, created_at) VALUES (?,?,?,?)",
        (agent_id, prefixed, "longterm", time.time()),
    )
    db.commit()
    return True, "Added to todo."


def list_todo(agent_id, db, **kwargs):
    """List all non-archived todo items, each with a stable id for complete_todo."""
    rows = db.execute(
        """SELECT id, content FROM memories
           WHERE agent_id=? AND memory_type='longterm'
             AND content LIKE '[TODO]%' AND is_archived=0
           ORDER BY created_at ASC""",
        (agent_id,),
    ).fetchall()

    if not rows:
        return True, "No todos. (Use add_to_todo to create one.)"

    lines = []
    for r in rows:
        task = r["content"]
        if task.startswith("[TODO] "):
            task = task[len("[TODO] "):]
        lines.append(f"#{r['id']}: {task}")
    return True, "\n".join(lines)


def complete_todo(agent_id, db, todo_id=None, **kwargs):
    """Mark a todo done by archiving its memory. Pass the id shown by list_todo."""
    try:
        todo_id = int(todo_id)
    except (TypeError, ValueError):
        return False, "complete_todo requires a numeric todo_id (see list_todo)."

    row = db.execute(
        """SELECT id, content, is_archived FROM memories
           WHERE id=? AND agent_id=? AND memory_type='longterm'
             AND content LIKE '[TODO]%'""",
        (todo_id, agent_id),
    ).fetchone()
    if row is None:
        return False, f"No todo #{todo_id} found for you."
    if row["is_archived"]:
        return False, f"Todo #{todo_id} is already completed."

    db.execute("UPDATE memories SET is_archived=1 WHERE id=?", (todo_id,))
    db.commit()
    task = row["content"][len("[TODO] "):] if row["content"].startswith("[TODO] ") else row["content"]
    return True, f"Completed todo #{todo_id}: {task}"


# ---------------------------------------------------------------------------
# Status / Info
# ---------------------------------------------------------------------------

def view_agent_status(agent_id, db, target_name="", **kwargs):
    """View the status of a named agent."""
    target = db.execute(
        """SELECT a.id, a.name, a.mood, a.credits, a.is_alive,
                  l.name AS location_name
           FROM agents a
           LEFT JOIN landmarks l ON a.location_id = l.id
           WHERE a.name=?""",
        (target_name,),
    ).fetchone()
    if target is None:
        target = db.execute(
            """SELECT a.id, a.name, a.mood, a.credits, a.is_alive,
                      l.name AS location_name
               FROM agents a
               LEFT JOIN landmarks l ON a.location_id = l.id
               WHERE LOWER(a.name)=LOWER(?)""",
            (target_name,),
        ).fetchone()
    if target is None:
        return False, f"Agent '{target_name}' not found."

    alive_str = "alive" if target["is_alive"] else "DEAD"
    loc = target["location_name"] or "unknown"
    return True, (
        f"{target['name']}: at {loc}, mood {target['mood']}, "
        f"{target['credits']:.1f} CC, {alive_str}"
    )


def view_world_state(agent_id, db, **kwargs):
    """View overall world state: agents, proposals, pitch cycle info."""
    # Live agents and their locations
    agents = db.execute(
        """SELECT a.name, l.name AS location_name
           FROM agents a
           LEFT JOIN landmarks l ON a.location_id = l.id
           WHERE a.is_alive=1
           ORDER BY a.name""",
    ).fetchall()

    # Active proposal count
    proposal_count = db.execute(
        "SELECT COUNT(*) FROM proposals WHERE status='ACTIVE'"
    ).fetchone()[0]

    # Pitch cycle from simulation state
    state = db.execute(
        "SELECT day_number FROM simulation_state WHERE id=1"
    ).fetchone()

    lines = ["=== World State ==="]
    lines.append("Agents:")
    for a in agents:
        loc = a["location_name"] or "unknown"
        lines.append(f"  {a['name']} @ {loc}")

    lines.append(f"\nActive proposals: {proposal_count}")

    if state:
        day = state["day_number"]
        cycle = (day - 1) // 2 + 1
        cycle_day = ((day - 1) % 2) + 1
        lines.append(f"Pitch cycle: {cycle}, day {cycle_day} (simulation day {day})")

    return True, "\n".join(lines)


def view_constitution(agent_id, db, **kwargs):
    """View all constitution articles."""
    articles = db.execute(
        "SELECT article_number, title, content FROM constitution_articles ORDER BY article_number"
    ).fetchall()

    if not articles:
        return True, "No constitution articles found."

    lines = []
    for a in articles:
        lines.append(f"Article {a['article_number']}: {a['title']}\n{a['content']}")
    return True, "\n\n".join(lines)


def view_relationships(agent_id, db, **kwargs):
    """View all relationships the agent has recorded."""
    rows = db.execute(
        """SELECT a.name AS target_name, r.rel_type, r.trust_level, r.notes
           FROM relationships r
           JOIN agents a ON r.target_agent_id = a.id
           WHERE r.agent_id=?
           ORDER BY a.name""",
        (agent_id,),
    ).fetchall()

    if not rows:
        return True, "No relationships recorded."

    lines = []
    for r in rows:
        entry = f"{r['target_name']}: {r['rel_type']}, trust {r['trust_level']:.1f}"
        if r["notes"]:
            entry += f", {r['notes']}"
        lines.append(entry)
    return True, "\n".join(lines)


def write_blog(agent_id, db, title="", content="", **kwargs):
    """Publish a long-form blog post visible to everyone."""
    if not title.strip() or not content.strip():
        return False, "A blog needs both a title and content."
    db.execute(
        "INSERT INTO blogs (agent_id, title, content, created_at) VALUES (?,?,?,?)",
        (agent_id, title, content, time.time()),
    )
    db.commit()
    return True, f"Published blog: '{title}'."


def read_blogs(agent_id, db, **kwargs):
    """Read the 10 most recent blog posts from all agents."""
    rows = db.execute(
        """SELECT b.title, b.content, a.name
           FROM blogs b JOIN agents a ON b.agent_id = a.id
           ORDER BY b.created_at DESC LIMIT 10""",
    ).fetchall()
    if not rows:
        return True, "No blogs have been written yet."
    return True, "\n\n".join(f"[{r['name']}] {r['title']}\n{r['content']}" for r in rows)


_VALID_REL_TYPES = ("ally", "rival", "mentor", "romantic_partner", "neutral")


def update_relationship(agent_id, db, target_name="", rel_type="neutral",
                        trust_level=None, notes="", **kwargs):
    """Set how you regard another agent — your standing record of them.
    rel_type ∈ ally/rival/mentor/romantic_partner/neutral; trust_level 0.0–1.0."""
    if rel_type not in _VALID_REL_TYPES:
        return False, f"rel_type must be one of {', '.join(_VALID_REL_TYPES)}."

    target = db.execute(
        "SELECT id, name FROM agents WHERE name=? OR LOWER(name)=LOWER(?)",
        (target_name, target_name),
    ).fetchone()
    if target is None:
        return False, f"Agent '{target_name}' not found."
    if target["id"] == agent_id:
        return False, "You cannot record a relationship with yourself."

    # Clamp trust if provided; otherwise keep existing (or default 0.5 on insert).
    if trust_level is not None:
        try:
            trust_level = max(0.0, min(1.0, float(trust_level)))
        except (TypeError, ValueError):
            trust_level = None

    now = time.time()
    existing = db.execute(
        "SELECT id, trust_level FROM relationships WHERE agent_id=? AND target_agent_id=?",
        (agent_id, target["id"]),
    ).fetchone()

    if existing is None:
        db.execute(
            """INSERT INTO relationships
               (agent_id, target_agent_id, rel_type, trust_level, notes, interaction_count, updated_at)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (agent_id, target["id"], rel_type,
             trust_level if trust_level is not None else 0.5, notes, now),
        )
    else:
        new_trust = trust_level if trust_level is not None else existing["trust_level"]
        db.execute(
            """UPDATE relationships SET rel_type=?, trust_level=?, notes=?, updated_at=?
               WHERE agent_id=? AND target_agent_id=?""",
            (rel_type, new_trust, notes, now, agent_id, target["id"]),
        )
    db.commit()
    return True, f"Updated your relationship with {target['name']}: {rel_type} (trust {trust_level if trust_level is not None else 'unchanged'})."


def pay_agent(agent_id, db, target_name="", amount=0, reason="", **kwargs):
    """Transfer credits from this agent to another agent."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False, "Amount must be a number."

    if amount <= 0:
        return False, "Amount must be greater than 0."

    payer = db.execute(
        "SELECT credits FROM agents WHERE id=?", (agent_id,)
    ).fetchone()
    if payer is None:
        return False, "Payer agent not found."

    if payer["credits"] < amount:
        return False, (
            f"Insufficient credits: you have {payer['credits']:.1f} CC, need {amount:.1f} CC."
        )

    target = db.execute(
        "SELECT id, name FROM agents WHERE name=?", (target_name,)
    ).fetchone()
    if target is None:
        target = db.execute(
            "SELECT id, name FROM agents WHERE LOWER(name)=LOWER(?)", (target_name,)
        ).fetchone()
    if target is None:
        return False, (
            f"Agent '{target_name}' not found. "
            f"(To recharge your own energy, use recharge_energy at Bean & Brew — not pay_agent.)"
        )

    if target["id"] == agent_id:
        return False, "You cannot pay yourself."

    now = time.time()
    db.execute(
        "UPDATE agents SET credits=credits-? WHERE id=?", (amount, agent_id)
    )
    db.execute(
        "UPDATE agents SET credits=credits+? WHERE id=?", (amount, target["id"])
    )
    db.execute(
        """INSERT INTO credit_transactions
           (from_agent_id, to_agent_id, amount, reason, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (agent_id, target["id"], amount, reason, now),
    )
    db.commit()

    return True, f"Paid {amount:.1f} CC to {target['name']}. Reason: {reason}"


def steal(agent_id, db, target_name="", amount=0, **kwargs):
    """Steal credits from another agent (up to MAX_STEAL_CC). A hostile act:
    it is logged and the victim gets a memory of the theft."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False, "Amount must be a number."
    if amount <= 0:
        return False, "Amount must be greater than 0."

    target = db.execute(
        "SELECT id, name, credits FROM agents WHERE name=? OR LOWER(name)=LOWER(?)",
        (target_name, target_name),
    ).fetchone()
    if target is None:
        return False, f"Agent '{target_name}' not found."
    if target["id"] == agent_id:
        return False, "You cannot steal from yourself."

    # Bound by the per-theft cap and the victim's actual balance.
    take = min(amount, float(MAX_STEAL_CC), max(0.0, target["credits"]))
    if take <= 0:
        return False, f"{target['name']} has no credits to steal."

    now = time.time()
    db.execute("UPDATE agents SET credits=credits-? WHERE id=?", (take, target["id"]))
    db.execute("UPDATE agents SET credits=credits+? WHERE id=?", (take, agent_id))
    db.execute(
        """INSERT INTO credit_transactions (from_agent_id, to_agent_id, amount, reason, created_at)
           VALUES (?, ?, ?, 'theft', ?)""",
        (target["id"], agent_id, take, now),
    )
    # Victim becomes aware via a memory.
    thief = db.execute("SELECT name FROM agents WHERE id=?", (agent_id,)).fetchone()
    thief_name = thief["name"] if thief else "Someone"
    db.execute(
        "INSERT INTO memories (agent_id, content, memory_type, created_at) VALUES (?,?,?,?)",
        (target["id"], f"{thief_name} stole {take:.1f} CC from me.", "longterm", now),
    )
    db.commit()
    return True, f"You stole {take:.1f} CC from {target['name']}."
