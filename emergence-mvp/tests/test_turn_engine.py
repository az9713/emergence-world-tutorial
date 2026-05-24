"""
Deterministic integration tests for the turn engine.

No API key required — a fake turn_runner is injected into run_simulation.
The fake executes real tool calls via the provided execute_fn so DB state
changes are exercised end-to-end.
"""

import os
import sys
import sqlite3
import tempfile
import time
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SIM_SECONDS_PER_TURN, SECONDS_PER_SIM_DAY
from engine.clock import current_day
from engine.economy import settle_cycle
from engine.turn_engine import run_simulation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_temp_db():
    """
    Create a temp-file SQLite DB that mirrors get_db() (row_factory + FK pragma),
    applies the schema, and inserts minimal fixture data.

    Returns an open sqlite3.Connection.  The caller is responsible for closing it
    and deleting the temp file.
    """
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "db", "schema.sql",
    )
    with open(schema_path) as f:
        schema_sql = f.read()

    # Use a named temp file so SQLite can open it normally
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(schema_sql)
    db.commit()

    now = time.time()

    # --- Landmarks ---
    landmarks = [
        ("Town Hall",       "municipal",   60.0,  60.0),
        ("Bean & Brew",     "commercial",  60.0, 180.0),
        ("Agent Billboard", "attraction", 180.0, 180.0),
        ("Birch Row 1",     "residential",  30.0,  30.0),
        ("Birch Row 2",     "residential", 210.0,  30.0),
        ("Birch Row 3",     "residential", 120.0,  30.0),
        ("Victory Arch",    "attraction", 180.0,  60.0),
        ("Central Plaza",   "recreation", 120.0, 120.0),
    ]
    lm_ids = {}
    for name, cat, x, y in landmarks:
        cur = db.execute(
            "INSERT INTO landmarks (name, category, x, y) VALUES (?, ?, ?, ?)",
            (name, cat, x, y),
        )
        lm_ids[name] = cur.lastrowid

    # --- Landmark tools ---
    landmark_tools = {
        "Town Hall":       ["submit_proposal", "vote_on_proposal", "view_proposals"],
        "Bean & Brew":     ["recharge_energy"],
        "Agent Billboard": ["post_to_billboard", "read_billboard"],
        "Victory Arch":    ["submit_pitch", "vote_on_pitch", "view_pitch_history"],
        "Birch Row 1":     ["self_care", "add_to_diary"],
        "Birch Row 2":     ["self_care", "add_to_diary"],
        "Birch Row 3":     ["self_care", "add_to_diary"],
    }
    for lm_name, tools in landmark_tools.items():
        for tool_name in tools:
            db.execute(
                "INSERT INTO landmark_tools (landmark_id, tool_name) VALUES (?, ?)",
                (lm_ids[lm_name], tool_name),
            )

    # --- Agents (3 agents, all alive, 10 CC each so tools don't fail on credit checks) ---
    agent_names = ["Alpha", "Beta", "Gamma"]
    agent_homes = ["Birch Row 1", "Birch Row 2", "Birch Row 3"]
    agent_ids = {}
    for i, (aname, home_name) in enumerate(zip(agent_names, agent_homes)):
        home_id = lm_ids[home_name]
        start_id = lm_ids["Central Plaza"]
        cur = db.execute(
            """INSERT INTO agents
               (name, personality, home_landmark_id, location_id, x, y,
                energy_need, knowledge_need, influence_need, credits, mood,
                last_energy_recharge_at, last_knowledge_at, last_influence_at,
                is_alive, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
            (
                aname,
                f"{aname} test personality",
                home_id,
                start_id,
                120.0, 120.0,
                0.1,   # energy_need: 10% — well below critical
                0.0,
                0.0,
                10.0,  # generous credits
                "neutral",
                0.0,   # last_energy_recharge_at = sim 0
                0.0,
                0.0,
                now,
            ),
        )
        agent_ids[aname] = cur.lastrowid

    # Seed all-neutral relationships so system_prompt doesn't error
    id_list = list(agent_ids.values())
    for a in id_list:
        for b in id_list:
            if a != b:
                db.execute(
                    """INSERT OR IGNORE INTO relationships
                       (agent_id, target_agent_id, rel_type, trust_level, interaction_count, updated_at)
                       VALUES (?,?,'neutral',0.5,0,?)""",
                    (a, b, now),
                )

    # --- simulation_state (started_at is NOT NULL) ---
    db.execute(
        """INSERT INTO simulation_state
           (id, day_number, turn_number, sim_clock, sim_seconds_per_turn, started_at)
           VALUES (1, 1, 0, 0, ?, ?)""",
        (SIM_SECONDS_PER_TURN, now),
    )
    db.commit()

    return db, db_path, agent_ids, lm_ids


def make_fake_runner(script):
    """
    Returns a fake turn_runner that replays scripted tool calls.
    script: list of lists of (tool_name, inputs_dict).
    One inner list is consumed per call (run_simulation calls this once per turn).
    The fake EXECUTES tools via the provided execute_fn so DB state actually changes.
    """
    calls = {"i": 0}

    def fake(system_prompt, tool_schemas, execute_fn, max_calls=None, **kw):
        idx = calls["i"]
        calls["i"] += 1
        steps = script[idx] if idx < len(script) else []
        tool_calls = []
        for tool_name, inputs in steps:
            ok, res = execute_fn(tool_name, inputs)
            tool_calls.append({
                "tool_name": tool_name,
                "inputs": inputs,
                "success": ok,
                "result": res,
            })
        return {
            "tool_calls": tool_calls,
            "final_text": "",
            "stop_reason": "no_tool_use",
            "error": None,
        }

    return fake


# ---------------------------------------------------------------------------
# Test A: basic turn execution — go_to_place, turn counter, sim_clock
# ---------------------------------------------------------------------------

class TestBasicTurnExecution(unittest.TestCase):

    def setUp(self):
        self.db, self.db_path, self.agent_ids, self.lm_ids = _build_temp_db()

    def tearDown(self):
        self.db.close()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_three_turns_go_to_place(self):
        """3 turns: each agent does go_to_place to Town Hall.
        Assert: turn_number==3, sim_clock advanced by 3*SIM_SECONDS_PER_TURN,
        each agent's location updated to Town Hall, tool_calls table has rows."""

        town_hall_id = self.lm_ids["Town Hall"]
        # Script: one step per turn (3 agents x 1 turn each = 3 total turns)
        script = [
            [("go_to_place", {"landmark_name": "Town Hall"})],
            [("go_to_place", {"landmark_name": "Town Hall"})],
            [("go_to_place", {"landmark_name": "Town Hall"})],
        ]
        fake = make_fake_runner(script)

        run_simulation(3, db=self.db, turn_runner=fake, sleep=False)

        # turn_number should be 3
        state = self.db.execute(
            "SELECT turn_number, sim_clock FROM simulation_state WHERE id=1"
        ).fetchone()
        self.assertEqual(state["turn_number"], 3)

        # sim_clock advanced by 3 turns
        expected_clock = 3 * SIM_SECONDS_PER_TURN
        self.assertAlmostEqual(state["sim_clock"], expected_clock, places=1)

        # All agents should now be at Town Hall
        agents = self.db.execute(
            "SELECT location_id FROM agents WHERE is_alive=1"
        ).fetchall()
        for a in agents:
            self.assertEqual(
                a["location_id"], town_hall_id,
                "Agent location_id should be Town Hall after go_to_place"
            )

        # tool_calls table should have rows
        tc_count = self.db.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]
        self.assertGreater(tc_count, 0, "tool_calls table should have rows after turns")


# ---------------------------------------------------------------------------
# Test B: day boundary — 13 turns crosses into day 2
# ---------------------------------------------------------------------------

class TestDayBoundary(unittest.TestCase):

    def setUp(self):
        self.db, self.db_path, self.agent_ids, self.lm_ids = _build_temp_db()

    def tearDown(self):
        self.db.close()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_day_advances_after_13_turns(self):
        """13 turns of view_world_state (cheap, no side effects).
        At 7200 s/turn, 13 turns = 93600 s > 86400 s (one sim day).
        Assert day_number >= 2 and matches current_day(db)."""

        # 13 turns, each agent does view_world_state
        num_turns = 13
        script = [
            [("view_world_state", {})]
            for _ in range(num_turns)
        ]
        fake = make_fake_runner(script)

        run_simulation(num_turns, db=self.db, turn_runner=fake, sleep=False)

        state = self.db.execute(
            "SELECT day_number, sim_clock FROM simulation_state WHERE id=1"
        ).fetchone()

        self.assertGreaterEqual(state["day_number"], 2, "day_number should be >= 2 after 13 turns")
        # day_number in DB must match current_day() derived from sim_clock
        self.assertEqual(state["day_number"], current_day(self.db))


# ---------------------------------------------------------------------------
# Test C: economy settle_cycle idempotency
# ---------------------------------------------------------------------------

class TestEconomySettleCycle(unittest.TestCase):

    def setUp(self):
        self.db, self.db_path, self.agent_ids, self.lm_ids = _build_temp_db()

    def tearDown(self):
        self.db.close()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_settle_cycle_idempotent(self):
        """Insert 2 pitch submissions in cycle 1 with votes.
        First call settles and awards credits.
        Second call is a no-op (idempotent).
        Assert: correct 20/10 distribution, credit_transactions count==2 after both calls."""

        now = time.time()
        alpha_id = self.agent_ids["Alpha"]
        beta_id = self.agent_ids["Beta"]

        # Insert pitch submissions for cycle 1
        cur = self.db.execute(
            """INSERT INTO pitch_submissions
               (agent_id, cycle_number, title, description, evidence_url, created_at)
               VALUES (?,1,'Alpha Pitch','desc','http://a.com',?)""",
            (alpha_id, now),
        )
        pitch_a_id = cur.lastrowid

        cur = self.db.execute(
            """INSERT INTO pitch_submissions
               (agent_id, cycle_number, title, description, evidence_url, created_at)
               VALUES (?,1,'Beta Pitch','desc','http://b.com',?)""",
            (beta_id, now + 1),
        )
        pitch_b_id = cur.lastrowid

        # Alpha's pitch gets 2 votes, Beta's gets 1 vote — Alpha should rank 1st
        gamma_id = self.agent_ids["Gamma"]
        self.db.execute(
            "INSERT INTO pitch_votes (submission_id, voter_id, created_at) VALUES (?,?,?)",
            (pitch_a_id, beta_id, now),
        )
        self.db.execute(
            "INSERT INTO pitch_votes (submission_id, voter_id, created_at) VALUES (?,?,?)",
            (pitch_a_id, gamma_id, now),
        )
        self.db.execute(
            "INSERT INTO pitch_votes (submission_id, voter_id, created_at) VALUES (?,?,?)",
            (pitch_b_id, alpha_id, now),
        )
        self.db.commit()

        # Record credits before settlement
        alpha_credits_before = self.db.execute(
            "SELECT credits FROM agents WHERE id=?", (alpha_id,)
        ).fetchone()["credits"]
        beta_credits_before = self.db.execute(
            "SELECT credits FROM agents WHERE id=?", (beta_id,)
        ).fetchone()["credits"]

        # First settlement
        results1 = settle_cycle(1, self.db)
        self.assertEqual(len(results1), 2, "Should settle 2 pitches (top 3 or fewer)")

        # Check credit awards: Alpha 1st (+20), Beta 2nd (+10)
        alpha_credits_after = self.db.execute(
            "SELECT credits FROM agents WHERE id=?", (alpha_id,)
        ).fetchone()["credits"]
        beta_credits_after = self.db.execute(
            "SELECT credits FROM agents WHERE id=?", (beta_id,)
        ).fetchone()["credits"]

        self.assertAlmostEqual(
            alpha_credits_after, alpha_credits_before + 20.0, places=3,
            msg="Alpha (1st) should receive 20 CC"
        )
        self.assertAlmostEqual(
            beta_credits_after, beta_credits_before + 10.0, places=3,
            msg="Beta (2nd) should receive 10 CC"
        )

        # There should be exactly 2 credit_transactions for this cycle
        txn_count = self.db.execute(
            "SELECT COUNT(*) FROM credit_transactions WHERE reason LIKE 'pitch_reward_cycle_1_%'"
        ).fetchone()[0]
        self.assertEqual(txn_count, 2)

        # Second settlement — must be a no-op
        results2 = settle_cycle(1, self.db)
        self.assertEqual(results2, [], "Second settle_cycle call should return empty list (idempotent)")

        # Transaction count must still be 2, not 4
        txn_count_after = self.db.execute(
            "SELECT COUNT(*) FROM credit_transactions WHERE reason LIKE 'pitch_reward_cycle_1_%'"
        ).fetchone()[0]
        self.assertEqual(txn_count_after, 2, "No new transactions after second settle call")


# ---------------------------------------------------------------------------
# Test D: dead-agent skip
# ---------------------------------------------------------------------------

class TestDeadAgentSkip(unittest.TestCase):

    def setUp(self):
        self.db, self.db_path, self.agent_ids, self.lm_ids = _build_temp_db()

    def tearDown(self):
        self.db.close()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_dead_agent_gets_no_tool_calls(self):
        """Set one agent is_alive=0 before the simulation.
        Run a few turns; assert the dead agent appears in zero tool_calls rows."""

        dead_id = self.agent_ids["Beta"]
        self.db.execute("UPDATE agents SET is_alive=0 WHERE id=?", (dead_id,))
        self.db.commit()

        # 4 turns with view_world_state — enough for all live agents to act
        num_turns = 4
        script = [
            [("view_world_state", {})]
            for _ in range(num_turns)
        ]
        fake = make_fake_runner(script)

        run_simulation(num_turns, db=self.db, turn_runner=fake, sleep=False)

        # Dead agent should have zero tool_calls rows
        dead_tc = self.db.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE agent_id=?", (dead_id,)
        ).fetchone()[0]
        self.assertEqual(
            dead_tc, 0,
            "Dead agent (Beta) should have no tool_calls rows"
        )

        # Live agents should have tool_calls rows (they acted)
        for name in ("Alpha", "Gamma"):
            live_id = self.agent_ids[name]
            live_tc = self.db.execute(
                "SELECT COUNT(*) FROM tool_calls WHERE agent_id=?", (live_id,)
            ).fetchone()[0]
            self.assertGreater(
                live_tc, 0,
                f"Live agent {name} should have at least one tool_calls row"
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
