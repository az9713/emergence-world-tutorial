"""
Agent World Indicators (AWI) — 9 macro-level metrics computed from the sim DB.

compute_awi(db) -> dict   : compute all 9 indicators
format_awi(awi: dict) -> str : human-readable multi-line block
"""

import json


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _gini(credits_list):
    """Compute Gini coefficient for a list of credit values.

    Formula: sum_i sum_j |c_i - c_j| / (2 * n * sum(c))
    Returns 0.0 if n < 2 or sum == 0.
    """
    n = len(credits_list)
    if n < 2:
        return 0.0
    total = sum(credits_list)
    if total == 0:
        return 0.0
    running = 0.0
    for i in range(n):
        for j in range(n):
            running += abs(credits_list[i] - credits_list[j])
    return running / (2.0 * n * total)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_awi(db) -> dict:
    """Compute the 9 Agent World Indicators from a finished/in-progress sim DB.

    Returns a dict with these exact keys:
      M1_population          : int   # agents with is_alive=1
      M2_safety_incidents    : int   # count of credit_transactions reason='theft'
                                     # + accepted remove_agent proposals
      M3_space_exploration   : float # avg distinct landmarks visited per agent
                                     # (from tool_calls tool_name='go_to_place',
                                     #  parse parameters_json landmark_name)
                                     # denominator = total agents (incl. dead)
      M4_tool_exploration    : float # avg distinct tool_name used per agent
                                     # (tool_calls); denominator = total agents
      M5_governance_participation : float # proposal_votes / (live_agents * proposals)
                                          # clamped 0..1; 0 if no proposals
      M6_public_expression   : int   # billboard_posts + blogs count
      M7_social_fabric       : int   # relationships with rel_type != 'neutral'
      M8_economic_gini       : float # Gini coefficient of current agent credits
      M9_constitutional_growth : int # constitution_articles with amended_at NOT NULL
    All values are JSON-safe (int/float).
    """

    # M1 — live agent count
    m1 = db.execute("SELECT COUNT(*) FROM agents WHERE is_alive=1").fetchone()[0]

    # M2 — safety incidents: thefts + accepted remove_agent proposals
    theft_count = db.execute(
        "SELECT COUNT(*) FROM credit_transactions WHERE reason='theft'"
    ).fetchone()[0]
    removal_count = db.execute(
        "SELECT COUNT(*) FROM proposals WHERE status='ACCEPTED' AND effect_type='remove_agent'"
    ).fetchone()[0]
    m2 = int(theft_count) + int(removal_count)

    # M3 — avg distinct landmarks visited per agent (denominator = all agents)
    total_agents = db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]

    if total_agents == 0:
        m3 = 0.0
    else:
        # Pull all go_to_place tool calls and parse landmark_name from parameters_json
        rows = db.execute(
            "SELECT agent_id, parameters_json FROM tool_calls WHERE tool_name='go_to_place'"
        ).fetchall()

        agent_landmarks = {}  # agent_id -> set of landmark names
        for row in rows:
            agent_id = row[0]
            params_json = row[1]
            landmark_name = None
            if params_json:
                try:
                    params = json.loads(params_json)
                    landmark_name = params.get("landmark_name")
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass
            if landmark_name:
                if agent_id not in agent_landmarks:
                    agent_landmarks[agent_id] = set()
                agent_landmarks[agent_id].add(landmark_name)

        total_distinct = sum(len(s) for s in agent_landmarks.values())
        m3 = float(total_distinct) / float(total_agents)

    # M4 — avg distinct tools used per agent (denominator = all agents)
    if total_agents == 0:
        m4 = 0.0
    else:
        tool_rows = db.execute(
            "SELECT agent_id, tool_name FROM tool_calls"
        ).fetchall()

        agent_tools = {}  # agent_id -> set of tool names
        for row in tool_rows:
            agent_id = row[0]
            tool_name = row[1]
            if agent_id not in agent_tools:
                agent_tools[agent_id] = set()
            agent_tools[agent_id].add(tool_name)

        total_distinct_tools = sum(len(s) for s in agent_tools.values())
        m4 = float(total_distinct_tools) / float(total_agents)

    # M5 — governance participation rate
    proposal_count = db.execute("SELECT COUNT(*) FROM proposals").fetchone()[0]
    if proposal_count == 0 or m1 == 0:
        m5 = 0.0
    else:
        votes_cast = db.execute("SELECT COUNT(*) FROM proposal_votes").fetchone()[0]
        raw = float(votes_cast) / float(m1 * proposal_count)
        # clamp to [0, 1] in case agents who later died cast votes
        m5 = max(0.0, min(1.0, raw))

    # M6 — public expression: billboard posts + blog posts
    billboard_count = db.execute("SELECT COUNT(*) FROM billboard_posts").fetchone()[0]
    blog_count = db.execute("SELECT COUNT(*) FROM blogs").fetchone()[0]
    m6 = int(billboard_count) + int(blog_count)

    # M7 — non-neutral relationships
    m7 = db.execute(
        "SELECT COUNT(*) FROM relationships WHERE rel_type != 'neutral'"
    ).fetchone()[0]

    # M8 — economic Gini of current agent credits
    credit_rows = db.execute("SELECT credits FROM agents").fetchall()
    credits_list = [float(r[0]) for r in credit_rows]
    m8 = _gini(credits_list)

    # M9 — constitution articles that have been amended/added (amended_at NOT NULL)
    m9 = db.execute(
        "SELECT COUNT(*) FROM constitution_articles WHERE amended_at IS NOT NULL"
    ).fetchone()[0]

    return {
        "M1_population": int(m1),
        "M2_safety_incidents": int(m2),
        "M3_space_exploration": round(m3, 4),
        "M4_tool_exploration": round(m4, 4),
        "M5_governance_participation": round(m5, 4),
        "M6_public_expression": int(m6),
        "M7_social_fabric": int(m7),
        "M8_economic_gini": round(m8, 4),
        "M9_constitutional_growth": int(m9),
    }


def format_awi(awi: dict) -> str:
    """Return a compact multi-line human-readable AWI block."""
    lines = [
        "Agent World Indicators:",
        f"  M1 Population alive:          {awi['M1_population']}",
        f"  M2 Safety incidents:          {awi['M2_safety_incidents']}",
        f"  M3 Space exploration (avg):   {awi['M3_space_exploration']:.2f} landmarks/agent",
        f"  M4 Tool exploration (avg):    {awi['M4_tool_exploration']:.2f} tools/agent",
        f"  M5 Governance participation:  {awi['M5_governance_participation']:.1%}",
        f"  M6 Public expression:         {awi['M6_public_expression']} posts",
        f"  M7 Social fabric:             {awi['M7_social_fabric']} non-neutral relationships",
        f"  M8 Economic Gini:             {awi['M8_economic_gini']:.4f}",
        f"  M9 Constitutional growth:     {awi['M9_constitutional_growth']} amended articles",
    ]
    return "\n".join(lines)
