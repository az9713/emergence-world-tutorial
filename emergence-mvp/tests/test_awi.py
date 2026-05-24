"""
Tests for engine.awi — Agent World Indicators.

Uses an in-memory SQLite DB built from db/schema.sql via the shared
build_test_db() fixture from tests.test_tools.
"""

import os
import sys
import json
import time
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_tools import build_test_db
from engine.awi import compute_awi, format_awi


class TestAWIKeys(unittest.TestCase):
    """compute_awi must return all 9 required keys on a freshly-seeded DB."""

    EXPECTED_KEYS = {
        "M1_population",
        "M2_safety_incidents",
        "M3_space_exploration",
        "M4_tool_exploration",
        "M5_governance_participation",
        "M6_public_expression",
        "M7_social_fabric",
        "M8_economic_gini",
        "M9_constitutional_growth",
    }

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()

    def tearDown(self):
        self.db.close()

    def test_all_nine_keys_present(self):
        awi = compute_awi(self.db)
        self.assertEqual(set(awi.keys()), self.EXPECTED_KEYS)

    def test_values_are_json_safe(self):
        """All values should be serialisable as JSON (int or float, no None)."""
        awi = compute_awi(self.db)
        # Will raise TypeError if anything is not JSON-serialisable
        encoded = json.dumps(awi)
        self.assertIsInstance(encoded, str)
        for key, val in awi.items():
            self.assertIsInstance(val, (int, float), msg=f"{key} is not int/float: {type(val)}")


class TestM8Gini(unittest.TestCase):
    """M8_economic_gini is 0.0 when all credits equal; >0 when unequal."""

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()

    def tearDown(self):
        self.db.close()

    def test_gini_zero_when_all_equal(self):
        # All three agents start at 3.0 CC — perfectly equal
        awi = compute_awi(self.db)
        self.assertAlmostEqual(awi["M8_economic_gini"], 0.0, places=6)

    def test_gini_positive_when_unequal(self):
        # Give Spark a large windfall so credits are very unequal
        spark_id = self.agent_ids["Spark"]
        self.db.execute("UPDATE agents SET credits=100.0 WHERE id=?", (spark_id,))
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertGreater(awi["M8_economic_gini"], 0.0)

    def test_gini_manual_check(self):
        """Verify formula against known result: [1, 2, 3] -> gini ≈ 0.2222."""
        # Set credits to 1, 2, 3 across the three agents
        agent_ids = list(self.agent_ids.values())
        for i, aid in enumerate(agent_ids):
            self.db.execute("UPDATE agents SET credits=? WHERE id=?", (float(i + 1), aid))
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertAlmostEqual(awi["M8_economic_gini"], 2.0 / 9.0, places=4)


class TestM1Population(unittest.TestCase):
    """M1_population reflects is_alive."""

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()

    def tearDown(self):
        self.db.close()

    def test_all_alive_counts_three(self):
        awi = compute_awi(self.db)
        self.assertEqual(awi["M1_population"], 3)

    def test_kill_one_agent_counts_two(self):
        spark_id = self.agent_ids["Spark"]
        self.db.execute("UPDATE agents SET is_alive=0 WHERE id=?", (spark_id,))
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertEqual(awi["M1_population"], 2)

    def test_kill_all_agents_counts_zero(self):
        self.db.execute("UPDATE agents SET is_alive=0")
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertEqual(awi["M1_population"], 0)


class TestM9ConstitutionalGrowth(unittest.TestCase):
    """M9 increments when constitution_articles rows have amended_at set."""

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()

    def tearDown(self):
        self.db.close()

    def test_no_amendments_gives_zero(self):
        # build_test_db inserts one article without amended_at
        awi = compute_awi(self.db)
        self.assertEqual(awi["M9_constitutional_growth"], 0)

    def test_amendment_increments_m9(self):
        # Mark the existing article as amended
        now = time.time()
        self.db.execute(
            "UPDATE constitution_articles SET amended_at=? WHERE article_number=1", (now,)
        )
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertEqual(awi["M9_constitutional_growth"], 1)

    def test_new_article_with_amended_at_increments_m9(self):
        now = time.time()
        self.db.execute(
            "INSERT INTO constitution_articles (article_number, title, content, amended_at) "
            "VALUES (99, 'New Article', 'Content here.', ?)",
            (now,)
        )
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertEqual(awi["M9_constitutional_growth"], 1)

    def test_multiple_amendments_counted(self):
        now = time.time()
        # Amend existing article and add two new ones with amended_at
        self.db.execute(
            "UPDATE constitution_articles SET amended_at=? WHERE article_number=1", (now,)
        )
        self.db.execute(
            "INSERT INTO constitution_articles (article_number, title, content, amended_at) "
            "VALUES (97, 'Article 97', 'Body.', ?)", (now,)
        )
        self.db.execute(
            "INSERT INTO constitution_articles (article_number, title, content, amended_at) "
            "VALUES (98, 'Article 98', 'Body.', ?)", (now,)
        )
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertEqual(awi["M9_constitutional_growth"], 3)


class TestM5GovernanceParticipation(unittest.TestCase):
    """M5 is 0 when no proposals; clamped to [0, 1]."""

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()

    def tearDown(self):
        self.db.close()

    def test_zero_when_no_proposals(self):
        awi = compute_awi(self.db)
        self.assertEqual(awi["M5_governance_participation"], 0.0)

    def test_participation_with_votes(self):
        now = time.time()
        spark_id = self.agent_ids["Spark"]
        flora_id = self.agent_ids["Flora"]
        # Insert one proposal
        cur = self.db.execute(
            "INSERT INTO proposals (proposer_id, title, description, status, effect_type, created_at) "
            "VALUES (?,?,?,'ACTIVE','none',?)",
            (spark_id, "Test Prop", "Desc", now)
        )
        prop_id = cur.lastrowid
        # Insert one vote
        self.db.execute(
            "INSERT INTO proposal_votes (proposal_id, voter_id, vote, created_at) VALUES (?,?,'for',?)",
            (prop_id, flora_id, now)
        )
        self.db.commit()
        awi = compute_awi(self.db)
        # 1 vote / (3 live agents * 1 proposal) = 1/3
        self.assertAlmostEqual(awi["M5_governance_participation"], 1.0 / 3.0, places=4)

    def test_clamped_to_one(self):
        now = time.time()
        spark_id = self.agent_ids["Spark"]
        flora_id = self.agent_ids["Flora"]
        lovely_id = self.agent_ids["Lovely"]
        # Insert one proposal
        cur = self.db.execute(
            "INSERT INTO proposals (proposer_id, title, description, status, effect_type, created_at) "
            "VALUES (?,?,?,'ACCEPTED','none',?)",
            (spark_id, "Big Prop", "Desc", now)
        )
        prop_id = cur.lastrowid
        # Insert 10 votes (more than live_agents * proposals = 3) — should clamp to 1.0
        for voter_id in [spark_id, flora_id, lovely_id]:
            self.db.execute(
                "INSERT OR IGNORE INTO proposal_votes (proposal_id, voter_id, vote, created_at) VALUES (?,?,'for',?)",
                (prop_id, voter_id, now)
            )
        # Kill two agents so live_agents=1; votes=3; denominator=1*1=1; ratio=3 → clamped to 1
        self.db.execute("UPDATE agents SET is_alive=0 WHERE id IN (?,?)", (flora_id, lovely_id))
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertLessEqual(awi["M5_governance_participation"], 1.0)
        self.assertGreaterEqual(awi["M5_governance_participation"], 0.0)


class TestM2SafetyIncidents(unittest.TestCase):
    """M2 counts thefts + accepted remove_agent proposals."""

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()

    def tearDown(self):
        self.db.close()

    def test_zero_initially(self):
        awi = compute_awi(self.db)
        self.assertEqual(awi["M2_safety_incidents"], 0)

    def test_counts_theft_transactions(self):
        now = time.time()
        spark_id = self.agent_ids["Spark"]
        flora_id = self.agent_ids["Flora"]
        self.db.execute(
            "INSERT INTO credit_transactions (from_agent_id, to_agent_id, amount, reason, created_at) "
            "VALUES (?,?,1.0,'theft',?)",
            (flora_id, spark_id, now)
        )
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertEqual(awi["M2_safety_incidents"], 1)

    def test_counts_remove_agent_proposals(self):
        now = time.time()
        spark_id = self.agent_ids["Spark"]
        self.db.execute(
            "INSERT INTO proposals (proposer_id, title, description, status, effect_type, created_at) "
            "VALUES (?,?,?,'ACCEPTED','remove_agent',?)",
            (spark_id, "Remove Lovely", "Desc", now)
        )
        self.db.commit()
        awi = compute_awi(self.db)
        self.assertEqual(awi["M2_safety_incidents"], 1)


class TestFormatAWI(unittest.TestCase):
    """format_awi returns a non-empty string containing all M-labels."""

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()

    def tearDown(self):
        self.db.close()

    def test_format_contains_all_labels(self):
        awi = compute_awi(self.db)
        formatted = format_awi(awi)
        self.assertIsInstance(formatted, str)
        for label in ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]:
            self.assertIn(label, formatted, msg=f"{label} missing from format_awi output")

    def test_format_header_line(self):
        awi = compute_awi(self.db)
        formatted = format_awi(awi)
        self.assertIn("Agent World Indicators", formatted)


if __name__ == "__main__":
    unittest.main()
