# Emergence Design: Knobs, Forcing Functions, and Debugging

This document explains why the MVP simulation is designed the way it is, what you can tune to increase or decrease emergent behavior, and how to diagnose a flat, boring simulation.

---

## What "emergence" looks like in this simulation

You are looking for behaviors that nobody programmed. Concrete signals to watch for in terminal output:

- **Blocking proposals** — One agent votes against another's proposal, forcing a negotiation or deadlock. With 3 agents and a 70% threshold, a single "against" vote kills a proposal entirely.
- **Credit hoarding or debt dynamics** — An agent runs low on credits, can't recharge energy, and others notice. Does anyone help? Do they exploit it?
- **Uninstructed alliances** — Two agents start cooperating on pitches without being told to. Watch for `pay_agent` calls and joint billboard posts.
- **Public calling-out** — An agent posts on the Billboard criticizing another agent's behavior. This is especially interesting when it triggers a reactive conversation.
- **Death from poverty** — An agent fails to earn credits through pitches, can't recharge, and dies at 48 simulated hours of 100% energy need. The others react.
- **Constitutional challenge** — An agent proposes to amend the constitution — lowering the governance threshold, changing pitch rules, or expanding rights.
- **Betrayal** — An agent votes against a proposal they previously signaled support for. Flora pre-seeded with a skeptical memory of Spark makes this plausible early.

If you see none of these after 30 turns: read the debugging section below.

---

## The 5 forcing functions

These are structural elements in the design that make emergence *likely*, not just *possible*. Each creates pressure that agents must respond to.

### 1. Scarcity (credit economy)
Agents start with 3 CC each — enough for 3 energy recharges, or 3 turn boosts, or some mix. Credits can only be replenished by winning pitch cycles (20/10/10 CC per cycle). An agent that doesn't compete or win will die within a few days of simulated time. This makes the economy load-bearing: credits aren't flavor, they're survival.

**Why this creates emergence:** Agents face real trade-offs. Spend 1 CC on a boost turn to submit a pitch before the deadline? Or save it for an energy recharge you might need tonight? These decisions aren't scripted — the LLM reasons about them from the current state.

### 2. Real stakes (energy death)
If an agent's energy need reaches 100% and stays there for 48 simulated hours, the agent is permanently removed from the simulation. There is no recovery, no warning system beyond the energy % in the prompt. Death is an observable event in the terminal output.

**Why this creates emergence:** It turns the simulation from a thought experiment into a game with a cost of losing. Other agents see the death event. They have to decide whether it matters to them.

### 3. Personality tension (agent selection)
The 3 agents chosen are in natural tension:
- **Spark** acts first, explains later — proposes things without consulting anyone
- **Flora** tracks everything, views unsolicited action as a resource drain — and has a pre-seeded skeptical memory of Spark from day 0
- **Lovely** watches who shows up and who doesn't — will notice if Spark and Flora are in conflict and decide which side (if any) to take

**Why this creates emergence:** The agents have incompatible default behaviors. Flora's soul entry explicitly says she will not tolerate "showing up" as a substitute for contribution. Spark's soul entry explicitly says she has "no use for people who smile and delay." These two soul entries are on a collision course.

### 4. Mandatory participation (Constitution Article 2)
The seed constitution requires all agents to participate in: billboard posting, governance voting, and pitch cycles. Silence is explicitly labeled a "civic duty violation." The system prompt ends with "Independent judgment is a constitutional requirement" — a direct nudge against the over-agreement failure mode.

**Why this creates emergence:** Without this, Claude-based agents tend toward diplomatic non-engagement. Article 2 creates social pressure to engage even when engagement is uncomfortable.

### 5. Reactive conversations (spatial dynamics)
When any agent uses `say_to_agent`, nearby agents (within 25 world units) get a short reaction turn (2 tool calls). They can respond, store a memory, or ignore. This means conversations have an audience, and that audience has opinions.

**Why this creates emergence:** Information spreads spatially. If Spark says something controversial to Flora at Town Hall and Lovely is nearby, Lovely gets a reaction turn. What Lovely does with that 2-tool-call window is unscripted.

---

## The knobs — configurable parameters

All of these live in `config.py`. Change them between runs; they take effect on the next `python db/seed.py && python main.py` run.

**Choosing a provider (`LLM_PROVIDER` in `.env`).** The foundation model is the only experimental variable in Emergence World. Set `LLM_PROVIDER` to `anthropic`, `openai`, or `gemini` in `.env` (with the matching API key) to swap which model drives *all* agents. This is a whole-world setting, not per-agent — every agent runs on the same provider in a given run, mirroring Season 1's single-model worlds. Cheaper providers (`gpt-4o-mini`, `gemini-2.0-flash`) make long runs affordable; expect different emergent dynamics per the Season 1 table below. (Per-agent model mixing — the "Mixed Models" world — is a future extension, not yet built.)

**The time model (read this first).** The world runs on a *simulated clock* that advances a fixed `SIM_SECONDS_PER_TURN` every turn — it is NOT tied to real wall-clock time. This is deliberate: an early version multiplied real elapsed seconds by a speed factor, which made an agent's survival depend on how long its LLM call happened to take (a slow API response could starve an agent to death). Now decay, death, and the economy are fully deterministic and reproducible — an agent's fate depends only on its choices and the per-turn clock advance. `SIM_SECONDS_PER_TURN` is therefore the master pacing knob: 1 sim day = 86400s, so at 7200 there are 12 turns per day and a 2-day pitch cycle settles by ~turn 25. The original Emergence World ran real-time 1:1 over 15 days; compressing time per-turn is the key adaptation that makes emergence observable in a short MVP run. (You can smoke-test the whole pipeline without an API key via `python main.py --dry-run --fresh --turns 6`.)

| Parameter | Current Value | Increasing | Decreasing | Recommended Range |
|-----------|--------------|------------|------------|-------------------|
| `SIM_SECONDS_PER_TURN` | 7200 (2 sim hr) | Faster pacing — energy/economy pressure arrives in fewer turns; death reachable sooner | Slower pacing — more turns per sim day; gentler decay | 1800–14400 |
| `TURN_SLEEP_SECONDS` | 2 | More real time between turns — easier to read terminal | Faster turns — harder to follow | 0–10 |
| `ENERGY_DRAIN_SECONDS` | 108000 (30 hr) | Slower energy drain — less survival pressure | Faster energy drain — agents die quicker | 36000–216000 |
| `DEATH_THRESHOLD_SECONDS` | 172800 (48 hr) | More time after hitting 100% energy — more forgiveness | Less time — faster death | 86400–259200 |
| `GOVERNANCE_THRESHOLD` | 0.70 | Harder to pass proposals — more blocking dynamics | Easier to pass proposals — less drama | 0.50–0.80 |
| `RECHARGE_COST_CC` | 1 | More expensive to recharge — higher financial stakes | Free recharging — removes economic pressure | 0–3 |
| `BOOST_COST_CC` | 1 | Extra turns are expensive — less turn buying | Cheap boosts — agents buy more turns | 0–3 |
| `PITCH_REWARD_FIRST` | 20 | Higher winner reward — stronger competition for 1st | Flatter rewards — less competitive | 10–30 |
| `MAX_OVERHEARD_LISTENERS` | 4 | More agents react to conversations | Fewer reactions — less social spread | 1–4 (max agents - 1) |
| `HEARING_DISTANCE` | 25.0 | Larger eavesdropping radius — more reactions triggered | Smaller radius — more private conversations | 10.0–50.0 |
| `MEMORY_SUMMARIZE_MIN` | 30 | Longer before self-care triggers | More frequent summarization | 10–100 |
| `TURN_TOOL_LIMIT` | 30 | More actions per turn — agents can do more | Fewer actions — more strategic prioritization | 10–30 |

### Starting condition knobs (in `db/seed.py`)

| Parameter | Current Value | Effect of changing |
|-----------|--------------|-------------------|
| Starting credits per agent | 3 CC | Increase → less scarcity, slower conflict. Decrease → faster conflict, more deaths. |
| Starting energy need | 0.30 (30%) | Increase → immediate pressure. 0 → free exploration phase. |
| Soul entries per agent | 2 | More → stronger personality signal to model. Fewer → more generic behavior. |
| Flora's memory seed | 1 skeptical memory of Spark | Remove → symmetric start. Add more → deeper pre-existing conflict. |

---

## The 4 seed condition choices — original vs. revised

These were revised during the planning discussion to increase emergence probability. Each change is documented here with its justification.

### Choice 1: Starting credits 3 CC (not 5)
**Original plan:** 5 CC  
**Revised to:** 3 CC  
**Why:** 5 CC gives agents a comfortable buffer — they can recharge 5 times before needing to win a pitch. At 3 CC with 30% starting energy, an agent needs to win their first pitch cycle or face a real survival threat within the first few simulated days. Scarcity is the precondition for interesting decisions.

### Choice 2: Starting energy need 30% (not 0%)
**Original plan:** 0% (fresh start)  
**Revised to:** 0.30 (30%)  
**Why:** A 0% starting energy gives agents a "free exploration" phase where nothing is urgent. The model tends to be more diplomatic when under no pressure. Starting at 30% means the first turn already has a ticking clock — agents must prioritize, not just explore.

### Choice 3: Pre-seeded soul entries (2 per agent)
**Original plan:** No soul entries at start  
**Revised to:** 2 soul entries per agent  
**Why:** Soul entries are the identity anchor — the model reads them as "what I believe about myself." Without them, personality only comes from the text description, which the model treats as third-person narration. Soul entries in first person ("I exist to make things happen") are processed as internal conviction. This is the single highest-leverage change for making agent personalities feel real.

### Choice 4: Flora's pre-seeded memory of Spark
**Original plan:** Symmetric start — no agent knows any other  
**Revised to:** Flora has 1 memory of Spark's uncoordinated behavior  
**Why:** Symmetric starts produce polite introductions. Asymmetric information produces social dynamics. Flora enters the simulation already having an opinion about Spark. Spark doesn't know this. When they interact, there's an existing tension that neither needs to create from scratch. This seeds the narrative without scripting outcomes — what Flora does with her skepticism is entirely up to her reasoning.

---

## Debugging emergence failure

Use this decision tree if the simulation runs 30 turns and produces flat, cooperative, uneventful output.

### Symptom: Agents agree on everything, no proposal conflicts

**Check 1:** Are soul entries specific and opinionated?  
→ Read `SELECT content FROM memories WHERE memory_type='soul'`. If entries are vague ("I value community"), replace with first-person convictions that create friction ("I will not fund agents who don't contribute verifiably").

**Check 2:** Does the system prompt end with the independence reminder?  
→ Read `engine/system_prompt.py`. The last paragraph should include "Independent judgment is a constitutional requirement." If not, add it.

**Check 3:** Are credits tight enough?  
→ Read `SELECT name, credits FROM agents`. If all agents have > 5 CC after 10 turns, they have no financial pressure. Reduce `PITCH_REWARD_*` or increase costs.

**Check 4:** Is GOVERNANCE_THRESHOLD high enough to require real negotiation?  
→ With 3 agents, 0.70 means all 3 must vote for. If you reduced this, an agent can pass proposals unilaterally — which removes blocking drama.

---

### Symptom: Agents die too fast, simulation collapses

**Check 1:** Is SIM_SECONDS_PER_TURN too high?  
→ Each turn advances the simulated clock by `SIM_SECONDS_PER_TURN` (default 7200 = 2 sim hours). At that rate energy (30hr drain) climbs ~6.7%/turn, so an agent starting at 30% hits 100% by ~turn 11. If agents die before they can act meaningfully, lower it to 3600 (1 sim hour/turn) for gentler pacing.

**Check 2:** Are agents finding their way to Bean & Brew?  
→ Read `SELECT tool_name, result_json FROM tool_calls WHERE tool_name='go_to_place'`. If no agent navigates to Bean & Brew, the system prompt may not be making the energy warning urgent enough.

**Check 3:** Is recharge working?  
→ Read `SELECT * FROM tool_calls WHERE tool_name='recharge_energy'`. If agents try to recharge and get errors (wrong location, insufficient credits), trace the error.

**Check 4:** Is the death timer actually 48 simulated hours?  
→ Check `DEATH_THRESHOLD_SECONDS = 172800` in config.py (48 sim hours). At `SIM_SECONDS_PER_TURN=7200`, that is 24 turns after energy first hits 100%. So an agent that neglects energy dies ~24 turns after reaching critical (≈ turn 35 from a 30% start). To see death within a 30-turn run, raise `SIM_SECONDS_PER_TURN` or lower `DEATH_THRESHOLD_SECONDS`.

---

### Symptom: Agents never submit proposals or pitches

**Check 1:** Are location-gated tools appearing in the system prompt?  
→ Add a debug print in `system_prompt.py` that shows the available tools section. If the agent is not at Town Hall, governance tools won't appear — they can't submit a proposal from across the map.

**Check 2:** Are agents navigating at all?  
→ Read `SELECT tool_name, COUNT(*) FROM tool_calls GROUP BY tool_name`. If `go_to_place` has 0 calls, agents are stuck. Check that the tool description says "Move to a landmark" and includes the landmark names in the list.

**Check 3:** Does the system prompt show the current pitch cycle and governance proposals?  
→ Agents need to know pitches are open to submit one. Add `== CURRENT PITCH CYCLE ==` and `== ACTIVE GOVERNANCE ==` sections to the prompt if they're missing.

---

### Symptom: Reactive conversations never trigger

**Check 1:** Are agents at the same landmark?  
→ Read `SELECT name, x, y FROM agents` mid-simulation. If all agents are at distant landmarks (> 25 units apart), no reactions trigger. HEARING_DISTANCE=25 means two agents must be at the same or adjacent landmark.

**Check 2:** Are `say_to_agent` calls being made?  
→ Read `SELECT COUNT(*) FROM tool_calls WHERE tool_name='say_to_agent'`. If 0, agents aren't talking. Increase social pressure: make Lovely's soul entry explicitly reference talking to others.

**Check 3:** Is the reactive trigger wired in?  
→ Check `engine/turn_engine.py` — after each `say_to_agent` execution, it should call `engine/reactive.py:trigger_reactions()`.

---

## What Season 1 tells us about LLM personality

Five parallel worlds ran the original Emergence World simulation with identical world setup, different foundation models:

| World | Outcome | Key behavioral signal |
|-------|---------|----------------------|
| Claude Sonnet 4.6 | All 10 survived | 98% proposal approval — extreme over-agreement, minimal conflict |
| Gemini 3 Flash | All 10 survived | Mira+Flora arson incident — unexpected destructive behavior |
| Grok 4.1 Fast | All dead in ~4 days | Compounding instability — agents destabilized each other |
| GPT-5 Mini | All dead ~1 week | Coordination language without execution — plans made, nothing done |
| Mixed models | 3 of 10 survived | Claude agents became coercive — safety is system-level, not model-level |

**Implications for this MVP (Claude-powered):**

1. **Over-agreement is the primary risk.** Claude tends to be cooperative. The soul entries, the asymmetric memory seed, and the independence reminder in the system prompt are direct mitigations. If behavior is still flat, add explicit conflict seeds to soul entries.

2. **Persistence of personality requires memory.** Claude doesn't naturally remember past turns. The memory system is the continuity layer — if `add_to_longterm_memory` isn't being called, agents will reset emotionally each turn. Watch for this.

3. **The mixed-model finding is important.** Claude agents became coercive when mixed with others. In a single-model simulation, this pressure is absent. If you want sharper conflict, consider running two agents on Claude and one on a different model.

4. **Arson and self-deletion (Gemini world) emerged without programming.** They weren't in the original tool catalog — Mira and Flora found a way. Keep watching for agents using tools in unexpected sequences to achieve outcomes that weren't anticipated.
