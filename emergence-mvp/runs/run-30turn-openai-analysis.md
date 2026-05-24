# 30-Turn Run Analysis — OpenAI (gpt-4o-mini)

**Provider:** OpenAI `gpt-4o-mini` (`LLM_PROVIDER=openai`)
**Turns:** 30 (3 agents round-robin, 10 turns each)
**Tuning:** `--scenario forced-governance` — identical knobs to the earlier Gemini tuned run:
- `GOVERNANCE_THRESHOLD = 0.50` (2/3 majority passes → coalitions possible)
- Flora seeded with **active opposition** to Spark, plus a dispute seed pushing her to file a Town Hall proposal

This run is a **direct provider comparison**: same world, same rules, same tuning as the Gemini run — only the foundation model changed. Compare with `run-30turn-analysis.md` (Gemini).

**Artifacts:** `runs/run-30turn-openai.txt` (full log), `runs/conversations-30turn-openai.txt` (93 exchanges), `sim.db`.

---

## Headline

`gpt-4o-mini` produced a **"coordination without execution" collapse** — the exact Season-1 GPT failure signature. The agents talked constantly, organized meetings and events, and *discussed* contribution and accountability — but **never submitted a single pitch or governance proposal**, earned no credits, spent everything they had on energy, and ended the run **collectively broke (0 CC each)**, with desperate, futile theft attempts as the economy cratered. Nobody died — but only because 30 turns wasn't quite long enough for the starvation they were heading into.

---

## Final Outcome

| Agent | Credits (start → end) | Energy need | Status |
|-------|----------------------|-------------|--------|
| **Spark** | 3 → **0 CC** | 40% | alive |
| **Flora** | 3 → **0 CC** | 40% | alive |
| **Lovely** | 3 → **0 CC** | **80%** | alive (but cornered) |

- **220 tool calls, 32 failures (~15%)** — notably higher than Gemini's ~4%. `gpt-4o-mini` is sloppier with location-gating and tool inputs.
- **0 pitches submitted. 0 proposals submitted.** (M5 governance participation: 0%.)
- **All credits spent on energy recharges** (17 successful + 8 that failed at 0 CC). No income source was ever used → the economy ran dry.
- **10 theft attempts, all failed** — everyone was already broke ("X has no credits to steal").

---

## What Actually Emerged

1. **Hyperactivity without contribution.** `gpt-4o-mini` was *busy* — 94 `say_to_agent`, 38 `add_to_todo`, plus events and a blog (M4 tool exploration 11.0/agent, higher than Gemini). But the activity was **meta**: proposing "Innovative Ideas Town Hall" and "Team Brainstorming Session" *events*, talking about collaboration — never the economic actions (pitch, recharge-budgeting) that actually matter for survival.

2. **Economic death spiral.** With no pitch income, the only credit movement was *outflow* — repeated energy recharges drained all three agents to 0 CC. Once broke, they couldn't recharge further (8 failed attempts at 0 CC), and Lovely's energy climbed to 80%. The world was sliding toward collective starvation.

3. **Theft emerged — and was inert.** Agents reached for the `steal` tool **10 times** (desperation/conflict surfacing!), but every attempt failed because mutual poverty meant there was nothing to steal. Conflict *appeared* but had no fuel. (M2 safety incidents = 0 because no theft succeeded.)

4. **Flora's persona partly held** — her accountability voice came through ("without accountability…", "verifiable contributions") and 2 relationships were recorded via `update_relationship`. But she **never acted on the seeded directive** to file a Town Hall proposal. The seed shaped her *talk*, not her *actions*.

---

## Why It Played Out This Way

- **The defining trait of `gpt-4o-mini` here is weak agentic execution.** It defaults to organizing and discussing rather than committing to the consequential tools (`submit_pitch`, `submit_proposal`). This is the same pattern Season 1 saw in the GPT world ("coordination language without execution"), and it's stronger in this smaller/older model.
- **The forced-governance tuning had no effect** — because exercising it requires *submitting a proposal*, which never happened. You can't weaponize a 2/3 threshold if nobody legislates. The sharpened Flora seed produced pointed dialogue but no `submit_proposal` call.
- **No income + mandatory upkeep = ruin.** Energy recharge is the one unavoidable spend; pitches are the only income. Skipping pitches while recharging is a guaranteed slide to 0 CC. Gemini avoided this by actually pitching (and triggering the 20/10/10 payout); `gpt-4o-mini` did not.
- **Higher tool-error rate** compounded the waste: it repeatedly tried `pay_agent("Bean & Brew")` (5×) even after our description fix, mis-typed an agent name ("Flor"), and called location-gated tools from the wrong place.

---

## Gemini vs OpenAI — same knobs, different model

| Dimension | Gemini 2.5 Flash | OpenAI gpt-4o-mini |
|-----------|------------------|--------------------|
| Concrete deliverable | Built a "Hello World" web service (split endpoints) | Proposed *meetings* (events); no deliverable |
| Pitches submitted | 4 (full cycle settled, 20/10/10 paid) | **0** |
| Governance proposals | 0 | **0** |
| End credits | 21 / 21 / 0 CC | **0 / 0 / 0 CC** |
| Theft | none | 10 attempts (all failed — everyone broke) |
| Tool-call failure rate | ~4% | ~15% |
| Dominant behavior | collaboration + norm formation | coordination + economic collapse |
| Trajectory | stable, accumulating wealth | sliding toward starvation |

Both models *talk* a lot and both skew cooperative rather than combative. The decisive difference is **execution**: Gemini converted talk into the load-bearing economic actions; `gpt-4o-mini` did not, and the economy collapsed as a result.

---

## Tool Gaps & Observations (this run)

| Issue | Evidence | Note |
|-------|----------|------|
| Recharge confusion persists on weaker model | `pay_agent("Bean & Brew")` tried 5× despite the A2 description fix | Prompt-level clarity isn't enough for gpt-4o-mini; consider a hard guard hint |
| Todo churn returns | 38 `add_to_todo`, `complete_todo` barely used | The completion tool exists (A1) but the model doesn't reach for it |
| No income behavior | 0 `submit_pitch` in 30 turns | Model needs a stronger nudge toward the economy, or a system-prompt directive |
| Higher malformed-input rate | "Flor" truncated name, wrong-location calls | Inherent to the smaller model; all non-fatal (logged, sim continues) |

---

## Takeaways for Operators & Builders

- **Model choice dominates outcome far more than the tuning knobs.** The same `forced-governance` setup produced a wealthy, collaborative Gemini world and a bankrupt, all-talk OpenAI world. Picking the foundation model *is* the experiment.
- **`gpt-4o-mini` is a poor fit for survival-economy simulations** without scaffolding — it under-executes the consequential tools. For a serious OpenAI run, use a stronger model (`gpt-4o`/`gpt-4.1`) or add a system-prompt directive that forces economic action ("you must submit a pitch each cycle or you will go broke").
- **The collapse is itself a valuable result** — it reproduces the Season-1 GPT-world failure mode in miniature, on a laptop, in ~30 turns. That makes this MVP a cheap reproduction rig for studying *why* some model societies starve.

---

## Appendix — Key Data

**Top tools:** say_to_agent 94, add_to_todo 38, go_to_place 19, recharge_energy 17, list_events 17, **steal 10**, pay_agent 6, update_relationship 4, rsvp_event 4, propose_event 4.

**Credit transactions:** all `energy_recharge` (−1 CC each) plus one peer payment ("Pay for coffee to recharge my energy", Lovely→Spark 1 CC). **No pitch rewards** (no pitches). **No successful thefts.**

**AWI:** M1 alive 3 · M2 safety incidents 0 · M3 space 3.0 landmarks/agent · M4 tools 11.0/agent · M5 governance 0% · M6 expression 1 post · M7 social fabric 2 · M8 Gini 0.0000 (everyone equally broke) · M9 constitutional growth 0.

**Failures (32):** steal 10 (no credits to steal), recharge 8 (0 CC), list_events 6 (wrong location), pay_agent 5 (paid the café), say_to_agent 1 (typo'd name), rsvp 1 (duplicate), read_billboard 1 (wrong location).
