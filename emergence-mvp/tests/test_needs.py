"""
Tests for engine/needs.py — needs decay engine.

Run from project root:
    python tests/test_needs.py
"""
import sys
import os
import sqlite3
import time
import unittest

# Ensure the project root is on the path so imports work from any cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    ENERGY_DRAIN_SECONDS,
    KNOWLEDGE_DRAIN_SECONDS,
    INFLUENCE_DRAIN_SECONDS,
    DEATH_THRESHOLD_SECONDS,
)

# Production decay runs on the simulated clock with speed=1. These tests exercise the
# _decay math with an arbitrary speed multiplier (the `speed` param still exists), so we
# define a local test multiplier rather than importing a production constant.
SIMULATION_SPEED = 3600
from engine.needs import (
    _decay,
    calculate_needs,
    update_agent_needs,
    check_death,
    recharge_energy_reset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_db():
    """Return a fresh in-memory SQLite connection with the full schema applied."""
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "db",
        "schema.sql",
    )
    with open(schema_path) as f:
        schema = f.read()
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(schema)
    db.commit()
    return db


def _insert_landmark(db, name="TestLandmark", x=0.0, y=0.0):
    """Insert a minimal landmark and return its id."""
    cur = db.execute(
        "INSERT INTO landmarks (name, x, y) VALUES (?, ?, ?)",
        (name, x, y),
    )
    db.commit()
    return cur.lastrowid


def _insert_agent(
    db,
    landmark_id,
    *,
    name="TestAgent",
    personality="curious",
    last_energy_recharge_at=None,
    last_knowledge_at=None,
    last_influence_at=None,
    death_energy_zero_since=None,
    is_alive=1,
    created_at=None,
):
    """Insert a minimal agent and return its id."""
    if created_at is None:
        created_at = time.time()
    cur = db.execute(
        """INSERT INTO agents
           (name, personality, home_landmark_id, location_id,
            last_energy_recharge_at, last_knowledge_at, last_influence_at,
            death_energy_zero_since, is_alive, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name, personality, landmark_id, landmark_id,
            last_energy_recharge_at, last_knowledge_at, last_influence_at,
            death_energy_zero_since, is_alive, created_at,
        ),
    )
    db.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestDecayFunction(unittest.TestCase):
    """Unit tests for _decay."""

    def test_decay_known_value(self):
        """With speed=3600 and drain=108000, 1 real second elapsed -> ~0.0333."""
        # 1.0 * 3600 / 108000 = 0.03333...
        t0 = 1_000_000.0
        now = t0 + 1.0
        result = _decay(t0, ENERGY_DRAIN_SECONDS, now, SIMULATION_SPEED)
        self.assertAlmostEqual(result, 0.0333, delta=0.01)

    def test_decay_none_returns_full(self):
        """last_reset_at=None means fully depleted -> 1.0."""
        result = _decay(None, ENERGY_DRAIN_SECONDS, time.time(), SIMULATION_SPEED)
        self.assertEqual(result, 1.0)

    def test_decay_clamps_at_one(self):
        """Very old reset timestamp should clamp to 1.0, not exceed it."""
        t0 = 1.0          # ancient timestamp
        now = 1_000_000.0  # far in the future
        result = _decay(t0, ENERGY_DRAIN_SECONDS, now, SIMULATION_SPEED)
        self.assertEqual(result, 1.0)

    def test_decay_zero_elapsed(self):
        """Just recharged -> need is 0.0."""
        t0 = 1_000_000.0
        result = _decay(t0, ENERGY_DRAIN_SECONDS, t0, SIMULATION_SPEED)
        self.assertEqual(result, 0.0)


class TestCalculateNeeds(unittest.TestCase):
    """Tests for calculate_needs with a known in-memory DB."""

    def setUp(self):
        self.db = _build_db()
        lm_id = _insert_landmark(self.db)
        # Anchor all resets at t0
        self.t0 = 1_000_000.0
        self.speed = SIMULATION_SPEED  # 3600
        # Insert agent with reset timestamps all at t0
        self.agent_id = _insert_agent(
            self.db,
            lm_id,
            last_energy_recharge_at=self.t0,
            last_knowledge_at=self.t0,
            last_influence_at=self.t0,
        )

    def tearDown(self):
        self.db.close()

    def test_calculate_needs_known_timestamps(self):
        """After 10 real seconds with SIMULATION_SPEED=3600, verify each need."""
        elapsed = 10.0
        now = self.t0 + elapsed

        expected_energy    = elapsed * self.speed / ENERGY_DRAIN_SECONDS
        expected_knowledge = elapsed * self.speed / KNOWLEDGE_DRAIN_SECONDS
        expected_influence = elapsed * self.speed / INFLUENCE_DRAIN_SECONDS

        needs = calculate_needs(self.agent_id, self.db, now=now, speed=self.speed)

        self.assertAlmostEqual(needs["energy"],    expected_energy,    delta=0.001)
        self.assertAlmostEqual(needs["knowledge"], expected_knowledge, delta=0.001)
        self.assertAlmostEqual(needs["influence"], expected_influence, delta=0.001)

    def test_calculate_needs_null_timestamps(self):
        """Agent with NULL timestamps should return 1.0 for all needs."""
        db = _build_db()
        lm_id = _insert_landmark(db, name="LM2")
        agent_id = _insert_agent(
            db, lm_id,
            name="NullAgent",
            last_energy_recharge_at=None,
            last_knowledge_at=None,
            last_influence_at=None,
        )
        needs = calculate_needs(agent_id, db, now=self.t0, speed=self.speed)
        self.assertEqual(needs["energy"], 1.0)
        self.assertEqual(needs["knowledge"], 1.0)
        self.assertEqual(needs["influence"], 1.0)
        db.close()


class TestUpdateAgentNeeds(unittest.TestCase):
    """Tests for update_agent_needs — DB write and death timer management."""

    def setUp(self):
        self.db = _build_db()
        lm_id = _insert_landmark(self.db)
        self.t0 = 2_000_000.0
        self.speed = SIMULATION_SPEED
        self.agent_id = _insert_agent(
            self.db, lm_id,
            last_energy_recharge_at=self.t0,
        )

    def tearDown(self):
        self.db.close()

    def test_update_writes_needs_to_db(self):
        """update_agent_needs should persist computed values."""
        elapsed = 5.0
        now = self.t0 + elapsed
        needs = update_agent_needs(self.agent_id, self.db, now=now, speed=self.speed)
        row = self.db.execute(
            "SELECT energy_need FROM agents WHERE id=?", (self.agent_id,)
        ).fetchone()
        self.assertAlmostEqual(row["energy_need"], needs["energy"], delta=0.0001)

    def test_death_timer_set_when_energy_critical(self):
        """death_energy_zero_since should be set when energy first hits >= 0.999."""
        # Move far enough into the future that energy = 1.0
        # ENERGY_DRAIN_SECONDS=108000, speed=3600 -> full depletion at 30 real seconds
        now = self.t0 + 31.0
        update_agent_needs(self.agent_id, self.db, now=now, speed=self.speed)
        row = self.db.execute(
            "SELECT death_energy_zero_since FROM agents WHERE id=?",
            (self.agent_id,),
        ).fetchone()
        self.assertIsNotNone(row["death_energy_zero_since"])
        self.assertAlmostEqual(row["death_energy_zero_since"], now, delta=0.01)

    def test_death_timer_not_set_when_energy_ok(self):
        """death_energy_zero_since should remain NULL while energy is healthy."""
        now = self.t0 + 1.0  # barely any time elapsed
        update_agent_needs(self.agent_id, self.db, now=now, speed=self.speed)
        row = self.db.execute(
            "SELECT death_energy_zero_since FROM agents WHERE id=?",
            (self.agent_id,),
        ).fetchone()
        self.assertIsNone(row["death_energy_zero_since"])


class TestCheckDeath(unittest.TestCase):
    """Tests for check_death — death triggering and recovery."""

    def setUp(self):
        self.db = _build_db()
        lm_id = _insert_landmark(self.db)
        self.t0 = 3_000_000.0
        self.speed = SIMULATION_SPEED  # 3600

    def tearDown(self):
        self.db.close()

    def test_death_triggers_when_threshold_exceeded(self):
        """Test 5: Agent with energy depleted; after death timer reaches threshold, dies."""
        # death_energy_zero_since = t0
        # DEATH_THRESHOLD_SECONDS = 172800
        # Need (now - t0) * speed >= 172800
        # elapsed_real = 172800 / 3600 = 48 seconds
        lm_id = self.db.execute("SELECT id FROM landmarks LIMIT 1").fetchone()["id"]
        agent_id = _insert_agent(
            self.db, lm_id,
            name="DyingAgent",
            last_energy_recharge_at=None,  # energy is already 1.0
            death_energy_zero_since=self.t0,
            is_alive=1,
        )

        elapsed_real = DEATH_THRESHOLD_SECONDS / self.speed  # exactly 48 seconds
        now = self.t0 + elapsed_real + 1.0  # +1 to safely exceed threshold

        result = check_death(agent_id, self.db, now=now, speed=self.speed)
        self.assertTrue(result)

        row = self.db.execute(
            "SELECT is_alive FROM agents WHERE id=?", (agent_id,)
        ).fetchone()
        self.assertEqual(row["is_alive"], 0)

    def test_check_death_returns_false_if_already_dead(self):
        """If is_alive=0, check_death should return False without re-processing."""
        lm_id = self.db.execute("SELECT id FROM landmarks LIMIT 1").fetchone()["id"]
        agent_id = _insert_agent(
            self.db, lm_id,
            name="AlreadyDeadAgent",
            is_alive=0,
            death_energy_zero_since=self.t0,
        )
        now = self.t0 + 9999.0
        result = check_death(agent_id, self.db, now=now, speed=self.speed)
        self.assertFalse(result)

    def test_check_death_returns_false_before_threshold(self):
        """Agent at critical energy but timer hasn't reached threshold yet."""
        lm_id = self.db.execute("SELECT id FROM landmarks LIMIT 1").fetchone()["id"]
        agent_id = _insert_agent(
            self.db, lm_id,
            name="AlmostDeadAgent",
            last_energy_recharge_at=None,
            death_energy_zero_since=self.t0,
            is_alive=1,
        )
        # Only 10 real seconds elapsed -> 10 * 3600 = 36000 simulated < 172800
        now = self.t0 + 10.0
        result = check_death(agent_id, self.db, now=now, speed=self.speed)
        self.assertFalse(result)

    def test_death_recovery_clears_timer(self):
        """Test 6: After recharge_energy_reset, check_death returns False."""
        lm_id = self.db.execute("SELECT id FROM landmarks LIMIT 1").fetchone()["id"]
        agent_id = _insert_agent(
            self.db, lm_id,
            name="RecoveryAgent",
            last_energy_recharge_at=None,  # energy depleted
            death_energy_zero_since=self.t0,
            is_alive=1,
        )

        # Recharge clears the death timer
        recharge_energy_reset(agent_id, self.db, now=self.t0)

        # Verify DB state
        row = self.db.execute(
            "SELECT death_energy_zero_since, energy_need FROM agents WHERE id=?",
            (agent_id,),
        ).fetchone()
        self.assertIsNone(row["death_energy_zero_since"])
        self.assertEqual(row["energy_need"], 0.0)

        # Even at a time that would have exceeded the threshold, death should not fire
        now = self.t0 + 9999.0
        result = check_death(agent_id, self.db, now=now, speed=self.speed)
        self.assertFalse(result)


class TestRechargeEnergyReset(unittest.TestCase):
    """Tests for recharge_energy_reset."""

    def setUp(self):
        self.db = _build_db()
        lm_id = _insert_landmark(self.db)
        self.t0 = 4_000_000.0
        self.agent_id = _insert_agent(
            self.db, lm_id,
            last_energy_recharge_at=None,
            death_energy_zero_since=self.t0 - 100.0,
        )

    def tearDown(self):
        self.db.close()

    def test_recharge_resets_energy_and_clears_death_timer(self):
        """After recharge, energy_need=0.0 and death_energy_zero_since=NULL."""
        recharge_energy_reset(self.agent_id, self.db, now=self.t0)
        row = self.db.execute(
            "SELECT energy_need, last_energy_recharge_at, death_energy_zero_since "
            "FROM agents WHERE id=?",
            (self.agent_id,),
        ).fetchone()
        self.assertEqual(row["energy_need"], 0.0)
        self.assertAlmostEqual(row["last_energy_recharge_at"], self.t0, delta=0.01)
        self.assertIsNone(row["death_energy_zero_since"])

    def test_recharge_then_calculate_energy_zero(self):
        """After recharge, calculate_needs at the same 'now' yields energy=0.0."""
        recharge_energy_reset(self.agent_id, self.db, now=self.t0)
        needs = calculate_needs(
            self.agent_id, self.db, now=self.t0, speed=SIMULATION_SPEED
        )
        self.assertEqual(needs["energy"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
