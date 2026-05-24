import time
import config
from engine.clock import current_day


def cycle_for_day(day):
    """2-day cycles: days 1-2 = cycle 1, days 3-4 = cycle 2, ..."""
    return (day - 1) // 2 + 1


def _is_settled(cycle_number, db):
    """True if this cycle already paid out (a pitch_reward txn exists for it)."""
    row = db.execute(
        "SELECT 1 FROM credit_transactions WHERE reason LIKE ? LIMIT 1",
        (f"pitch_reward_cycle_{cycle_number}_%",),
    ).fetchone()
    return row is not None


def settle_cycle(cycle_number, db, observer=None):
    """Rank that cycle's pitches by vote count DESC, then created_at ASC (earlier wins ties).
    Award 20/10/10 CC to top 3. Credit each winner's balance and log a credit_transaction
    (from_agent_id=NULL, reason=f'pitch_reward_cycle_{cycle_number}_rank_{rank}').
    Idempotent: if already settled or no pitches, do nothing. Returns list of (agent_name, rank, reward)."""
    if _is_settled(cycle_number, db):
        return []
    pitches = db.execute(
        """SELECT ps.id, ps.agent_id, ps.title, ps.created_at,
                  (SELECT COUNT(*) FROM pitch_votes pv WHERE pv.submission_id=ps.id) AS votes
           FROM pitch_submissions ps WHERE ps.cycle_number=?
           ORDER BY votes DESC, ps.created_at ASC""",
        (cycle_number,),
    ).fetchall()
    if not pitches:
        return []
    rewards = [config.PITCH_REWARD_FIRST, config.PITCH_REWARD_SECOND, config.PITCH_REWARD_THIRD]
    results = []
    now = time.time()
    for rank, pitch in enumerate(pitches[:3], start=1):
        reward = rewards[rank - 1]
        db.execute("UPDATE agents SET credits = credits + ? WHERE id=?", (reward, pitch["agent_id"]))
        db.execute(
            "INSERT INTO credit_transactions (from_agent_id, to_agent_id, amount, reason, created_at) VALUES (NULL,?,?,?,?)",
            (pitch["agent_id"], reward, f"pitch_reward_cycle_{cycle_number}_rank_{rank}", now),
        )
        name = db.execute("SELECT name FROM agents WHERE id=?", (pitch["agent_id"],)).fetchone()["name"]
        results.append((name, rank, reward))
    db.commit()
    if observer and results:
        observer.print_event(
            "PITCH CYCLE %d SETTLED: " % cycle_number +
            ", ".join(f"#{r}={n} (+{cc} CC)" for n, r, cc in results),
            kind="economy",
        )
    return results


def settle_completed_cycles(db, observer=None):
    """Settle every cycle strictly before the current cycle that isn't settled yet.
    Call once per turn after the clock advances."""
    current_cycle = cycle_for_day(current_day(db))
    for c in range(1, current_cycle):
        settle_cycle(c, db, observer)
