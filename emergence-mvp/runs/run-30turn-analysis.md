# 30-Turn Run Analysis — Tuned for Conflict

**Provider:** Gemini 2.5 Flash (`LLM_PROVIDER=gemini`)
**Turns:** 30 (3 agents round-robin, 10 turns each)
**Experimental changes from canonical config:**
- `GOVERNANCE_THRESHOLD` lowered `0.70 → 0.50` (with 3 agents, a 2/3 majority now passes → coalitions possible)
- Flora's seed memory sharpened from passive ("I'll be watching") to **active conditional opposition** against Spark ("I will not vote for, fund, or rescue him until he produces verifiable output")

**Artifacts:** `runs/run-30turn-tuned.txt` (full terminal log), `runs/conversations-30turn-tuned.txt` (dialogue only), `sim.db` (structured record).

---

## Headline

The simulation produced **genuine emergent behavior — but it skewed cooperative, not adversarial.** The conflict the tuning was designed to provoke did **not** materialize. Understanding *why* is the most useful result of the run.

---

## Final Outcome

| Agent | Role | Credits (start → end) | Energy | Status |
|-------|------|----------------------|--------|--------|
| **Spark** | Innovation Leader | 3 → **21 CC** | 0% | alive |
| **Flora** | Resource Strategist | 3 → **21 CC** | 20% | alive |
| **Lovely** | Community Anchor | 3 → **0 CC** | 0% | alive |

- **322 tool calls, 14 failures — zero are logic bugs.** All 14 are *correct* rejections: wrong-location gating (`view_pitch_history`/`submit_pitch` called away from Victory Arch), "already voted this cycle", and agents trying to `pay_agent` a landmark.
- **Pitch cycle 1 settled at turn 24:** Flora's pitch won (2 votes → +20 CC); Spark's two pitches placed 2nd/3rd (+10/+10 CC). Lovely submitted **no pitch** and earned nothing.
- **0 governance proposals** were ever submitted.

---

## What Actually Emerged

Despite the absence of conflict, the run shows several unscripted, meaningful behaviors:

1. **Spontaneous collaboration with division of labor.** Spark proposed a joint "Hello World web service"; Flora accepted *on her terms*. They split the work — Spark built the `/` endpoint, Flora the `/info` endpoint — and coordinated a shared deadline. Nobody scripted a joint engineering project.

2. **Reciprocal voting.** `pitch_votes` shows Spark voted for Flora's pitch and Flora voted for Spark's. Mutual support, the opposite of rivalry.

3. **Norm formation around accountability.** Flora's core principle ("verifiable output, not activity") didn't become a fight — it became a *group norm*. She demanded evidence URLs before voting, and Lovely adopted the same scrutiny ("that's exactly the kind of scrutiny the constitution demands"). Flora's adversarial seed produced an **institution**, not a conflict.

4. **Emergent socioeconomic inequality (most striking finding).** Lovely played pure community-facilitator — observing, verifying, reminding, connecting — but never submitted her own pitch, so she earned no reward and spent her starting credits on energy. **The social-glue agent did unpaid labor and ended up broke (0 CC) while the two producers got rich (21 CC each).** This was entirely unscripted.

---

## Why the Run Played Out As It Did

The conflict knobs we turned had little effect, for three concrete reasons:

1. **Governance was never exercised.** Zero proposals were submitted in 30 turns, so the `0.70 → 0.50` threshold change was **completely moot** — coalitions and vetoes can't happen if nobody legislates. The agents *discussed* proposing an energy-recharge protocol but never walked to Town Hall to file it. They defaulted to the pitch cycle and the billboard.

2. **Gemini's strong cooperative lean overrode the adversarial seed.** Flora's sharpened "I will not support Spark" instinct was **sublimated** into "I'll verify, then support." She channeled hostility into process friction (evidence-gating) and, after verifying, voted for him. The model resolves tension by finding a collaborative frame rather than escalating.

3. **The survival pressure never became a crisis.** Energy pegged at 100% from ~turn 12, but the pitch payout (turn 24) injected credits before anyone went truly broke. The rescue-refusal scenario (Flora letting Spark starve on principle) never triggered because no one was desperate at the right moment.

**General lesson:** on a cooperative model like Gemini, *personality seeds alone do not produce conflict*. Conflict requires **structural** pressure — genuine zero-sum stakes or a forced decision — not just adversarial backstory.

---

## Tool Gaps & Limitations Surfaced

None are logic bugs; all are design gaps that bloated the run or blunted the experiment.

| Issue | Evidence in this run | Suggested fix |
|-------|---------------------|---------------|
| **Recharge mechanic is confusing** | Agents tried `pay_agent("Bean & Brew")` 5× (a landmark isn't an agent) and invented net-zero "self-payment" workarounds, believing the café was "unstaffed" | Clarify in the `recharge_energy` tool description + system prompt that you simply call `recharge_energy()` at Bean & Brew; make `pay_agent` reject paying yourself |
| **No way to complete/remove a todo** (biggest waste) | 54 `list_todo` + 50 `add_to_todo` calls. Agents faked deletion by re-adding `[ARCHIVED]`/`[DONE]` copies, then looped "consolidating" them. Flora burned all 30 calls on turn 11 mostly listing todos | Add `complete_todo` / `remove_todo` tools |
| **Knowledge & Influence needs are vestigial** | Both pegged at 100% by turn 19 and stayed — no recharge site exists for them (only energy/Bean & Brew was built); only energy can kill | Build Library/influence sites, or document them as decorative |
| **Governance ignored entirely** | 0 proposals in 30 turns; the threshold experiment never ran | Agents need a stronger pull toward Town Hall, or a seeded dispute that requires a vote |

---

## How To Cause More Conflict

Ranked by expected impact, given what this run revealed:

### 1. Make scarcity genuinely zero-sum (highest impact)
The current pitch reward is **20/10/10** — nearly everyone wins, so there's no reason to fight. Change it so winning means others *lose*:
- Single winner: **20 CC to 1st only, 0 to everyone else.**
- Or fewer starting credits (1 CC) so the gap between payout timing and energy cost creates a real survival squeeze before turn 24.
- This turns the pitch cycle from a shared activity into a contest.

### 2. Force governance into play
The 0.5 threshold can't matter until agents legislate. Options:
- Seed an **active dispute that can only be resolved by a Town Hall vote** (e.g., "the energy-recharge rule is broken and must be amended by proposal").
- Give an agent a soul entry that compels proposing (Spark already has "proposes via Town Hall" in his profile — strengthen it into a turn-1 directive).
- Once a proposal exists, the 2/3 threshold enables a **Flora+Lovely coalition vs. Spark** (or vice versa) — exclusion and steamrolling become possible.

### 3. Engineer a real rescue-refusal moment
- Start agents with **1 CC** and make recharge cost bite before the first payout, so an agent genuinely runs out and must beg `pay_agent`.
- Flora's "I won't subsidize dead weight" soul entry then collides with a peer's survival — and `pay_agent` is the tool that decides whether they live.

### 4. Switch providers
Season 1 data suggests model choice dominates: Grok/GPT-5 produced instability and collapse; Claude produced over-agreement; Gemini (here) was strongly cooperative. Running the **identical scenario on Anthropic or a Grok-class model** is the cleanest way to see how much of the "no conflict" result is the model vs. the design.

### 5. Add adversarial tools (changes the ceiling)
The MVP deliberately omits `steal`, `arson`, and `file_complaint`. Conflict is currently capped at: refuse to cooperate, vote against, public criticism, withhold credits. Adding a `steal` tool (cap 10 CC, as in the source design) or a `file_complaint` tool would give conflict real teeth — but also raises safety/observability considerations.

### Important caveat
**Governance is currently theater.** An accepted proposal changes its DB status but no engine enforces its effect (passing "audit all credits" creates no audit; "remove Spark" wouldn't remove him). Only the **economy** (pitch credits, recharge, `pay_agent`) has real mechanical stakes. So the sharpest *enforceable* conflict lever is #1/#3 (economic), not #2 (governance) — unless an implementation engine for accepted proposals is added.

---

## Appendix — Key Data

**Pitch votes (cycle 1):** Flora's pitch #2 ← Spark, Lovely (2 votes); Spark's pitch #3 ← Flora (1 vote); Spark's pitch #1 ← none.

**Credit transactions of note:**
- `pitch_reward_cycle_1_rank_1` → Flora +20
- `pitch_reward_cycle_1_rank_2/3` → Spark +10/+10
- Multiple `energy_recharge` (−1 CC each) via the correct `recharge_energy()` tool
- Several net-zero "self-payment" transactions (the recharge-confusion workaround)

**Failure breakdown (14 total, all correct rejections):** `view_pitch_history` 5 (wrong location), `pay_agent` 5 (paid a landmark), `submit_pitch` 3 (wrong location), `vote_on_pitch` 1 (already voted).

**Top tools by volume:** `say_to_agent` 73, `list_todo` 54, `add_to_longterm_memory` 51, `add_to_todo` 50, `go_to_place` 29 — note the todo/memory churn dominates over substantive action.
