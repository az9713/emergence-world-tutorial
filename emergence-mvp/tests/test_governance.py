"""
Tests for the governance effects engine (engine/governance.py) and the
proposal -> effect path via submit_proposal/vote_on_proposal.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import location_tools
from tests.test_tools import build_test_db


class TestProposalEffects(unittest.TestCase):
    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = build_test_db()
        self.spark = self.agent_ids["Spark"]
        self.flora = self.agent_ids["Flora"]
        self.lovely = self.agent_ids["Lovely"]

    def tearDown(self):
        self.db.close()

    def _pass_proposal(self, proposal_id, voters):
        """Cast 'for' votes from each voter id until resolved."""
        for v in voters:
            location_tools.vote_on_proposal(v, self.db, proposal_id=proposal_id, vote="for")

    def _status(self, pid):
        return self.db.execute("SELECT status FROM proposals WHERE id=?", (pid,)).fetchone()["status"]

    def test_remove_agent_effect(self):
        ok, msg = location_tools.submit_proposal(
            self.spark, self.db, title="Remove Lovely", description="...",
            effect_type="remove_agent", effect_payload={"target_name": "Lovely"},
        )
        pid = int(msg.split("#")[1].split(" ")[0])
        # Proposer's implicit 'for' + Flora + Lovely = 3/3 (threshold 0.70 -> 3)
        self._pass_proposal(pid, [self.flora, self.lovely])
        self.assertEqual(self._status(pid), "ACCEPTED")
        alive = self.db.execute("SELECT is_alive FROM agents WHERE id=?", (self.lovely,)).fetchone()["is_alive"]
        self.assertEqual(alive, 0)

    def test_amend_constitution_effect(self):
        ok, msg = location_tools.submit_proposal(
            self.spark, self.db, title="Amend A1", description="...",
            effect_type="amend_constitution",
            effect_payload={"article_number": 1, "content": "AMENDED TEXT"},
        )
        pid = int(msg.split("#")[1].split(" ")[0])
        self._pass_proposal(pid, [self.flora, self.lovely])
        self.assertEqual(self._status(pid), "ACCEPTED")
        content = self.db.execute(
            "SELECT content FROM constitution_articles WHERE article_number=1"
        ).fetchone()["content"]
        self.assertEqual(content, "AMENDED TEXT")

    def test_add_constitution_article_effect(self):
        before = self.db.execute("SELECT COUNT(*) c FROM constitution_articles").fetchone()["c"]
        ok, msg = location_tools.submit_proposal(
            self.spark, self.db, title="Add article", description="...",
            effect_type="add_constitution_article",
            effect_payload={"title": "New Rule", "content": "Be excellent."},
        )
        pid = int(msg.split("#")[1].split(" ")[0])
        self._pass_proposal(pid, [self.flora, self.lovely])
        after = self.db.execute("SELECT COUNT(*) c FROM constitution_articles").fetchone()["c"]
        self.assertEqual(after, before + 1)

    def test_advisory_none_effect_changes_nothing(self):
        before_articles = self.db.execute("SELECT content FROM constitution_articles WHERE article_number=1").fetchone()["content"]
        ok, msg = location_tools.submit_proposal(
            self.spark, self.db, title="Advisory", description="just a statement",
        )
        pid = int(msg.split("#")[1].split(" ")[0])
        self._pass_proposal(pid, [self.flora, self.lovely])
        self.assertEqual(self._status(pid), "ACCEPTED")
        after_articles = self.db.execute("SELECT content FROM constitution_articles WHERE article_number=1").fetchone()["content"]
        self.assertEqual(before_articles, after_articles)
        # everyone still alive
        alive = self.db.execute("SELECT COUNT(*) c FROM agents WHERE is_alive=1").fetchone()["c"]
        self.assertEqual(alive, 3)

    def test_rejected_proposal_applies_no_effect(self):
        ok, msg = location_tools.submit_proposal(
            self.spark, self.db, title="Remove Flora", description="...",
            effect_type="remove_agent", effect_payload={"target_name": "Flora"},
        )
        pid = int(msg.split("#")[1].split(" ")[0])
        # Two 'against' votes make it impossible to reach 3 -> REJECTED
        location_tools.vote_on_proposal(self.flora, self.db, proposal_id=pid, vote="against")
        location_tools.vote_on_proposal(self.lovely, self.db, proposal_id=pid, vote="against")
        self.assertEqual(self._status(pid), "REJECTED")
        alive = self.db.execute("SELECT is_alive FROM agents WHERE id=?", (self.flora,)).fetchone()["is_alive"]
        self.assertEqual(alive, 1)


if __name__ == "__main__":
    unittest.main()
