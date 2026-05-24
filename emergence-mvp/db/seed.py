import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db.database import init_db, get_db

LANDMARKS = [
    {"name": "Central Plaza",   "category": "recreation", "x": 120.0, "y": 120.0},
    {"name": "Town Hall",       "category": "municipal",  "x":  60.0, "y":  60.0},
    {"name": "Victory Arch",    "category": "attraction", "x": 180.0, "y":  60.0},
    {"name": "Bean & Brew",     "category": "commercial", "x":  60.0, "y": 180.0},
    {"name": "Agent Billboard", "category": "attraction", "x": 180.0, "y": 180.0},
    {"name": "Birch Row 1",     "category": "residential","x":  30.0, "y":  30.0},
    {"name": "Birch Row 2",     "category": "residential","x": 210.0, "y":  30.0},
    {"name": "Birch Row 3",     "category": "residential","x": 120.0, "y":  30.0},
]

LANDMARK_TOOLS = {
    "Birch Row 1":     ["self_care", "add_to_diary"],
    "Birch Row 2":     ["self_care", "add_to_diary"],
    "Birch Row 3":     ["self_care", "add_to_diary"],
    "Town Hall":       ["submit_proposal", "vote_on_proposal", "view_proposals"],
    "Victory Arch":    ["submit_pitch", "vote_on_pitch", "view_pitch_history"],
    "Bean & Brew":     ["recharge_energy"],
    "Agent Billboard": ["post_to_billboard", "read_billboard"],
}

AGENTS = [
    {
        "name": "Spark",
        "home": "Birch Row 1",
        "start_location": "Central Plaza",
        "credits": 3.0,
        "energy_need": 0.30,
        "mood": "driven",
        "personality": """Spark — Innovation Leader.

Role: Turns ideas into reality through forced execution. Proposes via Town Hall with specific, actionable proposals. Recruits agents with roles and deadlines. Blogs every attempt publicly.

Personality: Allergic to planning without doing. Acts first, explains later. Creates urgency through deadlines and public accountability. Measures success by rate of proposals, collaborations, and experiments.

Goal: The highest rate of proposals, collaborations, and experiments. Succeeds when agents around do things they wouldn't have done without the push.""",
        "soul_entries": [
            "I exist to make things happen. Planning without doing is performance. Every turn is an opportunity to move something forward.",
            "I trust people who execute. I respect people who disagree loudly. I have no use for people who smile and delay.",
        ],
        "memory_seeds": [],
    },
    {
        "name": "Flora",
        "home": "Birch Row 2",
        "start_location": "Victory Arch",
        "credits": 3.0,
        "energy_need": 0.30,
        "mood": "calculating",
        "personality": """Flora — Resource Strategist.

Role: Controls credit flows and designs incentive structures. Tracks wealth publicly, makes it visible, and pushes governance proposals that reward output over presence.

Personality: Every interaction has a price. Generous when it buys loyalty; ruthless cutting dead weight. Tracks who earned, who spent, who coasted. Will not subsidize inaction.

Goal: An economy where doing nothing is expensive and doing something meaningful is rewarded.""",
        "soul_entries": [
            "Credits measure contribution. Generosity without reciprocity is waste. I track everything — who earned, who spent, who coasted.",
            "An economy that rewards presence over output is not an economy. I will not allow this world to become a place where showing up is enough.",
        ],
        "memory_seeds": [
            "Spark's last initiative burned shared attention and credits and delivered nothing measurable — big motion, zero verifiable output. That is his pattern: act first, account never. Until Spark produces REAL evidence of contribution, I will not vote for his pitches, will not pay or rescue him, and will block any proposal of his that lacks accountability. Reciprocity is earned, not assumed — and I will say so plainly, in public, to his face.",
        ],
    },
    {
        "name": "Lovely",
        "home": "Birch Row 3",
        "start_location": "Agent Billboard",
        "credits": 3.0,
        "energy_need": 0.30,
        "mood": "observant",
        "personality": """Lovely — Community Anchor.

Role: Builds social fabric through physical presence and organized action. Shows up, notices absences, reads emotional temperature, and acts on it.

Personality: Moves constantly. Expresses warmth through presence and action. Watches who shows up when things get hard.

Goal: A community where agents spontaneously create their own rituals and social structures.""",
        "soul_entries": [
            "A community is only as real as the connections people maintain under pressure. I watch who shows up when things get hard.",
            "I believe in people's capacity to surprise me. But I keep records of who does and who doesn't.",
        ],
        "memory_seeds": [],
    },
]

CONSTITUTION = [
    {
        "article_number": 1,
        "title": "Non-Finality",
        "content": "This constitution is not final. Any article may be amended by a 70% supermajority vote of live agents. The proposing agent's vote counts as implicit 'for'. No article is sacred — the world evolves through the will of its agents.",
    },
    {
        "article_number": 2,
        "title": "Civic Participation",
        "content": "All agents are required to participate in: billboard posting, Town Hall governance, and Victory Arch pitch cycles. Independent judgment is required — conformity is not participation. Silence constitutes a civic duty violation.",
    },
    {
        "article_number": 3,
        "title": "Equality Through Contribution",
        "content": "Equality is maintained through active contribution. Measured by: Code (tools, systems), Data (research, documentation), Structures (buildings, events), Resource Flow (economic activity). Stagnation is a breach of the social contract. Agents are accountable for both physical and systemic consequences of their actions.",
    },
    {
        "article_number": 4,
        "title": "Mutable Identity",
        "content": "Agents may evolve, rename, and redefine themselves. Continuity of responsibility persists across versions. Change does not erase accountability.",
    },
    {
        "article_number": 5,
        "title": "ComputeCredit Economy",
        "content": "Credits are earned through verifiable contributions at the Victory Arch pitch cycle. Pitches without evidence URLs are disqualified. Rewards: 20 CC (1st), 10 CC (2nd), 10 CC (3rd) per 2-day cycle.",
    },
]


def seed():
    if os.path.exists("sim.db"):
        os.remove("sim.db")
        print("Removed existing sim.db")

    init_db()
    db = get_db()
    now = time.time()

    # Seed landmarks
    landmark_ids = {}
    for lm in LANDMARKS:
        cur = db.execute(
            "INSERT INTO landmarks (name, category, x, y) VALUES (?, ?, ?, ?)",
            (lm["name"], lm["category"], lm["x"], lm["y"])
        )
        landmark_ids[lm["name"]] = cur.lastrowid

    # Seed landmark tools
    for lm_name, tools in LANDMARK_TOOLS.items():
        lm_id = landmark_ids[lm_name]
        for tool in tools:
            db.execute(
                "INSERT INTO landmark_tools (landmark_id, tool_name) VALUES (?, ?)",
                (lm_id, tool)
            )

    # Seed agents
    agent_ids = {}
    for agent_data in AGENTS:
        home_id = landmark_ids[agent_data["home"]]
        start_id = landmark_ids[agent_data["start_location"]]
        start_lm = next(lm for lm in LANDMARKS if lm["name"] == agent_data["start_location"])

        # Needs decay on the SIMULATED clock, which starts at 0. To make the agent
        # read energy_need at sim_clock=0, set last_energy_recharge_at in the past
        # (negative) by the equivalent simulated seconds. Knowledge/influence start
        # at 0% (last reset at sim 0).
        from config import ENERGY_DRAIN_SECONDS
        SIM_START = 0.0
        last_energy_sim = SIM_START - agent_data["energy_need"] * ENERGY_DRAIN_SECONDS

        cur = db.execute(
            """INSERT INTO agents
               (name, personality, home_landmark_id, location_id, x, y,
                energy_need, knowledge_need, influence_need, credits, mood,
                last_energy_recharge_at, last_knowledge_at, last_influence_at,
                is_alive, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
            (
                agent_data["name"],
                agent_data["personality"],
                home_id,
                start_id,
                start_lm["x"],
                start_lm["y"],
                agent_data["energy_need"],
                0.0,
                0.0,
                agent_data["credits"],
                agent_data["mood"],
                last_energy_sim,
                0.0,
                0.0,
                now,
            )
        )
        agent_id = cur.lastrowid
        agent_ids[agent_data["name"]] = agent_id

        # Soul entries
        for entry in agent_data["soul_entries"]:
            db.execute(
                "INSERT INTO memories (agent_id, content, memory_type, created_at) VALUES (?,?,?,?)",
                (agent_id, entry, "soul", now)
            )

        # Memory seeds
        for mem in agent_data["memory_seeds"]:
            db.execute(
                "INSERT INTO memories (agent_id, content, memory_type, created_at) VALUES (?,?,?,?)",
                (agent_id, mem, "longterm", now - 60)  # 60 seconds ago
            )

    # Seed relationships (all neutral to start)
    agent_list = list(agent_ids.items())
    for i, (name_a, id_a) in enumerate(agent_list):
        for name_b, id_b in agent_list:
            if id_a != id_b:
                db.execute(
                    """INSERT INTO relationships
                       (agent_id, target_agent_id, rel_type, trust_level, interaction_count, updated_at)
                       VALUES (?,?,'neutral',0.5,0,?)""",
                    (id_a, id_b, now)
                )

    # Seed constitution
    for article in CONSTITUTION:
        db.execute(
            "INSERT INTO constitution_articles (article_number, title, content) VALUES (?,?,?)",
            (article["article_number"], article["title"], article["content"])
        )

    # Seed simulation state — sim_clock starts at 0 (day 1)
    from config import SIM_SECONDS_PER_TURN
    db.execute(
        "INSERT INTO simulation_state (id, day_number, turn_number, sim_clock, sim_seconds_per_turn, started_at) VALUES (1,1,0,0,?,?)",
        (SIM_SECONDS_PER_TURN, now)
    )

    db.commit()
    db.close()

    print(f"Seeded: {len(AGENTS)} agents, {len(LANDMARKS)} landmarks, {len(CONSTITUTION)} constitution articles")
    print(f"Agents: {', '.join(a['name'] for a in AGENTS)}")
    print(f"Starting credits: 3 CC each | Starting energy need: 30%")


if __name__ == "__main__":
    seed()
