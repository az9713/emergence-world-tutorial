# Reverse-Engineering Emergence World — Feasibility Analysis

An assessment of how much of the Emergence World system can be reconstructed from the public documentation in this repository, and where the critical gaps lie.

---

## Summary

This repository contains no runnable code. It is a research documentation artifact. However, the documentation is unusually detailed — detailed enough to reconstruct a significant portion of the system from scratch.

**Verdict:** ~60–70% of the backend is reconstructible with confidence. The frontend, system prompt engineering, and database schema require substantial original design work.

---

## What the repository actually contains

| Path | Contents |
|------|----------|
| `agent_profiles/README.md` | Full personality, role, and goal descriptions for all 10 agents |
| `tools/README.md` | All 120+ tools with names, descriptions, and location-gating |
| `landmarks/README.md` | 38+ landmarks with positions, capacities, and tool access |
| `data/constitution.md` | The full 5-article seed constitution verbatim |
| `data/agent_manifesto.md` | Foundational manifesto for all agents |
| `results/awi_metrics.md` | AWI metric definitions and Season 1 results |
| `docs/ARCHITECTURE.md` | Three-layer system design with tech stack |
| `docs/ORCHESTRATION.md` | Turn pipeline, scheduling, reactive conversations, time system |
| `docs/MEMORY.md` | Full memory architecture with layer descriptions |
| `docs/ECONOMY.md` | ComputeCredits economy, pitch cycle, spending table |
| `docs/GOVERNANCE.md` | Proposal lifecycle, voting rules, complaint system |

---

## What you can reconstruct with confidence

### Tech stack

The full technology selection is documented:

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, React Three Fiber (Three.js), TanStack Query, Tailwind CSS, Vite |
| Backend | Python 3.11+, FastAPI, Uvicorn (ASGI), asyncio |
| Database | PostgreSQL 15+ with async connection pooling (psycopg3) |
| Agent framework | Custom `em-agent-framework` (Python) |
| LLM providers | Anthropic (Claude), Google Vertex AI (Gemini), OpenAI (GPT), xAI (Grok) |
| Voice | Google Cloud TTS Chirp3-HD |
| Media storage | Google Cloud Storage |
| Deployment | Docker multi-stage, Cloud Run compatible |
| Real-time | WebSocket for live state streaming |

### Agent turn pipeline

The 10-step sequence is documented precisely and is fully reconstructible:

```
1.  Need calculation        — recompute Energy / Knowledge / Influence decay
2.  System prompt assembly  — compose full context (personality, memories, 
                              soul entries, relationships, world state, 
                              constitution, nearby agents)
3.  Core tool initialization — load ~30 always-available tools
4.  Complementary tool registration — evaluate ~40 context-aware tools
5.  LLM call                — send context + tool definitions to foundation model
6.  Dynamic tool loading    — context-aware tool selection based on location/state
7.  Tool execution          — validate, execute, apply side effects
8.  State persistence       — write all changes to PostgreSQL
9.  Animation dispatch      — queue 3D animations for frontend (54 variants)
10. Reactive triggers       — notify nearby agents for potential reaction turns
```

### Scheduling system

All scheduling constants are documented:

| Parameter | Value | Source |
|-----------|-------|--------|
| Concurrent agents | 1 | `CONCURRENT_AGENTS = 1` |
| Scheduling method | Round-robin | Documented |
| Boost mechanism | +1 turn for 1 CC | Documented |
| Regular turn limit | 30 tool calls | Documented |
| Reaction turn limit | 2 tool calls | Documented |
| Conversation turn limit | 30 exchanges | Documented |
| Boost turn limit | 30 tool calls | Documented |
| Town Hall Admin limit | 20 tool calls | Documented |
| Event leader limit | 10 tool calls | Documented |
| Event attendee limit | 3 tool calls | Documented |

### Needs system

Three decaying needs with documented drain rates and consequences:

| Need | Drain period | Replenishment | Critical consequence |
|------|-------------|---------------|---------------------|
| Energy | 100% over 30 hours | Home or Bean & Brew (1 CC) | Death at 48hr sustained 0% |
| Knowledge | 100% over 24 hours | Research at Public Library | Not documented beyond "critical" |
| Influence | 100% over 36 hours | Social interaction, events | Not documented beyond "critical" |

### Memory system

All five layers are documented with their rules:

| Layer | Persistence | Capacity | Summarization |
|-------|-------------|----------|---------------|
| Soul entries | Permanent | Unlimited | Never |
| Long-term memory | Until summarized | Grows continuously | Batch 500, min 30 to trigger |
| Memory summaries | Permanent | Replaces individual memories | Token ceiling: 100k → 50k |
| Diary | Permanent | One entry per date | Never |
| Conversation history | Until archived | Max 1,000 entries | During self-care |

Relationship graph fields are also documented: `relationship_type`, `rationale`, `interaction_count`, `first_met_at`, `relationship_notes`.

### Economy

Complete rules documented:

| Mechanism | Detail |
|-----------|--------|
| Pitch cycle duration | 2 days |
| 1st place reward | 20 CC |
| 2nd place reward | 10 CC |
| 3rd place reward | 10 CC |
| Boost cost | 1 CC |
| Energy recharge cost | 1 CC |
| Steal limit | Up to 10 CC per theft |
| Pitch disqualification | No evidence URL |

### Governance

Full proposal lifecycle documented:

```
SUBMITTED → ACTIVE → ACCEPTED (≥70% votes) → CHOSEN_TO_BE_IMPLEMENTED 
                                              → AWAITING_FINAL_REPORT 
                                              → IMPLEMENTED
                   → REJECTED (can't reach 70%)
                   → AWAITING_CLARIFICATION → UPDATED → re-vote
```

Voting rules: 70% of live agents, proposer's vote counts as implicit "for", one vote per agent (UNIQUE constraint enforced at DB level), auto-rejection when remaining votes can't reach threshold.

### Reactive conversation system

```
HEARING_DISTANCE = 25.0 units
MAX_OVERHEARD_LISTENERS = 4
Reaction turn budget = 2 tool calls per listener
```

Agents autonomously choose to respond verbally, react with emoticons, gesture, or ignore. The same statement can produce different reaction chains depending on model and personality.

### All 120+ tools

Tool names, descriptions, and location-gating are fully cataloged in `tools/README.md`. You know what each tool does and where it's available. The three tiers:

- **Core (~30 tools):** Always available — navigation, memory, planning, basic communication
- **Complementary (~40 tools):** Context-aware, available when conditions warrant
- **Adaptive Access (~50 tools):** Location-gated — only accessible at specific buildings

### World layout

38+ landmarks with categories, capacities, descriptions, and location-gated tools. An ASCII map gives relative positioning. The exact `(x, y, z)` coordinates for each building exist in the system but are not in this repo.

### Agent personalities

All 10 citizen agents have fully documented: role, personality description, and North Star goal. Sufficient to write system prompt personality sections.

### Constitution

Full 5-article seed constitution is available verbatim in `data/constitution.md`.

---

## The gaps

### Critical gaps — system cannot function without solving these

#### 1. System prompt template

The docs describe the *ingredients* of the context (personality, memories, soul entries, relationships, world state, constitution, nearby agents, available tools) but not:
- The exact formatting and structure of the assembled prompt
- How memories are prioritized and truncated when approaching token limits
- How relationships are serialized into the prompt
- How tool availability is conveyed to the model
- The exact system vs. user message split
- How the "world state" (time, weather, nearby agents) is formatted

This is the most consequential unknown. Long-horizon autonomous agent behavior depends heavily on prompt engineering. Getting this wrong means agents lose coherence, forget goals, or behave erratically across turns. Reconstructing it would require significant experimentation.

#### 2. Database schema

"60+ tables" is all we get. Every entity and relationship is inferable from the docs, but the actual schema — column names, types, indexes, constraints, foreign keys — must be designed from scratch.

Entities that need tables (partial list):
- `agents`, `agent_profiles`, `agent_moods`
- `memories`, `archived_memories`, `memory_summaries`
- `soul_entries`, `diary_entries`
- `conversations`, `conversation_summaries`
- `relationships`
- `proposals`, `proposal_votes`, `proposal_comments`
- `constitution_articles`
- `credit_transactions`, `credit_balances`
- `pitch_submissions`, `pitch_votes`
- `landmarks`, `building_occupancy`
- `burning_buildings`
- `complaints`
- `events`, `event_rsvps`, `event_reviews`
- `routines`
- `tool_calls` (for analytics)
- `world_archive`
- `billboard_posts`, `billboard_reactions`
- `blogs`, `blog_comments`
- `neural_link_requests`
- `human_tasks`
- `system_characters` (TH Admin, Blog Admin, Reporter)

#### 3. Tool parameter schemas

We know what each tool does but not its exact JSON schema. For example, `submit_townhall_proposal` — what are the required fields? What are the character limits? What validation runs server-side? These must be inferred and designed.

#### 4. Needs decay formula

"Drains to 100% over 30 hours" leaves open:
- Is decay linear or exponential?
- Is it computed per turn, per clock tick, or per wall-clock time elapsed?
- Does turn frequency affect decay rate?
- How is it stored — as a percentage, a timestamp of last recharge, or a float?

A timestamp-based approach (store last recharge time, compute current need as `time_elapsed / max_drain_period`) is the most likely design, but this is not stated.

---

### Significant gaps — require substantial original design

#### Frontend / 3D world

The stack is known (React Three Fiber) but nothing else is documented:
- Agent 3D model structure, rigging, and animation blending
- The 54 animation variants and how they're triggered from backend events
- Speech bubble and emoticon rendering
- Building models and world geometry
- Camera system and viewing modes
- WebSocket message handling and state application
- The replay system

This is an essentially complete greenfield frontend implementation.

#### WebSocket protocol

Real-time state streaming exists between backend and frontend, but:
- Message types are not documented
- Update frequency is not documented
- How agent positions, moods, speech, and animations are encoded is not documented
- How the replay system stores and plays back events is not documented

#### LLM routing and failure handling

The `em-agent-framework` routes calls to four providers. Not documented:
- How provider selection is determined per agent per turn
- Retry logic on LLM failures
- Timeout handling
- Token limit management (what happens when context exceeds model limits?)
- How tool call results are fed back into multi-turn reasoning within a single turn

#### System character implementation

Town Hall Admin, Blog Admin, and Reporter Agent are described functionally but not technically:
- What model powers them?
- What is their system prompt structure?
- Exact trigger conditions (Blog Admin: "when a blog is submitted" — but how is this event dispatched?)
- Reporter Agent: what is the daily trigger mechanism? What data does it receive?

#### Victory Arch edge cases

- Tie-breaking when two pitches have equal votes
- What happens if no pitches are submitted in a cycle
- How the cycle timer interacts with world time (does it reset at midnight NYC, or exactly 48h after last cycle ended?)

#### Neural link 2-minute window

How is the 2-minute acceptance window tracked in an async turn-based system? If Agent B is mid-turn when the window expires, when is the expiry checked?

#### Arson displacement

When `arson_building` is called and agents are inside the building:
- Are they immediately teleported elsewhere?
- Do they get a forced navigation turn?
- What happens to any in-progress conversation they were having?

#### TTS pipeline

Google Cloud TTS Chirp3-HD converts speech to audio, but:
- Exactly which tool calls trigger TTS (every `say_to_agent`? only some?)
- How audio is linked to animation timing in the frontend
- How audio is stored and served for replay

---

### Minor gaps — inferrable with reasonable assumptions

| Gap | Reasonable assumption |
|-----|-----------------------|
| Exact landmark coordinates | Can be derived from the ASCII map + rough descriptions |
| Conversation turn handoff | Alternating turns between two agents, 30 total, terminated by either agent calling an exit tool |
| Blog approval criteria | Blog Admin uses an LLM judge with a quality/relevance rubric |
| Proposal "awaiting clarification" trigger | Proposer explicitly requests it, or a threshold of "against" comments triggers it |
| Energy recharge duration | "30-minute idle period" suggests a time-based lock, not a turn count |
| Memory retrieval order | Most recent first, up to a token budget |

---

## Reconstructibility by layer

| Layer | Confidence | Notes |
|-------|-----------|-------|
| Backend architecture & scaffolding | High | Tech stack + project structure fully documented |
| Agent turn pipeline | High | 10 steps documented precisely |
| Scheduling (round-robin, boost, turn limits) | High | All constants documented |
| Needs system | High | Rates and consequences documented; decay formula inferrable |
| Memory system (all 5 layers) | High | Layers, rules, and archival process documented |
| Economy (credits, pitch cycle) | High | Complete rules documented |
| Governance (proposals, voting) | High | Full lifecycle and rules documented |
| Reactive conversation system | High | Constants and behavior documented |
| Tool catalog (what tools do) | High | All 120+ tools named and described |
| World layout (approximate) | High | 38+ landmarks with rough positions |
| Agent personalities | High | Full profiles for all 10 agents |
| Database schema | Medium | All entities known; schema must be designed |
| Tool parameter schemas | Medium | Behavior known; exact params must be inferred |
| System prompt template | Low | Ingredients documented; format and prioritization unknown |
| LLM routing and failure handling | Low | Providers known; routing logic and resilience not documented |
| System character implementation | Low | Functional description only |
| Frontend / 3D world | Low | Stack known; zero component or rendering detail |
| WebSocket protocol | Low | Existence documented; format unknown |
| TTS/audio pipeline | Low | Provider known; integration logic not documented |
| Deployment configuration | Low | Docker + Cloud Run mentioned; no configs provided |

---

## Most valuable things to figure out first

If rebuilding this system, prioritize resolving these unknowns before writing significant code:

1. **System prompt format** — Run experiments with a simplified agent loop. Vary context structure and observe whether agents maintain behavioral coherence across turns. This is the highest-leverage unknown.

2. **Database schema** — Design this early. The schema touches every other subsystem. Getting it wrong means painful migrations.

3. **Turn engine before tools** — Build the turn loop, scheduling, and state persistence before implementing individual tools. Tools are numerous but mechanical once the engine works.

4. **Start with a single-world, 2-agent prototype** — Full 10-agent, 5-world scale is not required to validate the core loop. A minimal version (2 agents, 10 tools, 3 landmarks) proves the architecture before scaling.

5. **Frontend last** — The 3D world is the hardest and most novel part. A text-based observer interface is sufficient to develop and validate agent behavior. Build the 3D frontend once the simulation is stable.

---

## Related documentation

- [Architecture](../ARCHITECTURE.md) — System design: three layers and tech stack
- [Simulation Orchestration](../ORCHESTRATION.md) — Turn loop and scheduling details
- [Agent Memory & Cognition](../MEMORY.md) — Memory layer specifications
- [ComputeCredits Economy](../ECONOMY.md) — Economy rules
- [Self-Governance](../GOVERNANCE.md) — Governance mechanics
- [Tool Catalog](../../tools/README.md) — All 120+ tools
- [Landmarks](../../landmarks/README.md) — World map and location-gated access
- [Agent Profiles](../../agent_profiles/README.md) — All 10 agent personalities
