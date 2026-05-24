import math
import os


def _load_dotenv():
    """Load KEY=VALUE pairs from a .env file at the project root into os.environ.
    Zero-dependency; does not overwrite variables already set in the environment.
    Imported-side-effect: runs on first import of config, so ANTHROPIC_API_KEY in
    .env is available before any code reads it."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


_load_dotenv()

CONCURRENT_AGENTS = 1
HEARING_DISTANCE = 25.0
MAX_OVERHEARD_LISTENERS = 4
TURN_TOOL_LIMIT = 30
REACTION_TOOL_LIMIT = 2

ENERGY_DRAIN_SECONDS = 108000     # 30 hours to 100%
KNOWLEDGE_DRAIN_SECONDS = 86400   # 24 hours to 100%
INFLUENCE_DRAIN_SECONDS = 129600  # 36 hours to 100%
DEATH_THRESHOLD_SECONDS = 172800  # 48 hours at 100% energy = death

# Canonical Emergence World invariant: 70% supermajority of live agents.
# (Experiments that want coalition dynamics — e.g. 0.50 so a 2/3 majority passes —
# should set this via a scenario preset rather than changing the baseline here.)
GOVERNANCE_THRESHOLD = 0.70
MEMORY_SUMMARIZE_MIN = 30
MEMORY_BATCH_SIZE = 500

BOOST_COST_CC = 1
RECHARGE_COST_CC = 1
MAX_STEAL_CC = 10   # cap per theft via the `steal` tool
PITCH_REWARD_FIRST = 20
PITCH_REWARD_SECOND = 10
PITCH_REWARD_THIRD = 10

# Time model: the world advances a fixed amount of SIMULATED time per turn,
# independent of how long the LLM call takes in real wall-clock time. This keeps
# needs decay and the economy deterministic and reproducible — an agent's survival
# depends on its choices, not on API latency.
SIM_SECONDS_PER_TURN = 7200  # 2 simulated hours per turn
# Derived pacing at this rate: 1 sim day = 86400s = 12 turns. A 2-day pitch cycle
# settles by ~turn 25. Energy (30hr drain) goes from 30% -> critical by ~turn 6,
# 100% by ~turn 11; death (48hr at 100%) would land ~turn 35 if an agent never
# recharges. So a 30-turn run shows real energy pressure + one full pitch cycle.
TURN_SLEEP_SECONDS = 2       # real seconds between turns (for observability only)
SECONDS_PER_SIM_DAY = 86400

DB_PATH = "sim.db"

# --- LLM provider selection ---------------------------------------------------
# The foundation model is the only experimental variable (Season 1 ran Claude,
# Gemini, Grok, and GPT in parallel). Choose a provider to control cost/behavior.
# Override any of these in .env, e.g.  LLM_PROVIDER=gemini
# Supported: "anthropic", "openai", "gemini".
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()

# Per-provider model ids (overridable via .env). Defaults favor cheaper models for
# the non-Anthropic providers since the whole point of choosing them is cost.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Gemini is reached through its OpenAI-compatible endpoint, so the same OpenAI SDK
# tool-calling path serves both OpenAI and Gemini (one adapter, two providers).
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
