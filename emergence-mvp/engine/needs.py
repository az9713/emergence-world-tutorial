from config import (
    ENERGY_DRAIN_SECONDS,
    KNOWLEDGE_DRAIN_SECONDS,
    INFLUENCE_DRAIN_SECONDS,
    DEATH_THRESHOLD_SECONDS,
)
from engine.clock import sim_now

# Decay/death operate on the SIMULATED clock (engine.clock.sim_now), not wall-clock.
# `now` is simulated seconds; `speed` is a multiplier kept at 1 (the per-turn clock
# advance, not a speed multiplier, controls pacing). The `speed` parameter is retained
# so tests can pass explicit values.


def _decay(last_reset_at, drain_seconds, now, speed):
    """Linear decay. Returns float 0.0-1.0.

    need = min(1.0, elapsed_sim_seconds * speed / drain_seconds)

    If last_reset_at is None, treat as fully depleted (1.0).
    Clock skew is handled by clamping elapsed to >= 0.
    """
    if last_reset_at is None:
        return 1.0
    elapsed = max(0.0, now - last_reset_at)
    return min(1.0, elapsed * speed / drain_seconds)


def calculate_needs(agent_id, db, now=None, speed=None):
    """Return dict {'energy': float, 'knowledge': float, 'influence': float}
    computed fresh from the agent's last-reset timestamps.

    Does NOT write to DB.
    """
    if now is None:
        now = sim_now(db)
    if speed is None:
        speed = 1

    row = db.execute(
        "SELECT last_energy_recharge_at, last_knowledge_at, last_influence_at "
        "FROM agents WHERE id = ?",
        (agent_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"Agent {agent_id} not found")

    return {
        "energy": _decay(row["last_energy_recharge_at"], ENERGY_DRAIN_SECONDS, now, speed),
        "knowledge": _decay(row["last_knowledge_at"], KNOWLEDGE_DRAIN_SECONDS, now, speed),
        "influence": _decay(row["last_influence_at"], INFLUENCE_DRAIN_SECONDS, now, speed),
    }


def update_agent_needs(agent_id, db, now=None, speed=None):
    """Calculate needs, persist them to the agents table, and manage the death timer.

    Returns the needs dict.

    Death timer logic:
    - If energy >= 0.999 (critical) and death_energy_zero_since is NULL:
        set death_energy_zero_since = now  (energy just hit critical)
    - If energy < 0.999 and death_energy_zero_since is already set:
        clear it (agent recovered before dying) -> set to NULL
    """
    if now is None:
        now = sim_now(db)
    if speed is None:
        speed = 1

    needs = calculate_needs(agent_id, db, now=now, speed=speed)

    row = db.execute(
        "SELECT death_energy_zero_since FROM agents WHERE id = ?",
        (agent_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"Agent {agent_id} not found")

    death_since = row["death_energy_zero_since"]

    if needs["energy"] >= 0.999 and death_since is None:
        # Energy just hit critical — start the death countdown
        db.execute(
            "UPDATE agents SET energy_need=?, knowledge_need=?, influence_need=?, "
            "death_energy_zero_since=? WHERE id=?",
            (needs["energy"], needs["knowledge"], needs["influence"], now, agent_id),
        )
    elif needs["energy"] < 0.999 and death_since is not None:
        # Agent recovered — clear the death timer
        db.execute(
            "UPDATE agents SET energy_need=?, knowledge_need=?, influence_need=?, "
            "death_energy_zero_since=NULL WHERE id=?",
            (needs["energy"], needs["knowledge"], needs["influence"], agent_id),
        )
    else:
        # No change to death_energy_zero_since; just update the need values
        db.execute(
            "UPDATE agents SET energy_need=?, knowledge_need=?, influence_need=? "
            "WHERE id=?",
            (needs["energy"], needs["knowledge"], needs["influence"], agent_id),
        )

    db.commit()
    return needs


def check_death(agent_id, db, now=None, speed=None):
    """Return True if the agent should die (and marks is_alive=0), else False.

    Death condition: death_energy_zero_since is set AND
        (now - death_energy_zero_since) * speed >= DEATH_THRESHOLD_SECONDS.

    If the agent is already dead (is_alive=0), return False (already handled).
    Caller is responsible for calling update_agent_needs first so the timer is current.
    """
    if now is None:
        now = sim_now(db)
    if speed is None:
        speed = 1

    row = db.execute(
        "SELECT is_alive, death_energy_zero_since FROM agents WHERE id = ?",
        (agent_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"Agent {agent_id} not found")

    if row["is_alive"] == 0:
        # Already dead — nothing to do
        return False

    death_since = row["death_energy_zero_since"]
    if death_since is None:
        return False

    elapsed_real = now - death_since
    simulated_seconds = elapsed_real * speed
    if simulated_seconds >= DEATH_THRESHOLD_SECONDS:
        db.execute("UPDATE agents SET is_alive=0 WHERE id=?", (agent_id,))
        db.commit()
        return True

    return False


def recharge_energy_reset(agent_id, db, now=None):
    """Reset energy: set last_energy_recharge_at=now, energy_need=0.0,
    death_energy_zero_since=NULL.

    Commits. Used by the recharge_energy tool.
    (The tool layer handles the credit cost.)
    """
    if now is None:
        now = sim_now(db)

    db.execute(
        "UPDATE agents SET last_energy_recharge_at=?, energy_need=0.0, "
        "death_energy_zero_since=NULL WHERE id=?",
        (now, agent_id),
    )
    db.commit()
