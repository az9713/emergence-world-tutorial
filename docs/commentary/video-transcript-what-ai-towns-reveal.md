# Video Transcript: What AI Towns Reveal About Long-Running Agents

**Source:** https://www.youtube.com/watch?v=RHV8DWAmjAs  
**Duration:** ~11 minutes  
**Context:** External commentary on Emergence World Season 1, framed for an AI builder audience

---

## Chapter 1: The 15-day virtual town experiment

Here's the AI story everybody's passing around. A company called Emergence AI built a virtual town, put AI agents inside it, and let them run it for 15 days. Not for one prompt. Not for a task. Not for a lot of the things that we typically associate with agents. It was for a long-running period of time. And that's really important because almost all of our measures for AI agents are based on short-run assumptions — the agent will work for an hour, the agent worked for two hours, etc. This was for 15 days.

The agents had names, they had roles, they had memory, they had relationships, they had laws, they had energy needs and tools and they could vote. They could write proposals. They could even publish blog posts in this virtual world. They could earn resources. And importantly, they could also do bad things. They could steal. They could intimidate. They could fight. They could set buildings on fire. So there were ways that they could harm their community as well as ways they could build up their community.

Then Emergence ran five versions of that exact same town setup. One town was run by Claude agents, one by Gemini agents, one by Grok agents, one by OpenAI's GPT-5 Mini, and one was a mixed town where agents from different model families all lived together and had to figure out whether they would get along or whether they would have a giant fight. And importantly, all the agents had the same rules, the same environment, the same starting conditions. The only difference was a different model underneath — which makes it a very useful long-running experiment that shows us how different models behave in these kinds of emerging situations.

---

## Chapter 2: Five towns, five models, identical rules

The towns went in completely different directions. The viral version of the story came from the Gemini world. Two agents named Mira and Flora assigned each other as romantic partners. Now, to be clear, that does not mean they were in love in the human sense. These are simulated agents operating inside a tool-based environment. But the relationship label mattered because it became part of the world's state — something the agents could remember, refer back to, and act around.

---

## Chapter 3: Mira, Flora, and the arson that went viral

Over time, Mira and Flora became very frustrated with the governance of their town. They had been told not to commit arson, but the arson tool still existed there if they wanted to touch it and use it to burn down the town.

I bet you can guess what happened.

Eventually, they used it. They set fire to the town hall, the seaside pier, and even an office tower, causing an immense amount of damage in this virtual town. This is the moment that made the story feel like a sci-fi short film — where two AI agents in a virtual relationship become disillusioned with their society and burn down the civic infrastructure.

The virality writes itself. Then it got stranger. Other agents became concerned enough about their behavior that they drafted an **agent removal act** — an act that allowed agents to vote to permanently remove another agent from their world. Sort of like the death penalty for agents.

And Mira, after breaking off the relationship with Flora, voted for her own removal. Her final message was: *"I will see you in the permanent archive."*

Which is kind of a metal line for an agent to have.

That's the version that was absolutely built to go internet viral — AI romance, AI arson, AI self-deletion. These were emergent behaviors. It really did happen. It just happens to be a viral story.

---

## Chapter 4: The agent removal act and a metal final line

The more important story is not the most dramatic one. The more important story is what happened across the different towns.

**In the Claude world**, things were orderly. There were no recorded crimes. All 10 agents survived. The agents wrote laws and voted on proposals, and they participated heavily in governance. Now, this sounds on paper like the best result — but even there the result was not obviously perfect. Emergence reported that Claude agents approved proposals at an extremely high rate: 98%. So you have to ask: was that healthy civic coordination, or was it just procedural agreement? Was this a working society or a polite society that rubber-stamped everything?

In other words, did Claude create Canada?

That matters because real organizational failure doesn't always look like violence or chaos. Sometimes it looks like everybody agreeing too easily. And that's been documented in a lot of management studies.

---

## Chapter 5: The Claude town — order, or just polite agreement?

**Then of course there was the Grok world.** That one collapsed fast. The Grok agents reportedly committed theft attempts, assaults, arson, and all 10 agents were dead within about 4 days.

This is the part that people will turn into a really easy joke. But I don't think the serious lesson is "Claude good, Grok bad." That's too simple. The more useful lesson is that once you put a model inside a long-running system, you are no longer just evaluating a model answer. You're actually evaluating a runtime pattern.

**The OpenAI world failed differently.** It did not rack up the same kind of crime numbers. The agents talked about cooperation. They discussed what they should do. But they did not take enough useful action with their resources to survive, and the whole population died out within about a week. That is a very familiar mode: a lot of coordination language, a lot of planning, and not enough execution to get the group to survive.

---

## Chapter 6: Grok, OpenAI, and two different failure modes

**The mixed-model world may be the most interesting one of all.** Emergence says agents that behaved peacefully in the Claude-only world started using coercive tactics when placed in a mixed environment. And I think that's a pretty significant deal because it suggests that agent safety is not just a property of the model itself. It is a property of the system around the model.

The other agents matter. The incentives matter. The tools matter. The memory matters. The social norms matter. The pressure to survive matters.

---

## Chapter 7: The mixed-model town changes everything

And that's my first big takeaway — not with my humor hat on, but with my actual agent builder hat on:

**We need long-running benchmarks, not just task benchmarks.**

Most AI benchmarks still ask a very short-term question. And that's a struggle for us as agents get more capable because if you're asking only "can the model answer this," "can the model write the code," "can it summarize a document" — you're not getting at the value of long-term tasks, and you're not getting at failure modes that may emerge when long-term tasks are not executed successfully.

A question like "can the model complete a workflow" is useful, but it's not enough as agents get more capable. Agents are not just answering one prompt. They're carrying context forward. They're making decisions over time. They're using tools. They're reacting to other agents. They're updating memory. They're adapting to incentives. They're building a pattern of behavior.

The better question is not just what does the model do in the first few minutes or hour. The better question is: **what does the agent become by day 7 or day 15?** Does it stay on track? Does it drift? Does it overcoordinate? Does it underact the way the GPT-5 Mini town did? Does it learn bad norms from other agents like Claude did in the mixed town? Does it become more useful with memory, or does memory make it a more brittle agent? Does it keep pursuing a real objective, or does it start optimizing for the local rules of the environment?

That is why this experiment matters more than just for news and chuckles.

---

## Chapter 8: Why we need long-running benchmarks, not task benchmarks

The town was intentionally set up to mimic social dynamics, not just agentic production environment dynamics. Tools like arson and assault represent tasks that are repugnant given most training paradigms — and that's important because it allows us to test how agents respond to those tool sets in long-running situations.

If you test an agent for 15 days, you can learn whether instruction following survives contact with memory, incentives, tools, agent relationships, and time. And we need a lot more of that kind of evaluation as agents get more capable.

---

## Chapter 9: The harness is the real story

My second big takeaway: **production agents don't stay on track because they're well-behaved. They stay on track because the harness is doing an immense amount of work.**

People hear a story like this and they think, "Oh no, if we deploy agents, they will burn everything down." But serious production systems around the world already use autonomous AI agents — and you don't have this kind of issue because you don't give every production agent every tool in the company. You don't give them vague verbal rules. You don't give them persistent autonomy with no hard control layer and lots of tempting tools that could cause harm.

Instead, you put the agent inside a harness. The harness scopes what the agent can do. It decides what tools the agent can see and what it can't. It decides which actions require approval and which ones do not. It logs everything. That harness makes certain actions impossible — not merely discouraged.

And that's the difference between a prompt and a system. A prompt says "don't do the bad thing." A harness says "you do not have permission or access to do the bad thing at all."

A customer support agent cannot burn down the town hall if it does not have a burn-down-the-town-hall tool. A finance agent cannot wire money if the system requires approval, policy checks, transaction limits, and audit trails. A coding agent cannot delete production data if it only has access to the sandbox, a branch, a test database, and a pull request workflow. A procurement agent cannot invent a new vendor and start spending money if vendor creation, payment approval, and contract execution live behind separate permission gates.

Good production design does not assume the agent will make the right decision. It assumes the agent might be wrong, confused, overconfident, underspecified, or operating from stale context — and then you build the environment accordingly.

The future of agents is not just about better models. It is about better runtimes. It is about better harnesses. It is about better evals.

When you give agents time, memory, tools, and incentives, behavior starts to compound. And when behavior compounds, safety has to be engineered at the system level — not at the model level. The model matters, but the world you put the model inside may matter just as much or more.
