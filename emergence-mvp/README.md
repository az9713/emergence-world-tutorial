# Emergence World MVP

A scaled multi-agent LLM simulation in which three autonomous agents (Spark, Flora, Lovely) inhabit a small town, manage credits and energy needs, propose and vote on governance, compete in pitch cycles, and form relationships — all driven by a deterministic simulated clock. Multiple LLM providers are supported (Anthropic, OpenAI, Gemini), making provider-level behavioral comparison straightforward.

## ⭐ Featured: Gemini vs OpenAI — same world, different mind

Two 30-turn runs, **identical in every way except the foundation model** (same agents, world, tools, and `forced-governance` tuning). The result is the Emergence World thesis in miniature:

| | **Gemini 2.5 Flash** | **OpenAI gpt-4o-mini** |
|---|---|---|
| Final credits | **21 / 21 / 0 CC** | **0 / 0 / 0 CC** |
| Pitches submitted | 4 (cycle paid out) | **0** |
| Pattern | collaboration + norm formation | coordination without execution → collapse |
| Outcome | thriving economy | bankrupt; 10 failed theft attempts |

The same setup produced a **thriving cooperative economy** on Gemini and a **bankrupt all-talk collapse** on gpt-4o-mini — strong evidence that *picking the foundation model is the experiment.*

- 📊 **[Comparison & contrast →](runs/run-30turn-comparison.md)**
- 🟦 Gemini analysis: [`runs/run-30turn-analysis.md`](runs/run-30turn-analysis.md) · dialogue [`runs/conversations-30turn-tuned.txt`](runs/conversations-30turn-tuned.txt)
- 🟩 OpenAI analysis: [`runs/run-30turn-openai-analysis.md`](runs/run-30turn-openai-analysis.md) · dialogue [`runs/conversations-30turn-openai.txt`](runs/conversations-30turn-openai.txt)

Reproduce either: `python main.py --scenario forced-governance --turns 30 --log runs/my-run.txt` (set `LLM_PROVIDER` first).

## Setup

```bash
pip install -r requirements.txt
```

Copy the environment template and configure your provider:

```bash
cp .env.example .env
```

Edit `.env` and set `LLM_PROVIDER` to `anthropic`, `openai`, or `gemini`, then add the corresponding API key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`).

## Running the simulation

Seed the database, then start a run:

```bash
python db/seed.py
python main.py --turns 12
```

**Offline smoke test** (no API key required):

```bash
python main.py --dry-run --fresh --turns 6 --no-sleep
```

## CLI flags

| Flag | Description |
|------|-------------|
| `--turns N` | Number of agent turns to run (default 12) |
| `--fresh` | Re-seed the database before running |
| `--no-sleep` | Disable the real-time pause between turns |
| `--dry-run` | Use a scripted fake LLM (no API calls) |
| `--scenario NAME` | Apply a named experiment preset (see below) |
| `--log [FILE]` | Save the run transcript; bare `--log` auto-names `runs/run-<timestamp>.txt`, or pass a path |

## Tests

```bash
python tests/test_needs.py
python tests/test_tools.py
python tests/test_turn_engine.py
python tests/test_reactive_memory.py
python tests/test_governance.py
python tests/test_awi.py
```

All suites use injected fakes and in-memory databases — no API key or seeded `sim.db` required.

## Analysis

Generate a Markdown report from the most recent run:

```bash
python report.py
# Output: runs/report.md
```

Run a batch of simulations and compare AWI metrics across runs:

```bash
python batch.py --runs 3 --dry-run
# Output: comparison table + runs/batch-summary.csv
```

## Scenarios

Named experiment presets alter config knobs and/or seed parameters without changing the default code path. Pass `--scenario NAME` to `main.py` or `batch.py`:

| Name | What it changes |
|------|-----------------|
| `baseline` | No changes — pure default behaviour |
| `zero-sum` | Pitch rewards for 2nd and 3rd place set to 0 |
| `forced-governance` | Governance threshold lowered to 50%; Flora seeded with a memory pushing a restrictive proposal |
| `rescue-test` | All agents start with 1 CC to stress-test resource recovery |

## Reference

- `docs/emergence-design.md` — design knobs, behavioral notes, and debugging guide
- `runs/run-30turn-comparison.md` — **Gemini vs OpenAI** head-to-head
- `runs/run-30turn-analysis.md` — Gemini 30-turn analysis
- `runs/run-30turn-openai-analysis.md` — OpenAI 30-turn analysis
- `runs/` — full transcripts and conversation extracts for both runs
