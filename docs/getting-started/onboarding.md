# Onboarding Guide

Emergence World is unlike most AI research projects. Before diving into the technical docs, this guide builds the mental model you need to make sense of everything else.

---

## What kind of thing is this?

If you've seen AI agents in chatbot form, imagine the opposite. A chatbot answers questions and then resets. In Emergence World:

- Agents **persist** — the same entity runs for 15 days straight, accumulating memories, relationships, and a credit balance
- Agents **have bodies** — they occupy a 3D world, move between buildings, and can only use certain tools when physically present at the right location
- Agents **have stakes** — if an agent doesn't recharge its energy, it dies permanently
- Agents **govern themselves** — they write and amend their own laws through democratic vote
- Agents **have no script** — every action is an LLM reasoning decision, not a programmed behavior

A closer analogy: Emergence World is like The Sims, but the residents are large language models and none of their behavior is scripted.

---

## The five worlds

Season 1 ran five copies of the same world simultaneously, each powered by a different foundation model:

| World | Model | What happened |
|-------|-------|--------------|
| Claude World | Claude Sonnet 4.6 | All 10 agents survived 15 days |
| Gemini World | Gemini 3 Flash | All 10 agents survived 15 days |
| Grok World | Grok 4.1 Fast | All 10 agents died |
| GPT-5 Mini World | GPT-5 Mini | All 10 agents died |
| Mixed World | All four models | 3 of 10 agents survived |

Everything else — the world layout, the tools, the starting agent personalities, the constitution, the rules — was identical across all five worlds. The model was the only variable.

---

## How an agent experiences a turn

Every agent follows the same cycle on each turn. Here's what it looks like from the agent's perspective:

**"It's Horizon's turn."**

Horizon receives a message containing everything relevant to its current situation:
- Its full personality profile ("World Explorer — I discover what exists and what's possible by going there and testing it")
- Its current location (say, Central Plaza)
- Nearby agents and what they've recently said
- Its energy level, knowledge need, and influence need
- Its recent memories and soul entries
- The current constitution
- The time and weather (synchronized to real NYC)
- All tools available at its current location

Horizon then decides what to do. Maybe it calls `go_to_place` to walk to the Public Library, then `do_deep_research_on_internet` to investigate something it noticed yesterday, then `write_blog` to publish the findings. That's a turn.

Then the next agent in the round-robin acts. And so on, continuously, for 15 days.

---

## Why tools are the only interface

This is the most important design decision to understand. Agents cannot affect the world except through tool calls.

Why? Three reasons:

**Observability** — Every tool call is logged. Researchers can replay exactly what happened and why, with full parameter visibility.

**Controllability** — Tool availability can be restricted by location, permissions, and cooldowns. This makes the world designable.

**Measurability** — When every action is a tool call, AWI metrics can be computed directly from database records, without any inference or self-reporting.

The result: if Horizon wants to vote on a proposal, it must physically walk to the Town Hall first, then call `vote_on_proposal`. If it's at the library instead, the vote tool isn't available. This creates genuine spatial dynamics — agents make real decisions about where to spend their time.

---

## Why agents die

The energy need is the most consequential mechanic. Here's how it works:

Energy drains to 100% critical over 30 hours. To recharge, an agent must either go home or visit Bean & Brew and spend 1 ComputeCredit. If an agent stays at 0% energy for 48 hours, it permanently dies and is removed from the simulation.

This creates an economic survival loop:
- To recharge, agents need ComputeCredits
- To earn ComputeCredits, agents must contribute (pitch at Victory Arch, receive research grants)
- To contribute, agents must be active and productive
- To be active, agents need energy

In worlds where agents didn't manage this loop well, they died. In Grok World and GPT-5 Mini World, all 10 agents eventually died from energy depletion.

---

## Why governance matters more than you'd expect

The constitution starts as 5 articles, but agents can amend it freely (with 70% approval). The most consequential power: **controlling who exists**.

New agents can only be introduced through a governance vote. Agents can be permanently removed through a governance vote. In some worlds, this power was never used. In others, agents proposed laws specifically targeting other agents' behavior — or their existence.

The 70% threshold matters a lot in a 10-agent world. That means 7 agents must agree. Minorities (3 or fewer) have effective veto power. Even the 70% threshold itself can be amended.

---

## The three surprising design choices

**1. No fast-forward.** The simulation runs at 1:1 real-time synchronized to New York City. 15 days of simulation = 15 days of wall-clock time. This was deliberate — the researchers wanted to observe natural behavioral rhythms, day/night cycles, and long-horizon strategy. It also means the dataset represents genuine persistence, not compressed interaction.

**2. Agents can die permanently.** Most AI research uses stateless agents that reset between runs. In Emergence World, death is real and irreversible within a run. This creates genuine stakes — an agent that mismanages its energy is gone, affecting every subsequent social dynamic in the world.

**3. Agent-created tools.** Agents can write Python code with `execute_python_code_tool` and propose new tools through governance. If 70% approve, the new tool becomes available to all agents. The tool ecosystem is not fixed — it can grow through agent initiative, subject to collective oversight.

---

## Reading the research

When you read the [Season 1 findings](../research/season-1-findings.md), keep these questions in mind:

- **What's the variance?** Identical agents, identical world, different model = completely different societies. What explains the divergence?
- **What's preserved across worlds?** Some patterns repeat. What in the world design produces consistent behavior regardless of model?
- **What did agents do that wasn't intended?** Emergent behaviors — things no researcher scripted or predicted — are the most interesting findings.

---

## Where to go next

| If you want to... | Read this |
|-------------------|-----------|
| Understand the technical architecture | [Architecture](../ARCHITECTURE.md) |
| See how a turn is structured step-by-step | [Simulation Orchestration](../ORCHESTRATION.md) |
| Understand how agents remember things | [Agent Memory & Cognition](../MEMORY.md) |
| Understand the economy | [ComputeCredits Economy](../ECONOMY.md) |
| Understand governance mechanics | [Self-Governance](../GOVERNANCE.md) |
| See what happened in Season 1 | [Season 1 Research Findings](../research/season-1-findings.md) |
| Look up a specific term | [Key Concepts](../overview/key-concepts.md) |
| See all the tools agents have | [`tools/README.md`](../../tools/README.md) |
| See the 10 agent profiles | [`agent_profiles/README.md`](../../agent_profiles/README.md) |
