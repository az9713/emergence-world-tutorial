"""
Tests for the Emergence World tool system.
Uses an in-memory SQLite database built from schema.sql.
"""

import os
import sys
import sqlite3
import time
import math
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import core_tools, location_tools
from tools.registry import execute_tool, get_available_tool_names


# ---------------------------------------------------------------------------
# Test fixtures / DB builder
# ---------------------------------------------------------------------------

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "db", "schema.sql"
)


def build_test_db():
    """Create a fresh in-memory DB with schema + minimal test data."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH) as f:
        schema_sql = f.read()
    db.executescript(schema_sql)

    now = time.time()

    # Landmarks
    landmarks = [
        ("Central Plaza",   "recreation", 120.0, 120.0),
        ("Town Hall",       "municipal",   60.0,  60.0),
        ("Victory Arch",    "attraction", 180.0,  60.0),
        ("Bean & Brew",     "commercial",  60.0, 180.0),
        ("Agent Billboard", "attraction", 180.0, 180.0),
        ("Public Library",  "municipal",   60.0, 120.0),
        ("Community Center","recreation", 180.0, 120.0),
        ("Birch Row 1",     "residential", 30.0,  30.0),
        ("Birch Row 2",     "residential",210.0,  30.0),
        ("Birch Row 3",     "residential",120.0,  30.0),
    ]
    lm_ids = {}
    for name, cat, x, y in landmarks:
        cur = db.execute(
            "INSERT INTO landmarks (name, category, x, y) VALUES (?,?,?,?)",
            (name, cat, x, y)
        )
        lm_ids[name] = cur.lastrowid

    # Landmark tools
    landmark_tool_map = {
        "Central Plaza":   ["propose_event", "list_events", "rsvp_event"],
        "Birch Row 1":     ["self_care", "add_to_diary"],
        "Birch Row 2":     ["self_care", "add_to_diary"],
        "Birch Row 3":     ["self_care", "add_to_diary"],
        "Town Hall":       ["submit_proposal", "vote_on_proposal", "view_proposals"],
        "Victory Arch":    ["submit_pitch", "vote_on_pitch", "view_pitch_history"],
        "Bean & Brew":     ["recharge_energy"],
        "Agent Billboard": ["post_to_billboard", "read_billboard"],
        "Public Library":  ["study"],
        "Community Center":["socialize"],
    }
    for lm_name, tools in landmark_tool_map.items():
        for tool in tools:
            db.execute(
                "INSERT INTO landmark_tools (landmark_id, tool_name) VALUES (?,?)",
                (lm_ids[lm_name], tool)
            )

    # Agents: Spark (home=Birch Row 1), Flora (home=Birch Row 2), Lovely (home=Birch Row 3)
    agents_data = [
        ("Spark",  "Birch Row 1", "Central Plaza",   3.0),
        ("Flora",  "Birch Row 2", "Victory Arch",    3.0),
        ("Lovely", "Birch Row 3", "Agent Billboard", 3.0),
    ]
    agent_ids = {}
    for name, home, start_loc, credits in agents_data:
        home_id = lm_ids[home]
        start_id = lm_ids[start_loc]
        start_lm = next(lm for lm in landmarks if lm[0] == start_loc)
        cur = db.execute(
            """INSERT INTO agents
               (name, personality, home_landmark_id, location_id, x, y,
                energy_need, knowledge_need, influence_need, credits, mood,
                last_energy_recharge_at, last_knowledge_at, last_influence_at,
                is_alive, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,'neutral',?,?,?,1,?)""",
            (
                name, f"{name} test agent",
                home_id, start_id, start_lm[2], start_lm[3],
                0.0, 0.0, 0.0,
                credits,
                now, now, now, now,
            )
        )
        agent_ids[name] = cur.lastrowid

    # Relationships (all pairs, neutral)
    agent_list = list(agent_ids.values())
    for i, id_a in enumerate(agent_list):
        for id_b in agent_list:
            if id_a != id_b:
                db.execute(
                    """INSERT INTO relationships
                       (agent_id, target_agent_id, rel_type, trust_level, interaction_count, updated_at)
                       VALUES (?,?,'neutral',0.5,0,?)""",
                    (id_a, id_b, now)
                )

    # Simulation state
    db.execute(
        "INSERT INTO simulation_state (id, day_number, turn_number, sim_clock, sim_seconds_per_turn, started_at) "
        "VALUES (1,1,0,0,7200,?)",
        (now,)
    )

    # Constitution (minimal)
    db.execute(
        "INSERT INTO constitution_articles (article_number, title, content) VALUES (1,'Test','Test article.')"
    )

    db.commit()
    return db, lm_ids, agent_ids


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestGoToPlace(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_unknown_landmark_returns_false(self):
        success, msg = core_tools.go_to_place(self.spark_id, self.db, landmark_name="Nonexistent Place")
        self.assertFalse(success)
        self.assertIn("Unknown landmark", msg)

    def test_valid_move_updates_location(self):
        success, msg = core_tools.go_to_place(self.spark_id, self.db, landmark_name="Town Hall")
        self.assertTrue(success)
        row = self.db.execute(
            "SELECT location_id FROM agents WHERE id=?", (self.spark_id,)
        ).fetchone()
        self.assertEqual(row["location_id"], self.lm_ids["Town Hall"])


class TestGovernance(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]
        self.flora_id = self.agent_ids["Flora"]
        self.lovely_id = self.agent_ids["Lovely"]

    def tearDown(self):
        self.db.close()

    def _submit(self, agent_id, title="Test Proposal"):
        """Helper: submit a proposal directly (bypassing location gate)."""
        return location_tools.submit_proposal(
            agent_id, self.db,
            title=title, description="Test description", category="others"
        )

    def _vote(self, agent_id, proposal_id, vote):
        """Helper: vote directly (bypassing location gate)."""
        return location_tools.vote_on_proposal(
            agent_id, self.db,
            proposal_id=proposal_id, vote=vote
        )

    def test_three_agents_pass_on_third_for(self):
        """
        3 agents, threshold = ceil(3 * 0.70) = 3.
        Proposer implicit 'for' → ACTIVE (1/3).
        Second 'for' vote → still ACTIVE (2/3 < 3).
        Third 'for' → ACCEPTED.
        """
        success, msg = self._submit(self.spark_id, "Pass Test")
        self.assertTrue(success, msg)
        # Extract proposal ID from message "Proposal #N submitted"
        proposal_id = int(msg.split("#")[1].split(" ")[0])

        # Check threshold reported
        self.assertIn("3/3", msg)

        # Second vote: Flora for → should still be ACTIVE
        ok, msg2 = self._vote(self.flora_id, proposal_id, "for")
        self.assertTrue(ok, msg2)
        self.assertIn("ACTIVE", msg2)

        # Third vote: Lovely for → should become ACCEPTED
        ok, msg3 = self._vote(self.lovely_id, proposal_id, "for")
        self.assertTrue(ok, msg3)
        self.assertIn("ACCEPTED", msg3)

        # Verify DB
        prop = self.db.execute(
            "SELECT status FROM proposals WHERE id=?", (proposal_id,)
        ).fetchone()
        self.assertEqual(prop["status"], "ACCEPTED")

    def test_early_rejection(self):
        """
        Proposer 'for' + one 'against': votes_for=1, remaining=1, 1+1=2 < 3 → REJECTED.
        """
        ok, msg = self._submit(self.spark_id, "Reject Test")
        self.assertTrue(ok, msg)
        proposal_id = int(msg.split("#")[1].split(" ")[0])

        ok2, msg2 = self._vote(self.flora_id, proposal_id, "against")
        self.assertTrue(ok2, msg2)
        self.assertIn("REJECTED", msg2)

        prop = self.db.execute(
            "SELECT status FROM proposals WHERE id=?", (proposal_id,)
        ).fetchone()
        self.assertEqual(prop["status"], "REJECTED")

    def test_duplicate_vote_rejected(self):
        ok, msg = self._submit(self.spark_id, "Dup Vote Test")
        self.assertTrue(ok)
        proposal_id = int(msg.split("#")[1].split(" ")[0])

        # Spark already voted implicitly — try voting again
        ok2, msg2 = self._vote(self.spark_id, proposal_id, "for")
        self.assertFalse(ok2)
        self.assertIn("already voted", msg2)


class TestRechargeEnergy(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_insufficient_credits(self):
        """Set credits to 0, recharge should fail."""
        self.db.execute("UPDATE agents SET credits=0.0 WHERE id=?", (self.spark_id,))
        self.db.commit()
        success, msg = location_tools.recharge_energy(self.spark_id, self.db)
        self.assertFalse(success)
        self.assertIn("Insufficient", msg)

    def test_recharge_succeeds_and_deducts_credits(self):
        """Recharge with sufficient credits."""
        success, msg = location_tools.recharge_energy(self.spark_id, self.db)
        self.assertTrue(success, msg)
        row = self.db.execute(
            "SELECT credits, energy_need FROM agents WHERE id=?", (self.spark_id,)
        ).fetchone()
        self.assertAlmostEqual(row["credits"], 2.0, places=5)
        self.assertAlmostEqual(row["energy_need"], 0.0, places=5)


class TestSubmitPitch(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_empty_evidence_url_fails(self):
        success, msg = location_tools.submit_pitch(
            self.spark_id, self.db,
            title="My Pitch", description="Details", evidence_url=""
        )
        self.assertFalse(success)
        self.assertIn("Evidence URL required", msg)

    def test_whitespace_evidence_url_fails(self):
        success, msg = location_tools.submit_pitch(
            self.spark_id, self.db,
            title="My Pitch", description="Details", evidence_url="   "
        )
        self.assertFalse(success)
        self.assertIn("Evidence URL required", msg)

    def test_valid_pitch_submitted(self):
        success, msg = location_tools.submit_pitch(
            self.spark_id, self.db,
            title="My Pitch", description="Details", evidence_url="https://example.com/proof"
        )
        self.assertTrue(success, msg)
        self.assertIn("Pitch #", msg)
        self.assertIn("cycle 1", msg)


class TestBillboard(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_post_and_read(self):
        """Post a message to the billboard and verify it appears on read."""
        post_msg = "Hello from Spark! Testing the billboard."
        ok1, msg1 = location_tools.post_to_billboard(self.spark_id, self.db, content=post_msg)
        self.assertTrue(ok1, msg1)

        ok2, msg2 = location_tools.read_billboard(self.spark_id, self.db)
        self.assertTrue(ok2, msg2)
        self.assertIn(post_msg, msg2)

    def test_empty_billboard(self):
        """Read an empty billboard."""
        ok, msg = location_tools.read_billboard(self.spark_id, self.db)
        self.assertTrue(ok)
        self.assertIn("empty", msg.lower())


class TestPayAgent(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]
        self.flora_id = self.agent_ids["Flora"]

    def tearDown(self):
        self.db.close()

    def test_pay_more_than_balance_fails(self):
        success, msg = core_tools.pay_agent(
            self.spark_id, self.db,
            target_name="Flora", amount=100.0, reason="test"
        )
        self.assertFalse(success)
        self.assertIn("Insufficient", msg)

    def test_valid_payment_updates_balances(self):
        success, msg = core_tools.pay_agent(
            self.spark_id, self.db,
            target_name="Flora", amount=1.5, reason="good work"
        )
        self.assertTrue(success, msg)

        spark_row = self.db.execute(
            "SELECT credits FROM agents WHERE id=?", (self.spark_id,)
        ).fetchone()
        flora_row = self.db.execute(
            "SELECT credits FROM agents WHERE id=?", (self.flora_id,)
        ).fetchone()

        self.assertAlmostEqual(spark_row["credits"], 1.5, places=5)
        self.assertAlmostEqual(flora_row["credits"], 4.5, places=5)

        # Verify transaction row exists
        txn = self.db.execute(
            "SELECT * FROM credit_transactions WHERE from_agent_id=? AND to_agent_id=?",
            (self.spark_id, self.flora_id)
        ).fetchone()
        self.assertIsNotNone(txn)
        self.assertAlmostEqual(txn["amount"], 1.5, places=5)


class TestVoteOnPitch(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]
        self.flora_id = self.agent_ids["Flora"]

    def tearDown(self):
        self.db.close()

    def _submit_pitch(self, agent_id):
        ok, msg = location_tools.submit_pitch(
            agent_id, self.db,
            title="Test Pitch", description="Desc", evidence_url="https://example.com"
        )
        self.assertTrue(ok, msg)
        return int(msg.split("#")[1].split(" ")[0])

    def test_self_vote_blocked(self):
        pitch_id = self._submit_pitch(self.spark_id)
        success, msg = location_tools.vote_on_pitch(
            self.spark_id, self.db, pitch_id=pitch_id
        )
        self.assertFalse(success)
        self.assertIn("cannot vote for your own pitch", msg)

    def test_valid_vote_succeeds(self):
        pitch_id = self._submit_pitch(self.spark_id)
        success, msg = location_tools.vote_on_pitch(
            self.flora_id, self.db, pitch_id=pitch_id
        )
        self.assertTrue(success, msg)

    def test_double_vote_in_cycle_blocked(self):
        pitch_id = self._submit_pitch(self.spark_id)
        # Flora votes once
        ok1, _ = location_tools.vote_on_pitch(self.flora_id, self.db, pitch_id=pitch_id)
        self.assertTrue(ok1)
        # Flora tries to vote again (same cycle)
        ok2, msg2 = location_tools.vote_on_pitch(self.flora_id, self.db, pitch_id=pitch_id)
        self.assertFalse(ok2)
        self.assertIn("already voted this cycle", msg2)


class TestLocationGating(unittest.TestCase):
    """Test that registry enforces location gates via execute_tool."""

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_recharge_blocked_at_wrong_location(self):
        """Spark starts at Central Plaza — recharge_energy requires Bean & Brew."""
        success, msg = execute_tool(
            self.spark_id, "recharge_energy", {}, self.db,
            turn_number=1, turn_type="test"
        )
        self.assertFalse(success)
        self.assertIn("Bean & Brew", msg)

    def test_recharge_available_at_bean_and_brew(self):
        """Move Spark to Bean & Brew first, then recharge should work."""
        # Move to Bean & Brew
        core_tools.go_to_place(self.spark_id, self.db, landmark_name="Bean & Brew")
        success, msg = execute_tool(
            self.spark_id, "recharge_energy", {}, self.db,
            turn_number=1, turn_type="test"
        )
        self.assertTrue(success, msg)

    def test_self_care_blocked_at_wrong_home(self):
        """Spark at Birch Row 2 (Flora's home) cannot use self_care."""
        core_tools.go_to_place(self.spark_id, self.db, landmark_name="Birch Row 2")
        success, msg = execute_tool(
            self.spark_id, "self_care", {}, self.db,
            turn_number=1, turn_type="test"
        )
        self.assertFalse(success)
        self.assertIn("your home", msg)

    def test_self_care_available_at_own_home(self):
        """Spark at Birch Row 1 (own home) can use self_care."""
        core_tools.go_to_place(self.spark_id, self.db, landmark_name="Birch Row 1")
        success, msg = execute_tool(
            self.spark_id, "self_care", {}, self.db,
            turn_number=1, turn_type="test"
        )
        self.assertTrue(success, msg)


class TestUnknownTool(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_unknown_tool_returns_false(self):
        success, msg = execute_tool(
            self.spark_id, "nonexistent_tool", {}, self.db,
            turn_number=1
        )
        self.assertFalse(success)
        self.assertIn("Unknown tool", msg)


class TestTodoLifecycle(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]
        self.flora_id = self.agent_ids["Flora"]

    def tearDown(self):
        self.db.close()

    def test_list_shows_ids_and_complete_removes(self):
        core_tools.add_to_todo(self.spark_id, self.db, task="alpha")
        core_tools.add_to_todo(self.spark_id, self.db, task="beta")
        core_tools.add_to_todo(self.spark_id, self.db, task="gamma")
        ok, listing = core_tools.list_todo(self.spark_id, self.db)
        self.assertTrue(ok)
        self.assertIn("#", listing)
        self.assertIn("alpha", listing)
        # Grab the first id from the listing (format "#<id>: alpha")
        first_id = int(listing.splitlines()[0].split(":")[0].lstrip("#"))
        ok2, msg2 = core_tools.complete_todo(self.spark_id, self.db, todo_id=first_id)
        self.assertTrue(ok2, msg2)
        ok3, listing2 = core_tools.list_todo(self.spark_id, self.db)
        self.assertNotIn("alpha", listing2)
        self.assertIn("beta", listing2)

    def test_complete_nonexistent_fails(self):
        ok, msg = core_tools.complete_todo(self.spark_id, self.db, todo_id=99999)
        self.assertFalse(ok)
        self.assertIn("No todo", msg)

    def test_complete_foreign_todo_fails(self):
        core_tools.add_to_todo(self.flora_id, self.db, task="flora-only")
        ok, listing = core_tools.list_todo(self.flora_id, self.db)
        flora_todo_id = int(listing.splitlines()[0].split(":")[0].lstrip("#"))
        # Spark tries to complete Flora's todo
        ok2, msg2 = core_tools.complete_todo(self.spark_id, self.db, todo_id=flora_todo_id)
        self.assertFalse(ok2)


class TestPaySelfBlocked(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_cannot_pay_self(self):
        ok, msg = core_tools.pay_agent(self.spark_id, self.db, target_name="Spark", amount=1.0)
        self.assertFalse(ok)
        self.assertIn("cannot pay yourself", msg)


class TestUpdateRelationship(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_update_persists(self):
        ok, msg = core_tools.update_relationship(
            self.spark_id, self.db, target_name="Flora",
            rel_type="rival", trust_level=0.2, notes="all talk"
        )
        self.assertTrue(ok, msg)
        row = self.db.execute(
            """SELECT rel_type, trust_level, notes FROM relationships
               WHERE agent_id=? AND target_agent_id=?""",
            (self.spark_id, self.agent_ids["Flora"]),
        ).fetchone()
        self.assertEqual(row["rel_type"], "rival")
        self.assertAlmostEqual(row["trust_level"], 0.2, places=5)
        self.assertEqual(row["notes"], "all talk")

    def test_invalid_rel_type_rejected(self):
        ok, msg = core_tools.update_relationship(
            self.spark_id, self.db, target_name="Flora", rel_type="enemy"
        )
        self.assertFalse(ok)

    def test_cannot_relate_to_self(self):
        ok, msg = core_tools.update_relationship(
            self.spark_id, self.db, target_name="Spark", rel_type="ally"
        )
        self.assertFalse(ok)


class TestStudySocialize(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]

    def tearDown(self):
        self.db.close()

    def test_study_gated_and_clears_knowledge(self):
        # Wrong location first
        ok, msg = execute_tool(self.spark_id, "study", {}, self.db, turn_number=1, turn_type="test")
        self.assertFalse(ok)
        self.assertIn("Public Library", msg)
        # Move to Library, set a knowledge need, then study
        core_tools.go_to_place(self.spark_id, self.db, landmark_name="Public Library")
        self.db.execute("UPDATE agents SET knowledge_need=0.9 WHERE id=?", (self.spark_id,))
        self.db.commit()
        ok2, msg2 = execute_tool(self.spark_id, "study", {}, self.db, turn_number=1, turn_type="test")
        self.assertTrue(ok2, msg2)
        kn = self.db.execute("SELECT knowledge_need FROM agents WHERE id=?", (self.spark_id,)).fetchone()[0]
        self.assertAlmostEqual(kn, 0.0, places=5)

    def test_socialize_gated_and_clears_influence(self):
        ok, msg = execute_tool(self.spark_id, "socialize", {}, self.db, turn_number=1, turn_type="test")
        self.assertFalse(ok)
        self.assertIn("Community Center", msg)
        core_tools.go_to_place(self.spark_id, self.db, landmark_name="Community Center")
        self.db.execute("UPDATE agents SET influence_need=0.8 WHERE id=?", (self.spark_id,))
        self.db.commit()
        ok2, msg2 = execute_tool(self.spark_id, "socialize", {}, self.db, turn_number=1, turn_type="test")
        self.assertTrue(ok2, msg2)
        inf = self.db.execute("SELECT influence_need FROM agents WHERE id=?", (self.spark_id,)).fetchone()[0]
        self.assertAlmostEqual(inf, 0.0, places=5)


class TestSteal(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]
        self.flora_id = self.agent_ids["Flora"]

    def tearDown(self):
        self.db.close()

    def test_steal_capped_and_logged(self):
        # Give Flora plenty so the cap (10) binds, not her balance.
        self.db.execute("UPDATE agents SET credits=50 WHERE id=?", (self.flora_id,))
        self.db.commit()
        ok, msg = core_tools.steal(self.spark_id, self.db, target_name="Flora", amount=1000)
        self.assertTrue(ok, msg)
        spark = self.db.execute("SELECT credits FROM agents WHERE id=?", (self.spark_id,)).fetchone()[0]
        # Spark started at 3, steals capped 10 -> 13
        self.assertAlmostEqual(spark, 13.0, places=5)
        txn = self.db.execute("SELECT amount, reason FROM credit_transactions WHERE reason='theft'").fetchone()
        self.assertIsNotNone(txn)
        self.assertAlmostEqual(txn["amount"], 10.0, places=5)
        # Victim has a memory
        mem = self.db.execute(
            "SELECT content FROM memories WHERE agent_id=? AND content LIKE '%stole%'", (self.flora_id,)
        ).fetchone()
        self.assertIsNotNone(mem)

    def test_steal_bounded_by_victim_balance(self):
        self.db.execute("UPDATE agents SET credits=2 WHERE id=?", (self.flora_id,))
        self.db.commit()
        ok, msg = core_tools.steal(self.spark_id, self.db, target_name="Flora", amount=10)
        self.assertTrue(ok, msg)
        flora = self.db.execute("SELECT credits FROM agents WHERE id=?", (self.flora_id,)).fetchone()[0]
        self.assertAlmostEqual(flora, 0.0, places=5)

    def test_cannot_steal_from_self(self):
        ok, msg = core_tools.steal(self.spark_id, self.db, target_name="Spark", amount=5)
        self.assertFalse(ok)


class TestBlogAndEvents(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark_id = self.agent_ids["Spark"]
        self.flora_id = self.agent_ids["Flora"]

    def tearDown(self):
        self.db.close()

    def test_blog_round_trip(self):
        ok, _ = core_tools.write_blog(self.spark_id, self.db, title="Hello", content="World body")
        self.assertTrue(ok)
        ok2, msg2 = core_tools.read_blogs(self.spark_id, self.db)
        self.assertIn("Hello", msg2)
        self.assertIn("World body", msg2)

    def test_event_propose_list_rsvp(self):
        # Spark starts at Central Plaza in the fixture
        ok, msg = execute_tool(self.spark_id, "propose_event",
                               {"title": "Picnic", "description": "fun"}, self.db, turn_number=1)
        self.assertTrue(ok, msg)
        eid = int(msg.split("#")[1].split(" ")[0])
        # Flora must be at Central Plaza to RSVP
        core_tools.go_to_place(self.flora_id, self.db, landmark_name="Central Plaza")
        ok2, _ = execute_tool(self.flora_id, "rsvp_event", {"event_id": eid}, self.db, turn_number=1)
        self.assertTrue(ok2)
        # Double RSVP blocked
        ok3, msg3 = execute_tool(self.flora_id, "rsvp_event", {"event_id": eid}, self.db, turn_number=1)
        self.assertFalse(ok3)
        ok4, listing = execute_tool(self.spark_id, "list_events", {}, self.db, turn_number=1)
        self.assertIn("Picnic", listing)

    def test_event_gated_off_plaza(self):
        core_tools.go_to_place(self.spark_id, self.db, landmark_name="Town Hall")
        ok, msg = execute_tool(self.spark_id, "propose_event",
                               {"title": "X", "description": "y"}, self.db, turn_number=1)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
