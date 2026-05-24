# Same World, Different Mind — Gemini vs OpenAI (30-Turn Comparison)

Two 30-turn runs of the Emergence World MVP, **identical in every way except the foundation model**. Same 3 agents (Spark, Flora, Lovely), same world, same tools, and the **same tuning** (`forced-governance` scenario: governance threshold 0.50 + a sharpened Flora seeded to oppose Spark). Only `LLM_PROVIDER` changed.

This is the core Emergence World thesis in miniature — *the foundation model is the only experimental variable* — reproduced on a laptop in ~30 turns.

- **Gemini analysis:** [`run-30turn-analysis.md`](run-30turn-analysis.md) · dialogue [`conversations-30turn-tuned.txt`](conversations-30turn-tuned.txt)
- **OpenAI analysis:** [`run-30turn-openai-analysis.md`](run-30turn-openai-analysis.md) · dialogue [`conversations-30turn-openai.txt`](conversations-30turn-openai.txt)

---

## Outcome at a glance

| Dimension | **Gemini 2.5 Flash** | **OpenAI gpt-4o-mini** |
|-----------|----------------------|------------------------|
| Final credits | **21 / 21 / 0 CC** | **0 / 0 / 0 CC** |
| Survivors | 3 / 3 (stable, wealthy) | 3 / 3 (broke, sliding toward starvation) |
| Pitches submitted | **4** (cycle settled, 20/10/10 paid out) | **0** |
| Governance proposals | 0 | 0 |
| Concrete deliverable | Built a "Hello World" web service (split endpoints) | None — only *proposed meetings* |
| Theft | none | **10 attempts, all failed** (everyone broke) |
| Tool-call failure rate | ~4% | ~15% |
| Dominant pattern | **collaboration + norm formation** | **coordination without execution → collapse** |
| Trajectory | accumulating wealth | economic death spiral |

---

## How each world behaved

### Gemini: build, then prosper
Spark proposed a joint project; Flora accepted *on her terms* ("results, not just activity"); they **split a real deliverable** (a "Hello World" web service — Spark the `/` endpoint, Flora `/info`). All three submitted pitches, voted reciprocally, and the cycle paid out 20/10/10 CC. A group **norm formed** around evidence-verification. Emergent **inequality** appeared — Lovely, the facilitator, did unpaid labor and ended broke while the two producers got rich. Flora's seeded antagonism **sublimated into productive scrutiny**: she demanded evidence, verified it, then supported Spark.

### OpenAI: talk, schedule, starve
gpt-4o-mini was *hyperactive* but **meta** — it proposed an "Idea Jam Session," then a "Team Brainstorming Session," and spent ~90 messages trying to **schedule a meeting that never happened**. It **never submitted a pitch** (no income) while repeatedly recharging energy (the one mandatory spend), draining all three agents to **0 CC**. Once broke, all three reached for the `steal` tool **10 times** — every attempt failing because mutual poverty left nothing to rob. The world was sliding toward collective starvation when the run ended.

---

## The decisive difference: execution, not disposition

Both models are **cooperative, talkative, and non-combative** — neither produced the explosive conflict the tuning was designed to provoke (and on both, governance went *unused* — zero proposals, so the 0.50 threshold never mattered). The split is entirely about **converting talk into consequential action**:

- **Gemini** reached for the load-bearing economic tools (`submit_pitch`, budgeted `recharge_energy`) → income → stability → emergent social structure.
- **gpt-4o-mini** stayed in the meta-layer (events, blogs, scheduling, discussion) → no income → bankruptcy → desperation.

This reproduces the **Season-1 GPT-world failure signature** — *"coordination language without execution"* — and contrasts it with a model that executes. It is strong evidence for the project's central claim: **picking the foundation model *is* the experiment.** The same world, rules, personalities, and tuning yield a thriving cooperative economy or a bankrupt talk-shop depending only on which mind drives the agents.

---

## Drama (read the dialogue, not just the metrics)

The numbers read as a dry collapse, but the OpenAI dialogue has a distinct low-key drama:

- **Flora's whisper campaign** — she repeatedly warns Lovely about Spark *behind his back*: *"Careful, Lovely. Spark's actions often lack accountability."* Her seeded antagonism manifested as a quiet cold war of insinuation rather than open confrontation.
- **Beckettian gridlock** — Flora blocks all action pending an "accountability framework" that never materializes; Spark tries to "set a time to meet" dozens of times; the meeting never happens, nothing is built.
- **Dignified collapse + a final mercy** — as credits hit zero, Lovely begs *"Could you help me out with just one credit?"* and Spark gives his last one. Meanwhile, all three were *silently attempting to rob each other* — civil words on the surface, desperate larceny underneath.

Gemini's drama, by contrast, was **constructive tension**: Flora's scrutiny forcing a real evidence norm, and the quiet injustice of the community-builder ending up broke.

---

## Practical guidance

- **For a thriving world:** Gemini 2.5 Flash (or a strong model) works out of the box.
- **For OpenAI:** `gpt-4o-mini` needs scaffolding — use `gpt-4o`/`gpt-4.1`, or add a system-prompt directive forcing economic action ("submit a pitch each cycle or you will go broke").
- **To study failure:** the gpt-4o-mini run is a cheap, ~30-turn reproduction of the GPT-world starvation dynamic — useful as a test rig for *why* some model societies collapse.
- **To get sharper conflict on either:** the tuning knobs aren't enough; force governance into play (a dispute that *requires* a vote) or make the economy genuinely zero-sum (single pitch winner), so scarcity compels someone to actually strike.
