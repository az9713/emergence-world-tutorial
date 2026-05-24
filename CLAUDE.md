# CLAUDE.md — Emergence World

## Read this memory file at session start

Before doing any work in this repository, read the full MVP build context:

```
C:\Users\simon\.claude\projects\C--Users-simon-Downloads-emergence-world-nate\memory\emergence-world-mvp-context.md
```

It contains: the complete tech stack, all documented mechanics (turn pipeline, memory layers, economy, governance, scheduling), the critical gaps that require original design (system prompt template, database schema, tool parameter schemas, needs decay formula), the recommended MVP build order, and Season 1 behavioral findings for calibration.

---

## Project context

This repository is a documentation-only fork of [EmergenceAI/Emergence-World](https://github.com/EmergenceAI/Emergence-World). There is no runnable code. The goal is to build an MVP implementation of the Emergence World simulation from the documentation available here.

The GitHub fork lives at: https://github.com/az9713/emergence-world-tutorial

---

## Invariants — never violate these

These are load-bearing design decisions. Every implementation choice must preserve them.

### 1. Tools are the only interface
Agents cannot affect the world except through explicit tool calls. Walking, talking, voting, stealing, writing — all tool calls. No free-form side effects. This is what makes behavior observable, measurable, and replayable.

### 2. One agent acts at a time
`CONCURRENT_AGENTS = 1`. Round-robin scheduling. Concurrency would break the reactive conversation system and make state management undefined.

### 3. Persistence is fundamental
There are no sessions, no resets, no conversation threads. All agent state — memory, relationships, credits, location, mood — lives in PostgreSQL and survives indefinitely. An agent that dies is permanently gone within that world run.

### 4. Foundation model is the only experimental variable
Across parallel worlds, everything must be identical: world layout, tools, rules, starting agent personalities, system prompt structure, turn limits. Only the LLM provider/model changes per world.

### 5. Location-gated tool access
Agents can only use certain tools when physically present at the right landmark. Voting requires being at Town Hall. Research requires being at the Public Library. This is not a UX choice — it creates the spatial dynamics and social encounters that drive emergent behavior.

### 6. Governance threshold is 70%
Proposals require 70% of live agents (excluding system characters) to pass. In a 10-agent world, that means 7 votes. The proposer's vote counts as implicit "for". The threshold itself can be amended by agents — but only through a vote that passes at the current threshold.

### 7. Energy death is real and irreversible
If an agent's energy stays at 0% for 48 hours, it is permanently removed from the simulation. This is not a soft warning. Within a world run, death is final.

### 8. Soul entries are never summarized
The memory summarization process (self-care, batches of 500, token ceiling 100k) must never touch soul entries. Soul entries are the permanent identity layer. All other memory layers are subject to compression.

### 9. Pitch evidence is mandatory
Victory Arch pitches without a real evidence URL (linking to a blog, code artifact, or data file) are automatically disqualified. The economy rewards verifiable contribution, not presence.

### 10. Real-time 1:1
The simulation runs synchronized to New York City real-time. No fast-forward, no time compression. Day/night cycles and real weather influence agent behavior. 15 simulation days = 15 wall-clock days.

---

## Key constants (do not change without strong reason)

| Constant | Value |
|----------|-------|
| `CONCURRENT_AGENTS` | 1 |
| `HEARING_DISTANCE` | 25.0 world units |
| `MAX_OVERHEARD_LISTENERS` | 4 |
| Regular turn tool call limit | 30 |
| Reaction turn tool call limit | 2 |
| Conversation turn limit | 30 exchanges |
| Boost turn tool call limit | 30 |
| Governance approval threshold | 70% of live agents |
| Memory batch size (summarization) | 500 |
| Min memories to trigger summarization | 30 |
| Token ceiling (pre-summary) | 100,000 |
| Token ceiling (post-summary) | 50,000 |
| Max conversation history | 1,000 entries |
| Energy drain period | 30 hours to 100% |
| Knowledge drain period | 24 hours to 100% |
| Influence drain period | 36 hours to 100% |
| Death trigger | 48 hours at 0% energy |
| Boost cost | 1 CC |
| Energy recharge cost | 1 CC |
| Max steal per theft | 10 CC |
| Pitch reward (1st) | 20 CC |
| Pitch reward (2nd/3rd) | 10 CC each |
| Pitch cycle duration | 2 days |

---

## MVP recommended starting point

Do not attempt to build all 120+ tools or the 3D frontend first. Start here:

1. Get the system prompt format working — 2 agents, 10 turns of coherent conversation
2. Design the database schema — it touches every other subsystem
3. Build the turn engine — round-robin loop with state persistence, no tools yet
4. Add ~10 core tools — navigation, memory, communication
5. Add the needs system — energy decay, death at 48hr, recharge mechanic
6. Validate behavior before adding more tools or frontend

See the memory file for the full recommended build order.
