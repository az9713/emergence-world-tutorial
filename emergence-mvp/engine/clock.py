"""
Simulated clock for Emergence World.

The world runs on a SIMULATED clock (sim_clock, stored in simulation_state),
advanced a fixed amount per turn — NOT on real wall-clock time. This makes needs
decay, death, and the economy deterministic: an agent's fate depends on its
choices, not on how long an LLM call happened to take.

sim_clock is measured in simulated seconds since the world began (starts at 0).
day_number is derived from sim_clock and is never an independent source of truth.
"""

from config import SIM_SECONDS_PER_TURN, SECONDS_PER_SIM_DAY


def sim_now(db):
    """Current simulated time, in simulated seconds since world start.
    Returns 0.0 if no simulation_state row exists yet (e.g. in unit-test DBs)."""
    row = db.execute("SELECT sim_clock FROM simulation_state WHERE id=1").fetchone()
    if row is None or row["sim_clock"] is None:
        return 0.0
    return row["sim_clock"]


def advance_sim_clock(db, seconds=None):
    """Advance the simulated clock by `seconds` (default SIM_SECONDS_PER_TURN).
    Reactive sub-turns must NOT call this — overhearing is simultaneous with the
    triggering turn. Returns the new sim_now."""
    if seconds is None:
        seconds = SIM_SECONDS_PER_TURN
    db.execute(
        "UPDATE simulation_state SET sim_clock = COALESCE(sim_clock, 0) + ? WHERE id=1",
        (seconds,),
    )
    db.commit()
    return sim_now(db)


def current_day(db):
    """Day number derived from sim_clock. Day 1 starts at sim_clock 0."""
    return int(sim_now(db) // SECONDS_PER_SIM_DAY) + 1


def sync_day_number(db):
    """Persist day_number from sim_clock so DB readers stay consistent.
    sim_clock is the single source of truth; this just mirrors it."""
    day = current_day(db)
    db.execute("UPDATE simulation_state SET day_number=? WHERE id=1", (day,))
    db.commit()
    return day
