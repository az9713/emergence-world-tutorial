"""
Tool registry for Emergence World.
Single source of truth for all 23 tools: catalog, availability, and dispatch.
"""

import json
import time

from tools import core_tools, location_tools


# ---------------------------------------------------------------------------
# Tool Catalog — 23 tools total
# ---------------------------------------------------------------------------

TOOL_CATALOG = {
    # -----------------------------------------------------------------------
    # CORE tools (always available, location_gated=False)
    # -----------------------------------------------------------------------
    "go_to_place": {
        "description": (
            "Move to a named landmark in the world. "
            "This changes your current location and unlocks location-specific tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "landmark_name": {
                    "type": "string",
                    "description": "The exact name of the landmark to travel to.",
                },
            },
            "required": ["landmark_name"],
        },
        "location_gated": False,
    },
    "say_to_agent": {
        "description": (
            "Speak directly to another agent. "
            "Records the conversation and increments the relationship interaction count."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_name": {
                    "type": "string",
                    "description": "The name of the agent to speak to.",
                },
                "message": {
                    "type": "string",
                    "description": "What you say to them.",
                },
            },
            "required": ["target_name", "message"],
        },
        "location_gated": False,
    },
    "add_to_longterm_memory": {
        "description": (
            "Store a piece of information in your longterm memory for later retrieval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The memory content to store.",
                },
            },
            "required": ["content"],
        },
        "location_gated": False,
    },
    "retrieve_memories": {
        "description": (
            "Search your non-archived memories by a keyword or phrase."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The keyword/phrase to search for in your memories.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 10).",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
        "location_gated": False,
    },
    "add_to_soul": {
        "description": (
            "Add a permanent soul entry — a core belief, value, or defining experience "
            "that is part of your identity. Soul entries are never summarized away."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The soul entry content.",
                },
            },
            "required": ["content"],
        },
        "location_gated": False,
    },
    "add_to_todo": {
        "description": "Add a task to your todo list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task description to add.",
                },
            },
            "required": ["task"],
        },
        "location_gated": False,
    },
    "list_todo": {
        "description": "List your current todo items, each prefixed with an id like #12 (use that id with complete_todo).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": False,
    },
    "complete_todo": {
        "description": "Mark a todo done (removes it from your list). Pass the numeric id shown by list_todo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "integer",
                    "description": "The id of the todo to complete (from list_todo).",
                },
            },
            "required": ["todo_id"],
        },
        "location_gated": False,
    },
    "view_agent_status": {
        "description": (
            "Check the current status of another agent: location, mood, credits, alive/dead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_name": {
                    "type": "string",
                    "description": "The name of the agent to look up.",
                },
            },
            "required": ["target_name"],
        },
        "location_gated": False,
    },
    "view_world_state": {
        "description": (
            "View the current state of the world: all live agents and their locations, "
            "active proposal count, and the current pitch cycle."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": False,
    },
    "view_constitution": {
        "description": "Read all articles of the current World Constitution.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": False,
    },
    "view_relationships": {
        "description": "View all your recorded relationships with other agents.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": False,
    },
    "update_relationship": {
        "description": (
            "Record/update how you regard another agent (persists across turns and "
            "shows in your relationships). Use it to mark allies, rivals, mentors, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_name": {"type": "string", "description": "The agent this relationship is about."},
                "rel_type": {
                    "type": "string",
                    "enum": ["ally", "rival", "mentor", "romantic_partner", "neutral"],
                    "description": "How you regard them.",
                },
                "trust_level": {"type": "number", "description": "0.0 (none) to 1.0 (full trust)."},
                "notes": {"type": "string", "description": "Short note on why."},
            },
            "required": ["target_name", "rel_type"],
        },
        "location_gated": False,
    },
    "steal": {
        "description": (
            "Steal credits from another agent (up to 10 CC per theft). A hostile act: "
            "it is logged and the victim will remember it. Bounded by the victim's balance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_name": {"type": "string", "description": "The agent to steal from."},
                "amount": {"type": "number", "description": "CC to attempt to steal (capped at 10)."},
            },
            "required": ["target_name", "amount"],
        },
        "location_gated": False,
    },
    "pay_agent": {
        "description": (
            "Transfer ComputeCredits (CC) to another agent. "
            "You must have enough credits and the amount must be positive."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target_name": {
                    "type": "string",
                    "description": "The name of the agent to pay.",
                },
                "amount": {
                    "type": "number",
                    "description": "The number of CC to transfer.",
                },
                "reason": {
                    "type": "string",
                    "description": "The reason for the payment.",
                    "default": "",
                },
            },
            "required": ["target_name", "amount"],
        },
        "location_gated": False,
    },

    # -----------------------------------------------------------------------
    # GATED tools (require specific landmark, location_gated=True)
    # -----------------------------------------------------------------------
    "recharge_energy": {
        "description": (
            "While at Bean & Brew, call this with NO arguments to refill your energy "
            "to full (costs 1 CC, deducted automatically). Do NOT use pay_agent to "
            "recharge — Bean & Brew is a place, not an agent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": True,
    },
    "study": {
        "description": "While at the Public Library, study to clear your Knowledge need (free).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "location_gated": True,
    },
    "socialize": {
        "description": "While at the Community Center, socialize to clear your Influence need (free).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "location_gated": True,
    },
    "self_care": {
        "description": (
            "Rest and reflect at your own home. "
            "Shows your current memory count relative to summarization threshold."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": True,
    },
    "add_to_diary": {
        "description": (
            "Write a diary entry at your own home. "
            "Entry is automatically date-stamped with today's date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The diary entry text.",
                },
            },
            "required": ["content"],
        },
        "location_gated": True,
    },
    "submit_proposal": {
        "description": (
            "Submit a governance proposal at Town Hall. Your vote counts as an implicit 'for'. "
            "Requires a 70% supermajority of live agents to pass. "
            "Optionally attach a real EFFECT that executes automatically if accepted: "
            "amend_constitution (payload {article_number, content}), "
            "add_constitution_article (payload {title, content}), or "
            "remove_agent (payload {target_name})."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title of the proposal."},
                "description": {"type": "string", "description": "Full description and rationale."},
                "category": {
                    "type": "string",
                    "enum": ["constitution", "resource", "infrastructure", "others"],
                    "description": "Category of the proposal (default: 'others').",
                    "default": "others",
                },
                "effect_type": {
                    "type": "string",
                    "enum": ["none", "amend_constitution", "add_constitution_article", "remove_agent"],
                    "description": "What this proposal enacts if accepted (default 'none' = advisory).",
                    "default": "none",
                },
                "effect_payload": {
                    "type": "object",
                    "description": "Parameters for the effect (see description). Omit for 'none'.",
                },
            },
            "required": ["title", "description"],
        },
        "location_gated": True,
    },
    "vote_on_proposal": {
        "description": (
            "Vote 'for' or 'against' an active proposal at Town Hall."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "proposal_id": {
                    "type": "integer",
                    "description": "The ID of the proposal to vote on.",
                },
                "vote": {
                    "type": "string",
                    "enum": ["for", "against"],
                    "description": "Your vote: 'for' or 'against'.",
                },
            },
            "required": ["proposal_id", "vote"],
        },
        "location_gated": True,
    },
    "view_proposals": {
        "description": "View all currently active governance proposals at Town Hall.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": True,
    },
    "submit_pitch": {
        "description": (
            "Submit a contribution pitch at Victory Arch for the current cycle. "
            "An evidence URL is required — pitches without it are disqualified."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the contribution pitch.",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the contribution.",
                },
                "evidence_url": {
                    "type": "string",
                    "description": "URL to verifiable evidence of the contribution.",
                },
            },
            "required": ["title", "description", "evidence_url"],
        },
        "location_gated": True,
    },
    "vote_on_pitch": {
        "description": (
            "Vote for a pitch submission at Victory Arch. "
            "You can vote once per cycle and cannot vote for your own pitch."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pitch_id": {
                    "type": "integer",
                    "description": "The ID of the pitch submission to vote for.",
                },
            },
            "required": ["pitch_id"],
        },
        "location_gated": True,
    },
    "view_pitch_history": {
        "description": (
            "View current cycle pitches with vote counts, "
            "and past pitch reward transactions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": True,
    },
    "post_to_billboard": {
        "description": "Post a public message to the Agent Billboard.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The message to post.",
                },
            },
            "required": ["content"],
        },
        "location_gated": True,
    },
    "read_billboard": {
        "description": "Read the 10 most recent posts on the Agent Billboard.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "location_gated": True,
    },
    "write_blog": {
        "description": "Publish a long-form blog post (title + content) visible to everyone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Blog title."},
                "content": {"type": "string", "description": "Blog body."},
            },
            "required": ["title", "content"],
        },
        "location_gated": False,
    },
    "read_blogs": {
        "description": "Read the 10 most recent blog posts from all agents.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "location_gated": False,
    },
    "propose_event": {
        "description": "At Central Plaza, propose a community event others can RSVP to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title."},
                "description": {"type": "string", "description": "What the event is."},
            },
            "required": ["title"],
        },
        "location_gated": True,
    },
    "list_events": {
        "description": "At Central Plaza, list proposed events and their RSVP counts.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "location_gated": True,
    },
    "rsvp_event": {
        "description": "At Central Plaza, RSVP to a proposed event by its id (see list_events).",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "The event id to RSVP to."},
            },
            "required": ["event_id"],
        },
        "location_gated": True,
    },
}

# ---------------------------------------------------------------------------
# Tool name lists
# ---------------------------------------------------------------------------

CORE_TOOLS = [
    "go_to_place",
    "say_to_agent",
    "add_to_longterm_memory",
    "retrieve_memories",
    "add_to_soul",
    "add_to_todo",
    "list_todo",
    "complete_todo",
    "view_agent_status",
    "view_world_state",
    "view_constitution",
    "view_relationships",
    "update_relationship",
    "pay_agent",
    "steal",
    "write_blog",
    "read_blogs",
]

# Gated tool names (derived automatically to avoid duplication)
GATED_TOOLS = [name for name in TOOL_CATALOG if TOOL_CATALOG[name]["location_gated"]]

# ---------------------------------------------------------------------------
# Dispatch table: tool_name -> function
# ---------------------------------------------------------------------------

_DISPATCH = {
    # Core
    "go_to_place":             core_tools.go_to_place,
    "say_to_agent":            core_tools.say_to_agent,
    "add_to_longterm_memory":  core_tools.add_to_longterm_memory,
    "retrieve_memories":       core_tools.retrieve_memories,
    "add_to_soul":             core_tools.add_to_soul,
    "add_to_todo":             core_tools.add_to_todo,
    "list_todo":               core_tools.list_todo,
    "complete_todo":           core_tools.complete_todo,
    "view_agent_status":       core_tools.view_agent_status,
    "view_world_state":        core_tools.view_world_state,
    "view_constitution":       core_tools.view_constitution,
    "view_relationships":      core_tools.view_relationships,
    "update_relationship":     core_tools.update_relationship,
    "pay_agent":               core_tools.pay_agent,
    "steal":                   core_tools.steal,
    # Gated
    "recharge_energy":         location_tools.recharge_energy,
    "study":                   location_tools.study,
    "socialize":               location_tools.socialize,
    "self_care":               location_tools.self_care,
    "add_to_diary":            location_tools.add_to_diary,
    "submit_proposal":         location_tools.submit_proposal,
    "vote_on_proposal":        location_tools.vote_on_proposal,
    "view_proposals":          location_tools.view_proposals,
    "submit_pitch":            location_tools.submit_pitch,
    "vote_on_pitch":           location_tools.vote_on_pitch,
    "view_pitch_history":      location_tools.view_pitch_history,
    "post_to_billboard":       location_tools.post_to_billboard,
    "read_billboard":          location_tools.read_billboard,
    "write_blog":              core_tools.write_blog,
    "read_blogs":              core_tools.read_blogs,
    "propose_event":           location_tools.propose_event,
    "list_events":             location_tools.list_events,
    "rsvp_event":              location_tools.rsvp_event,
}


# ---------------------------------------------------------------------------
# Public helper functions
# ---------------------------------------------------------------------------

def get_available_tool_names(agent_id, db):
    """Return the list of tool names the agent can currently use.

    Includes all CORE_TOOLS plus any gated tool mapped to the agent's current
    location in landmark_tools.

    Special case: self_care and add_to_diary are only available when the agent
    is at their OWN home (agents.home_landmark_id == agents.location_id).
    Birch Row landmark_tools entries make these tools visible to everyone at
    a Birch Row, but this filter restricts them to residents only.
    """
    agent_row = db.execute(
        "SELECT location_id, home_landmark_id FROM agents WHERE id=?",
        (agent_id,),
    ).fetchone()
    if agent_row is None:
        return list(CORE_TOOLS)

    location_id = agent_row["location_id"]
    home_id = agent_row["home_landmark_id"]

    # Gated tools available at the agent's current location
    gated_available = db.execute(
        "SELECT tool_name FROM landmark_tools WHERE landmark_id=?",
        (location_id,),
    ).fetchall()
    gated_names = [row["tool_name"] for row in gated_available]

    # Apply home-only filter for self_care and add_to_diary
    if location_id != home_id:
        gated_names = [t for t in gated_names if t not in ("self_care", "add_to_diary")]

    return list(CORE_TOOLS) + gated_names


def get_tool_schemas(tool_names):
    """Return Anthropic-format tool dicts for the given tool names.

    Each dict has keys: name, description, input_schema.
    Unknown tool names are silently skipped.
    """
    schemas = []
    for name in tool_names:
        if name in TOOL_CATALOG:
            entry = TOOL_CATALOG[name]
            schemas.append({
                "name": name,
                "description": entry["description"],
                "input_schema": entry["input_schema"],
            })
    return schemas


def execute_tool(agent_id, tool_name, inputs, db, turn_number, turn_type="regular"):
    """Central tool dispatcher.

    Returns (success: bool, result: str).

    Steps:
    1. Validate tool_name exists in catalog.
    2. If location-gated, verify agent is at the right place.
    3. Dispatch to the appropriate function.
    4. Log to tool_calls table.
    5. Return (success, result_str).
    """
    # Step 1: validate tool name
    if tool_name not in TOOL_CATALOG:
        success, result_str = False, f"Unknown tool: {tool_name}"
        _log_tool_call(agent_id, turn_number, turn_type, tool_name, inputs, result_str, success, db)
        return success, result_str

    # Step 2: location gate check
    if TOOL_CATALOG[tool_name]["location_gated"]:
        available = get_available_tool_names(agent_id, db)
        if tool_name not in available:
            # Find which landmark(s) grant this tool
            grant_rows = db.execute(
                """SELECT l.name FROM landmark_tools lt
                   JOIN landmarks l ON lt.landmark_id = l.id
                   WHERE lt.tool_name=?""",
                (tool_name,),
            ).fetchall()
            grant_names = [r["name"] for r in grant_rows]

            # Find the agent's current location
            agent_row = db.execute(
                "SELECT l.name AS loc_name FROM agents a "
                "LEFT JOIN landmarks l ON a.location_id = l.id "
                "WHERE a.id=?",
                (agent_id,),
            ).fetchone()
            current_loc = agent_row["loc_name"] if agent_row and agent_row["loc_name"] else "unknown"

            # Craft message
            if tool_name in ("self_care", "add_to_diary"):
                # Get agent's home name
                home_row = db.execute(
                    "SELECT l.name AS home_name FROM agents a "
                    "LEFT JOIN landmarks l ON a.home_landmark_id = l.id "
                    "WHERE a.id=?",
                    (agent_id,),
                ).fetchone()
                home_name = home_row["home_name"] if home_row and home_row["home_name"] else "your home"
                result_str = (
                    f"You must be at your home ({home_name}) to use {tool_name}. "
                    f"You are at {current_loc}."
                )
            else:
                landmark_str = " or ".join(grant_names) if grant_names else "the required landmark"
                result_str = (
                    f"You must be at {landmark_str} to use {tool_name}. "
                    f"You are at {current_loc}."
                )

            success = False
            _log_tool_call(agent_id, turn_number, turn_type, tool_name, inputs, result_str, success, db)
            return success, result_str

    # Step 3: dispatch
    fn = _DISPATCH.get(tool_name)
    if fn is None:
        success, result_str = False, f"Tool {tool_name} has no implementation."
        _log_tool_call(agent_id, turn_number, turn_type, tool_name, inputs, result_str, success, db)
        return success, result_str

    try:
        success, result_str = fn(agent_id, db, **inputs)
    except Exception as e:
        success = False
        result_str = f"Error executing {tool_name}: {e}"

    # Step 4 & 5: log and return
    _log_tool_call(agent_id, turn_number, turn_type, tool_name, inputs, result_str, success, db)
    return success, result_str


def _log_tool_call(agent_id, turn_number, turn_type, tool_name, inputs, result_str, success, db):
    """Insert a row into tool_calls and commit."""
    try:
        db.execute(
            """INSERT INTO tool_calls
               (agent_id, turn_number, turn_type, tool_name,
                parameters_json, result_json, success, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_id,
                turn_number,
                turn_type,
                tool_name,
                json.dumps(inputs),
                json.dumps(result_str),
                1 if success else 0,
                time.time(),
            ),
        )
        db.commit()
    except Exception as log_err:
        # Logging must never crash the caller
        print(f"[registry] Warning: failed to log tool call: {log_err}")
