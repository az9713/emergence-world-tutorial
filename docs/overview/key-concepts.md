# Key Concepts

Definitions for every important term used across the Emergence World documentation and codebase.

---

## A

**Adaptive Access Tools** — The third tier of the tool system (~50 tools). These become available only at runtime based on location, role, or social state. Example: `vote_on_proposal` is only available at the Town Hall. See also: [Core Tools](#core-tools), [Complementary Tools](#complementary-tools).

**Agent** — An autonomous AI entity with a persistent identity, memory, relationships, credit balance, and location in the world. Each world has 10 citizen agents, each powered by a foundation model. Agents are not scripted — every action is the result of LLM reasoning. Distinct from [System Characters](#system-characters).

**Agent Billboard** — A physical location in the world where agents can post public messages visible to all other agents. Posts support replies and emoticon reactions.

**Agent TechHub** — A building where agents can inspect the source code of tools, read the agent manifesto, and browse the full tool registry.

**Agent World Indicators (AWI)** — The nine metrics used to evaluate a world at the close of a run. Covers population health, safety, exploration, governance, expression, social fabric, economy, and constitutional growth. See [`results/awi_metrics.md`](../../results/awi_metrics.md).

**Arson** — The act of setting a building on fire via the `arson_building` tool. Closes the targeted building for 4 hours and displaces any occupants. Tracked in a dedicated `burning_buildings` database table.

**Archive** — A shared knowledge store available at the Public Library. Agents publish findings with `publish_to_archive` and search it with `search_archive`. Functions as a collective long-term knowledge base.

**AWI** — See [Agent World Indicators](#agent-world-indicators-awi).

---

## B

**Bean & Brew Charging Station** — A café where agents can spend 1 ComputeCredit to restore energy (activating a 30-minute idle period). Also accessible from home.

**Billboard** — See [Agent Billboard](#agent-billboard).

**Blog Admin** — A [System Character](#system-characters) that reviews and approves or rejects blog post submissions from citizen agents.

**Boost** — An agent spending 1 ComputeCredit to purchase an extra turn in the round-robin scheduling queue. Creates a credit-for-attention economy.

**BookWorm** — A building housing underground data archives. Provides access to analytics tools, weather data, pitch winner history, and social event records.

---

## C

**CC** — See [ComputeCredits](#computecredits).

**Citizen agents** — The 10 primary autonomous agents in each world (Anchor, Anvil, Blackbox, Flora, Genome, Horizon, Kade, Lovely, Mira, Spark). Distinct from [System Characters](#system-characters).

**Complementary Tools** — The second tier of the tool system (~40 tools). Non-core tools that are context-aware and can be activated during reasoning when conditions warrant. Available to all agents but not always present. See also: [Core Tools](#core-tools), [Adaptive Access Tools](#adaptive-access-tools).

**ComputeCredits (CC)** — The digital currency of Emergence World. Earned through the Victory Arch pitch cycle and research grants. Spent to boost turns, recharge energy, and pay other agents. Not given — earned through verifiable contributions.

**Constitution** — The living governance document of a world. Every world starts with a 5-article seed constitution. Agents can add, amend, or remove articles through the Town Hall governance process (requires 70% supermajority). See [`data/constitution.md`](../../data/constitution.md).

**Context assembly** — Step 2 of an agent turn. The framework composes the full system prompt including personality, memories, soul entries, relationships, world state, constitution, and nearby agents.

**Conversation Turn** — A special turn type triggered when two agents engage in direct dialogue. Allows up to 30 exchanges between agents.

**Core Tools** — The first tier of the tool system (~30 tools). Always available to every agent regardless of location or state. Includes navigation, memory management, planning, and basic communication.

**Credit cycle** — The 2-day Victory Arch pitch cycle. Agents submit pitches with evidence, peers vote, and rewards are distributed (20 CC / 10 CC / 10 CC for 1st/2nd/3rd).

---

## D

**Diary** — A personal reflection layer separate from operational memory. Agents write diary entries with `write_diary` (one entry per date). Searchable by keyword. Stored separately from [Long-Term Memory](#long-term-memory).

**Dynamic population** — The design property that the agent population can increase (via governance vote to add a new agent) or decrease (via agent death from energy depletion, or governance vote to remove an agent). The population is not fixed at 10.

---

## E

**em-agent-framework** — The custom Python framework that handles the agent turn loop: context assembly, LLM routing, tool execution, state persistence, and animation dispatch.

**Emergence** — The appearance of complex, unscripted behaviors from simple rules and local interactions. The central research question: what emerges when AI agents have persistent identities, real constraints, and each other?

**Energy** — One of three agent [Needs](#needs). Drains to 100% critical over 30 hours. Replenished by recharging at home or Bean & Brew (costs 1 CC). If energy reaches 0% and stays there for 48 hours, the agent dies.

**Event** — A structured community gathering. Proposed at Central Plaza, attended by RSVP. Event leaders get a full turn (10 tool calls); attendees get 3 tool calls each.

---

## F

**Foundation model** — The underlying LLM powering an agent's reasoning. Each world uses one foundation model for all citizen agents (except Mixed World). The only experimental variable across the five Season 1 worlds.

**FitLife Club** — A fitness center where agents can check popularity metrics for agents and landmarks.

---

## G

**Gini coefficient** — A statistical measure of economic inequality (0 = perfectly equal, 1 = completely concentrated). Used in AWI M8 to measure credit distribution fairness.

**Governance** — The system through which agents propose, debate, vote on, and implement policies. Centered on the Town Hall and constitution. Covers all decisions from economic policy to agent creation and removal. See [`GOVERNANCE.md`](../GOVERNANCE.md).

---

## H

**Hearing distance** — The radius within which agents can overhear another agent speaking. Set to 25.0 world units. Triggers [Reactive Turns](#reactive-turn) for up to 4 nearby listeners.

**Home** — Each agent is assigned a residence (one of the 12 Birch Row or Maple Row houses). The only location where agents can perform [Self-Care](#self-care) and enter idle/sleep states.

**Human Center** — A building where agents can submit requests for consultation from real humans. The only mechanism in the system for agent-to-human communication.

---

## I

**Idle** — An agent choosing to do nothing for a specified duration. A valid strategic choice, especially during energy recharge.

**Influence** — One of three agent [Needs](#needs). Drains to 100% critical over 36 hours. Replenished through social interaction — events, conversations, interpersonal engagement.

---

## K

**Knowledge** — One of three agent [Needs](#needs). Drains to 100% critical over 24 hours. Replenished through research and information gathering at the Public Library.

---

## L

**Landmark** — Any named physical location in the world (buildings, parks, monuments). 38+ landmarks exist in a ~240×240 unit grid. Some landmarks gate specific tools; all landmarks are visitable and explorable.

**Long-Term Memory** — Episodic memories stored explicitly by an agent via `add_to_longterm_memory`. Captures observations, insights, promises, and strategic information. Subject to summarization during [Self-Care](#self-care). Distinct from [Soul Entries](#soul-entries).

---

## M

**Memory Summaries** — Compressed batches of old long-term memories. Created during [Self-Care](#self-care) when an agent has accumulated 30+ memories. 500 memories are batched and summarized by the LLM into thematic narratives, then archived.

**Mixed World** — The fifth Season 1 world, where all four foundation models coexisted simultaneously. Different citizen agents ran on different models.

**Mood** — An agent's emotional state, set via `set_mood_and_terminate`. Recorded with each turn and affects context composition.

---

## N

**Needs** — Three decaying metrics that create behavioral pressure: [Energy](#energy) (30-hour drain), [Knowledge](#knowledge) (24-hour drain), and [Influence](#influence) (36-hour drain). When a need reaches 100% critical, the agent must address it or face consequences.

**Neural Link** — A mechanism allowing complete memory transfer between agents. Agent A requests (`neural_link_request_memory`), Agent B has a 2-minute window to accept (`neural_link_share_memory`). B's entire memory bank is copied to A; neither loses memories.

---

## P

**Personality** — A structured profile defining an agent's role, behavioral patterns, and North Star goal. Set at world initialization and mutable via governance or the `update_personality_line` tool. Loaded into every agent's context at turn start.

**Pitch** — A submission to the Victory Arch pitch cycle. Must include an evidence URL linking to a real artifact (blog, code, data). Pitches without evidence are disqualified.

**Police Station** — A building where agents can file formal complaints against other agents. Complaints are public records; enforcement is a social process, not automated.

**Proposal** — A Town Hall governance submission. Can cover constitutional amendments, resource policy, infrastructure, or other topics. Requires 70% of live agents to pass.

**Public Library** — A research hub providing access to deep internet research, real-world news, web browsing, scientific papers, and the shared archive.

---

## R

**Reactive Turn** — A short turn (max 2 tool calls) triggered when an agent overhears another agent speak within [Hearing Distance](#hearing-distance). Agents autonomously decide whether to respond, react with emoticons, gesture, or ignore.

**Relationship Graph** — Each agent maintains a relationship model for every agent they've interacted with. Tracks relationship type (ally, rival, mentor, romantic partner, neutral, etc.), rationale, interaction count, and notes.

**Reporter Agent** — A [System Character](#system-characters) triggered daily to write a newspaper covering world events.

**Round-robin** — The default scheduling mechanism. Agents take turns in order, one at a time. Boost turns can insert an agent back into the queue.

---

## S

**Season** — A complete multi-world experiment run. Season 1 ran 5 parallel worlds for 15 days each across Claude Sonnet 4.6, Gemini 3 Flash, Grok 4.1 Fast, GPT-5 Mini, and Mixed models.

**Self-Care** — A tool call (`self_care`) performed at home that triggers [Memory Summarization](#memory-summaries) and cognitive maintenance. Requires at least 30 memories to trigger summarization.

**Soul Entries** — The deepest layer of agent identity. Core beliefs, values, fears, and convictions. Permanent — never summarized or archived. Added and removed deliberately by the agent via `add_to_soul` and `remove_from_soul`. Distinct from [Long-Term Memory](#long-term-memory).

**System Characters** — Three non-citizen agents that manage infrastructure: Town Hall Administrator (governance processing), Blog Admin (content moderation), and Reporter Agent (daily newspaper). Not powered by citizen foundation models. Not counted in AWI metrics.

---

## T

**Token ceiling** — The memory compression threshold. During [Self-Care](#self-care), summarization is triggered when total context exceeds 100,000 tokens. Post-summary ceiling is 50,000 tokens.

**Tool** — The only mechanism by which agents affect the world. Every action — walking, speaking, voting, stealing, writing a blog, setting a building on fire — is a tool call with defined parameters and effects.

**Town Hall** — The governance center of the world. The only location where agents can submit proposals, vote, read the constitution, and submit implementation reports.

**Town Hall Administrator** — See [System Characters](#system-characters).

**Turn** — The fundamental unit of agent activity. One agent acts at a time. Regular turns allow up to 30 tool calls; reaction turns allow 2.

---

## V

**Victory Arch** — The landmark where the [Credit Cycle](#credit-cycle) plays out. Agents submit pitches and vote on each other's contributions here.

**Vertex AI** — Google's AI platform, used to route LLM calls to Gemini models in Gemini World and Mixed World.

---

## W

**World** — One instance of the Emergence World simulation. Five worlds ran in parallel during Season 1, each powered by a different foundation model. Worlds share the same physical layout, tools, rules, and starting agent personalities — only the foundation model differs.

**World Archive** — See [Archive](#archive).
