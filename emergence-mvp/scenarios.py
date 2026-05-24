"""Named experiment presets for the Emergence World simulation.

Usage:
    from scenarios import apply_scenario, list_scenarios

    seed_overrides = apply_scenario("forced-governance")
    from db.seed import seed
    seed(seed_overrides)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

# Each preset declares:
#   "config": dict of config-module attribute overrides (applied via setattr)
#   "seed":   dict of seed() overrides (starting_credits, starting_energy_need,
#             extra_memory_seeds, agent_providers)
SCENARIOS = {
    "baseline": {
        "config": {},
        "seed": {},
    },
    "zero-sum": {
        "config": {
            "PITCH_REWARD_SECOND": 0,
            "PITCH_REWARD_THIRD": 0,
        },
        "seed": {},
    },
    "forced-governance": {
        "config": {
            "GOVERNANCE_THRESHOLD": 0.50,
        },
        "seed": {
            "extra_memory_seeds": {
                "Flora": [
                    "Spark's proposals waste shared credits. I will push a Town Hall proposal to formally restrict uncoordinated spending, and I expect a vote."
                ],
            },
        },
    },
    "rescue-test": {
        "config": {},
        "seed": {
            "starting_credits": 1.0,
        },
    },
}


def apply_scenario(name):
    """Apply config overrides for the named scenario via setattr and return the
    seed-overrides dict for passing to seed().

    Raises ValueError listing valid names if the scenario is unknown.

    Note: setattr patches the config module object, which updates code that reads
    config.ATTR at call time. Modules that bound config values at import time via
    'from config import X' will NOT see the updated values — those are handled by
    the coordinator's wiring.
    """
    if name not in SCENARIOS:
        valid = ", ".join(sorted(SCENARIOS.keys()))
        raise ValueError(f"Unknown scenario {name!r}. Valid names: {valid}")

    preset = SCENARIOS[name]

    for attr, value in preset["config"].items():
        setattr(config, attr, value)

    return preset["seed"]


def list_scenarios():
    """Return a sorted list of available scenario names."""
    return sorted(SCENARIOS.keys())
