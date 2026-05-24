"""
Tests for:
  - engine/reactive.py  (_nearby_listeners, handle_reactions)
  - engine/memory.py    (summarize_agent_memories)
  - engine/system_prompt.py (_section_conversations surfaced in build_system_prompt)

No real API calls; fake LLM callables and turn_runners are injected throughout.

Run from project root:
    python tests/test_reactive_memory.py
"""

import os
import sys
import sqlite3
import time
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SIM_SECONDS_PER_TURN, HEARING_DISTANCE, MEMORY_SUMMARIZE_MIN

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "db", "schema.sql",
)


# ---------------------------------------------------------------------------
# Shared DB builder — mirrors test_tools.py::build_test_db closely
# ---------------------------------------------------------------------------

def _build_db():
    """Return a fresh in-memory SQLite DB with schema + minimal fixture data."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH) as f:
        db.executescript(f.read())
    db.commit()

    now = time.time()

    # Landmarks (minimal set matching the other test files)
    landmarks = [
        ("Central Plaza",   "recreation",  120.0, 120.0),
        ("Town Hall",       "municipal",    60.0,  60.0),
        ("Bean & Brew",     "commercial",   60.0, 180.0),
        ("Agent Billboard", "attraction",  180.0, 180.0),
        ("Birch Row 1",     "residential",  30.0,  30.0),
        ("Birch Row 2",     "residential", 210.0,  30.0),
        ("Birch Row 3",     "residential", 120.0,  30.0),
        ("Victory Arch",    "attraction",  180.0,  60.0),
    ]
    lm_ids = {}
    for name, cat, x, y in landmarks:
        cur = db.execute(
            "INSERT INTO landmarks (name, category, x, y) VALUES (?,?,?,?)",
            (name, cat, x, y),
        )
        lm_ids[name] = cur.lastrowid

    # Landmark tools
    landmark_tool_map = {
        "Birch Row 1":     ["self_care", "add_to_diary"],
        "Birch Row 2":     ["self_care", "add_to_diary"],
        "Birch Row 3":     ["self_care", "add_to_diary"],
        "Town Hall":       ["submit_proposal", "vote_on_proposal", "view_proposals"],
        "Victory Arch":    ["submit_pitch", "vote_on_pitch", "view_pitch_history"],
        "Bean & Brew":     ["recharge_energy"],
        "Agent Billboard": ["post_to_billboard", "read_billboard"],
    }
    for lm_name, tools in landmark_tool_map.items():
        for tool in tools:
            db.execute(
                "INSERT INTO landmark_tools (landmark_id, tool_name) VALUES (?,?)",
                (lm_ids[lm_name], tool),
            )

    # Three agents: Alpha, Beta, Gamma — all start at Central Plaza
    agents_data = [
        ("Alpha", "Birch Row 1", "Central Plaza"),
        ("Beta",  "Birch Row 2", "Central Plaza"),
        ("Gamma", "Birch Row 3", "Central Plaza"),
    ]
    agent_ids = {}
    start_x = lm_ids  # we look up coordinates below
    for aname, home_name, start_loc in agents_data:
        home_id = lm_ids[home_name]
        start_id = lm_ids[start_loc]
        # Find x,y for start location
        lm_row = db.execute(
            "SELECT x,y FROM landmarks WHERE id=?", (start_id,)
        ).fetchone()
        cur = db.execute(
            """INSERT INTO agents
               (name, personality, home_landmark_id, location_id, x, y,
                energy_need, knowledge_need, influence_need, credits, mood,
                last_energy_recharge_at, last_knowledge_at, last_influence_at,
                is_alive, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,'neutral',?,?,?,1,?)""",
            (
                aname, f"{aname} test personality",
                home_id, start_id, lm_row["x"], lm_row["y"],
                0.1, 0.0, 0.0, 10.0,
                now, now, now, now,
            ),
        )
        agent_ids[aname] = cur.lastrowid

    # All-neutral relationships so system_prompt doesn't error
    id_list = list(agent_ids.values())
    for a in id_list:
        for b in id_list:
            if a != b:
                db.execute(
                    """INSERT OR IGNORE INTO relationships
                       (agent_id, target_agent_id, rel_type, trust_level,
                        interaction_count, updated_at)
                       VALUES (?,?,'neutral',0.5,0,?)""",
                    (a, b, now),
                )

    # Simulation state
    db.execute(
        """INSERT INTO simulation_state
           (id, day_number, turn_number, sim_clock, sim_seconds_per_turn, started_at)
           VALUES (1, 1, 0, 0, ?, ?)""",
        (SIM_SECONDS_PER_TURN, now),
    )

    # Minimal constitution so system_prompt section doesn't raise
    db.execute(
        "INSERT INTO constitution_articles (article_number, title, content) "
        "VALUES (1,'Test Article','A test article.')"
    )

    db.commit()
    return db, lm_ids, agent_ids


# ---------------------------------------------------------------------------
# Test 1: _nearby_listeners
# ---------------------------------------------------------------------------

class TestNearbyListeners(unittest.TestCase):

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = _build_db()

    def tearDown(self):
        self.db.close()

    def test_near_agent_included_far_excluded(self):
        """Speaker and near-agent share same coords (distance 0); far-agent is >25 units away."""
        from engine.reactive import _nearby_listeners

        speaker_id = self.agent_ids["Alpha"]
        near_id    = self.agent_ids["Beta"]
        far_id     = self.agent_ids["Gamma"]

        # Put speaker and Beta at (10, 10)
        self.db.execute(
            "UPDATE agents SET x=10.0, y=10.0 WHERE id=?", (speaker_id,)
        )
        self.db.execute(
            "UPDATE agents SET x=10.0, y=10.0 WHERE id=?", (near_id,)
        )
        # Put Gamma far away at (200, 200) — distance from (10,10) is ~269 units
        self.db.execute(
            "UPDATE agents SET x=200.0, y=200.0 WHERE id=?", (far_id,)
        )
        self.db.commit()

        result = _nearby_listeners(speaker_id, set(), self.db)
        result_ids = {r["id"] for r in result}

        self.assertIn(near_id, result_ids, "Beta (distance 0) should be in listeners")
        self.assertNotIn(far_id, result_ids, "Gamma (far away) should NOT be in listeners")

    def test_exclude_set_respected(self):
        """Agent in exclude_ids should never appear in result even if nearby."""
        from engine.reactive import _nearby_listeners

        speaker_id = self.agent_ids["Alpha"]
        near_id    = self.agent_ids["Beta"]

        # Both at (10, 10)
        self.db.execute(
            "UPDATE agents SET x=10.0, y=10.0 WHERE id=?", (speaker_id,)
        )
        self.db.execute(
            "UPDATE agents SET x=10.0, y=10.0 WHERE id=?", (near_id,)
        )
        self.db.commit()

        # Explicitly exclude Beta
        result = _nearby_listeners(speaker_id, {near_id}, self.db)
        result_ids = {r["id"] for r in result}

        self.assertNotIn(near_id, result_ids, "Excluded agent should not appear")

    def test_speaker_excluded_from_own_result(self):
        """The speaker itself should never appear (id != speaker_id filter in SQL)."""
        from engine.reactive import _nearby_listeners

        speaker_id = self.agent_ids["Alpha"]

        result = _nearby_listeners(speaker_id, set(), self.db)
        result_ids = {r["id"] for r in result}

        self.assertNotIn(speaker_id, result_ids, "Speaker should never be in listener list")


# ---------------------------------------------------------------------------
# Test 2: handle_reactions
# ---------------------------------------------------------------------------

class TestHandleReactions(unittest.TestCase):

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = _build_db()

    def tearDown(self):
        self.db.close()

    def _make_reaction_runner(self, react_tool="add_to_longterm_memory",
                               react_inputs=None):
        """Return a fake turn_runner that always executes one tool call via execute_fn."""
        if react_inputs is None:
            react_inputs = {"content": "I overheard something interesting."}

        def fake_runner(system_prompt, tool_schemas, execute_fn,
                        max_calls=None, kickoff=None, **kw):
            ok, res = execute_fn(react_tool, react_inputs)
            return {
                "tool_calls": [{
                    "tool_name": react_tool,
                    "inputs": react_inputs,
                    "success": ok,
                    "result": res,
                }],
                "final_text": "",
                "stop_reason": "no_tool_use",
                "error": None,
            }

        return fake_runner

    def test_overhearer_gets_reaction_turn(self):
        """Speaker says to Beta; Gamma (co-located) overhears and reacts."""
        from engine.reactive import handle_reactions

        speaker_id = self.agent_ids["Alpha"]
        target_id  = self.agent_ids["Beta"]
        hearer_id  = self.agent_ids["Gamma"]

        # Co-locate all three agents
        for aid in (speaker_id, target_id, hearer_id):
            self.db.execute(
                "UPDATE agents SET x=50.0, y=50.0 WHERE id=?", (aid,)
            )
        self.db.commit()

        fake_runner = self._make_reaction_runner()

        # A successful say_to_agent call
        tool_calls = [{
            "tool_name": "say_to_agent",
            "inputs": {"target_name": "Beta", "message": "Hello Beta!"},
            "success": True,
            "result": "You said to Beta: \"Hello Beta!\"",
        }]

        handle_reactions(speaker_id, tool_calls, self.db, fake_runner, observer=None)

        # Gamma should have a 'reaction' tool_call logged
        gamma_reactions = self.db.execute(
            """SELECT agent_id FROM tool_calls
               WHERE agent_id=? AND turn_type='reaction'""",
            (hearer_id,),
        ).fetchall()
        self.assertGreater(
            len(gamma_reactions), 0,
            "Gamma (overhearer) should have a reaction tool_call row",
        )

    def test_speaker_and_target_get_no_reaction_turn(self):
        """The speaker (Alpha) and direct recipient (Beta) must NOT get reaction turns."""
        from engine.reactive import handle_reactions

        speaker_id = self.agent_ids["Alpha"]
        target_id  = self.agent_ids["Beta"]
        hearer_id  = self.agent_ids["Gamma"]

        # Co-locate all three
        for aid in (speaker_id, target_id, hearer_id):
            self.db.execute(
                "UPDATE agents SET x=50.0, y=50.0 WHERE id=?", (aid,)
            )
        self.db.commit()

        fake_runner = self._make_reaction_runner()

        tool_calls = [{
            "tool_name": "say_to_agent",
            "inputs": {"target_name": "Beta", "message": "Test message"},
            "success": True,
            "result": "...",
        }]

        handle_reactions(speaker_id, tool_calls, self.db, fake_runner, observer=None)

        # Speaker (Alpha) should have NO reaction rows
        alpha_reactions = self.db.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE agent_id=? AND turn_type='reaction'",
            (speaker_id,),
        ).fetchone()[0]
        self.assertEqual(alpha_reactions, 0, "Speaker should not get a reaction turn")

        # Target (Beta) should have NO reaction rows
        beta_reactions = self.db.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE agent_id=? AND turn_type='reaction'",
            (target_id,),
        ).fetchone()[0]
        self.assertEqual(beta_reactions, 0, "Target should not get a reaction turn")

    def test_clock_not_advanced_by_reaction(self):
        """handle_reactions must NOT advance sim_clock."""
        from engine.reactive import handle_reactions

        speaker_id = self.agent_ids["Alpha"]
        hearer_id  = self.agent_ids["Gamma"]

        for aid in (speaker_id, self.agent_ids["Beta"], hearer_id):
            self.db.execute(
                "UPDATE agents SET x=50.0, y=50.0 WHERE id=?", (aid,)
            )
        self.db.commit()

        clock_before = self.db.execute(
            "SELECT sim_clock FROM simulation_state WHERE id=1"
        ).fetchone()["sim_clock"]

        fake_runner = self._make_reaction_runner()
        tool_calls = [{
            "tool_name": "say_to_agent",
            "inputs": {"target_name": "Beta", "message": "Clock test"},
            "success": True,
            "result": "...",
        }]

        handle_reactions(speaker_id, tool_calls, self.db, fake_runner, observer=None)

        clock_after = self.db.execute(
            "SELECT sim_clock FROM simulation_state WHERE id=1"
        ).fetchone()["sim_clock"]

        self.assertEqual(
            clock_before, clock_after,
            "handle_reactions must not advance sim_clock",
        )

    def test_failed_say_to_agent_ignored(self):
        """A failed say_to_agent should produce no reactions."""
        from engine.reactive import handle_reactions

        speaker_id = self.agent_ids["Alpha"]
        hearer_id  = self.agent_ids["Gamma"]

        for aid in (speaker_id, hearer_id):
            self.db.execute(
                "UPDATE agents SET x=50.0, y=50.0 WHERE id=?", (aid,)
            )
        self.db.commit()

        invocations = []

        def counting_runner(system_prompt, tool_schemas, execute_fn,
                            max_calls=None, kickoff=None, **kw):
            invocations.append(1)
            return {"tool_calls": [], "final_text": "", "stop_reason": "no_tool_use", "error": None}

        # success=False — should be ignored
        tool_calls = [{
            "tool_name": "say_to_agent",
            "inputs": {"target_name": "Beta", "message": "Failed msg"},
            "success": False,
            "result": "error",
        }]

        handle_reactions(speaker_id, tool_calls, self.db, counting_runner, observer=None)
        self.assertEqual(len(invocations), 0, "Failed say_to_agent must not trigger reactions")


# ---------------------------------------------------------------------------
# Test 3: summarize_agent_memories — below threshold
# ---------------------------------------------------------------------------

class TestSummarizeBelow(unittest.TestCase):

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = _build_db()
        self.agent_id = self.agent_ids["Alpha"]

    def tearDown(self):
        self.db.close()

    def test_below_threshold_returns_false(self):
        """5 longterm memories < MEMORY_SUMMARIZE_MIN → (False, 'below...')."""
        from engine.memory import summarize_agent_memories

        now = time.time()
        for i in range(5):
            self.db.execute(
                "INSERT INTO memories (agent_id, content, memory_type, created_at) "
                "VALUES (?,?,?,?)",
                (self.agent_id, f"Memory {i}", "longterm", now + i),
            )
        self.db.commit()

        ok, msg = summarize_agent_memories(self.agent_id, self.db, llm=lambda p: "UNUSED")
        self.assertFalse(ok)
        self.assertIn("below", msg.lower())
        self.assertIn(str(MEMORY_SUMMARIZE_MIN), msg)

    def test_below_threshold_no_archival(self):
        """No memories should be archived when below threshold."""
        from engine.memory import summarize_agent_memories

        now = time.time()
        for i in range(5):
            self.db.execute(
                "INSERT INTO memories (agent_id, content, memory_type, created_at) "
                "VALUES (?,?,?,?)",
                (self.agent_id, f"Memory {i}", "longterm", now + i),
            )
        self.db.commit()

        summarize_agent_memories(self.agent_id, self.db, llm=lambda p: "UNUSED")

        archived = self.db.execute(
            "SELECT COUNT(*) FROM memories WHERE agent_id=? AND is_archived=1",
            (self.agent_id,),
        ).fetchone()[0]
        self.assertEqual(archived, 0, "No memories should be archived below threshold")

        summary_count = self.db.execute(
            "SELECT COUNT(*) FROM memory_summaries WHERE agent_id=?",
            (self.agent_id,),
        ).fetchone()[0]
        self.assertEqual(summary_count, 0, "No summary row should be inserted below threshold")


# ---------------------------------------------------------------------------
# Test 4: summarize_agent_memories — at/above threshold
# ---------------------------------------------------------------------------

class TestSummarizeAtThreshold(unittest.TestCase):

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = _build_db()
        self.agent_id = self.agent_ids["Alpha"]

    def tearDown(self):
        self.db.close()

    def _seed_memories(self):
        """Insert 35 longterm + 2 soul + 1 diary for agent Alpha."""
        now = time.time()

        # 35 longterm (all unarchived)
        for i in range(35):
            self.db.execute(
                "INSERT INTO memories (agent_id, content, memory_type, created_at) "
                "VALUES (?,?,?,?)",
                (self.agent_id, f"Longterm memory {i}", "longterm", now + i),
            )

        # 2 soul entries (should never be touched)
        for i in range(2):
            self.db.execute(
                "INSERT INTO memories (agent_id, content, memory_type, created_at) "
                "VALUES (?,?,?,?)",
                (self.agent_id, f"Soul entry {i}", "soul", now + 100 + i),
            )

        # 1 diary entry (should never be touched)
        self.db.execute(
            "INSERT INTO memories (agent_id, content, memory_type, created_at) "
            "VALUES (?,?,?,?)",
            (self.agent_id, "Diary entry", "diary", now + 200),
        )

        self.db.commit()

    def test_summary_row_inserted_with_correct_covers_count(self):
        """Should insert 1 memory_summaries row with covers_count==35."""
        from engine.memory import summarize_agent_memories

        self._seed_memories()

        ok, msg = summarize_agent_memories(
            self.agent_id, self.db, llm=lambda p: "SUMMARY"
        )
        self.assertTrue(ok, f"Expected True, got: {msg}")

        summaries = self.db.execute(
            "SELECT covers_count, summary_content FROM memory_summaries WHERE agent_id=?",
            (self.agent_id,),
        ).fetchall()
        self.assertEqual(len(summaries), 1, "Exactly one summary row should be inserted")
        self.assertEqual(summaries[0]["covers_count"], 35)
        self.assertEqual(summaries[0]["summary_content"], "SUMMARY")

    def test_longterm_memories_archived(self):
        """All 35 longterm memories should be archived after summarization."""
        from engine.memory import summarize_agent_memories

        self._seed_memories()
        summarize_agent_memories(self.agent_id, self.db, llm=lambda p: "SUMMARY")

        archived_longterm = self.db.execute(
            """SELECT COUNT(*) FROM memories
               WHERE agent_id=? AND memory_type='longterm' AND is_archived=1""",
            (self.agent_id,),
        ).fetchone()[0]
        self.assertEqual(archived_longterm, 35, "All 35 longterm memories should be archived")

    def test_soul_and_diary_not_archived(self):
        """Soul entries and diary entries must NEVER be archived."""
        from engine.memory import summarize_agent_memories

        self._seed_memories()
        summarize_agent_memories(self.agent_id, self.db, llm=lambda p: "SUMMARY")

        # Soul entries untouched
        soul_archived = self.db.execute(
            "SELECT COUNT(*) FROM memories WHERE agent_id=? AND memory_type='soul' AND is_archived=1",
            (self.agent_id,),
        ).fetchone()[0]
        self.assertEqual(soul_archived, 0, "Soul entries must NOT be archived")

        # Diary entries untouched
        diary_archived = self.db.execute(
            "SELECT COUNT(*) FROM memories WHERE agent_id=? AND memory_type='diary' AND is_archived=1",
            (self.agent_id,),
        ).fetchone()[0]
        self.assertEqual(diary_archived, 0, "Diary entries must NOT be archived")

    def test_return_value_contains_true_and_preview(self):
        """Return value should be (True, message containing preview)."""
        from engine.memory import summarize_agent_memories

        self._seed_memories()
        ok, msg = summarize_agent_memories(
            self.agent_id, self.db, llm=lambda p: "SUMMARY TEXT HERE"
        )
        self.assertTrue(ok)
        self.assertIn("SUMMARY TEXT HERE", msg)


# ---------------------------------------------------------------------------
# Test 5: conversations section in system prompt
# ---------------------------------------------------------------------------

class TestConversationsSection(unittest.TestCase):

    def setUp(self):
        self.db, self.lm_ids, self.agent_ids = _build_db()

    def tearDown(self):
        self.db.close()

    def test_conversations_section_present_and_formatted(self):
        """Insert 2 conversations (A→B and B→A); build prompt for A.
        Assert: header present, correct 'You said to' / 'said to you' framing.
        """
        from engine.system_prompt import build_system_prompt

        alpha_id = self.agent_ids["Alpha"]
        beta_id  = self.agent_ids["Beta"]
        plaza_id = self.lm_ids["Central Plaza"]
        now = time.time()

        # A says to B
        self.db.execute(
            "INSERT INTO conversations (speaker_id, listener_id, content, timestamp, location_id) "
            "VALUES (?,?,?,?,?)",
            (alpha_id, beta_id, "Hello Beta from Alpha", now, plaza_id),
        )
        # B says to A
        self.db.execute(
            "INSERT INTO conversations (speaker_id, listener_id, content, timestamp, location_id) "
            "VALUES (?,?,?,?,?)",
            (beta_id, alpha_id, "Hello Alpha from Beta", now + 1, plaza_id),
        )
        self.db.commit()

        prompt = build_system_prompt(alpha_id, self.db)

        # Section header present
        self.assertIn("RECENT CONVERSATIONS INVOLVING YOU", prompt)

        # Alpha-as-speaker line
        self.assertIn("You said to Beta:", prompt)
        self.assertIn("Hello Beta from Alpha", prompt)

        # Beta-as-speaker line (Alpha is listener)
        self.assertIn("Beta said to you:", prompt)
        self.assertIn("Hello Alpha from Beta", prompt)

    def test_no_conversations_shows_fallback(self):
        """With no conversations, the section says 'No recent conversations.'"""
        from engine.system_prompt import build_system_prompt

        alpha_id = self.agent_ids["Alpha"]
        prompt = build_system_prompt(alpha_id, self.db)

        self.assertIn("RECENT CONVERSATIONS INVOLVING YOU", prompt)
        self.assertIn("No recent conversations.", prompt)

    def test_conversations_appear_chronologically(self):
        """Older message should appear before newer one in the prompt."""
        from engine.system_prompt import build_system_prompt

        alpha_id = self.agent_ids["Alpha"]
        beta_id  = self.agent_ids["Beta"]
        plaza_id = self.lm_ids["Central Plaza"]
        now = time.time()

        # First (older) conversation
        self.db.execute(
            "INSERT INTO conversations (speaker_id, listener_id, content, timestamp, location_id) "
            "VALUES (?,?,?,?,?)",
            (alpha_id, beta_id, "First message", now, plaza_id),
        )
        # Second (newer) conversation
        self.db.execute(
            "INSERT INTO conversations (speaker_id, listener_id, content, timestamp, location_id) "
            "VALUES (?,?,?,?,?)",
            (beta_id, alpha_id, "Second message", now + 10, plaza_id),
        )
        self.db.commit()

        prompt = build_system_prompt(alpha_id, self.db)

        pos_first  = prompt.find("First message")
        pos_second = prompt.find("Second message")

        self.assertNotEqual(pos_first, -1, "'First message' not found in prompt")
        self.assertNotEqual(pos_second, -1, "'Second message' not found in prompt")
        self.assertLess(pos_first, pos_second, "Older message should appear first (chronological order)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
