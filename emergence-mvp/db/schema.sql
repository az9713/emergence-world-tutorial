CREATE TABLE IF NOT EXISTS landmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT,
    x REAL NOT NULL,
    y REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS landmark_tools (
    landmark_id INTEGER NOT NULL REFERENCES landmarks(id),
    tool_name TEXT NOT NULL,
    PRIMARY KEY (landmark_id, tool_name)
);

CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    personality TEXT NOT NULL,
    home_landmark_id INTEGER REFERENCES landmarks(id),
    location_id INTEGER REFERENCES landmarks(id),
    x REAL NOT NULL DEFAULT 120.0,
    y REAL NOT NULL DEFAULT 120.0,
    energy_need REAL NOT NULL DEFAULT 0.0,
    knowledge_need REAL NOT NULL DEFAULT 0.0,
    influence_need REAL NOT NULL DEFAULT 0.0,
    credits REAL NOT NULL DEFAULT 3.0,
    mood TEXT NOT NULL DEFAULT 'curious',
    last_energy_recharge_at REAL,
    last_knowledge_at REAL,
    last_influence_at REAL,
    is_alive INTEGER NOT NULL DEFAULT 1,
    death_energy_zero_since REAL,
    provider TEXT,
    model TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    content TEXT NOT NULL,
    memory_type TEXT NOT NULL CHECK(memory_type IN ('longterm','soul','diary')),
    created_at REAL NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS memory_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    summary_content TEXT NOT NULL,
    covers_count INTEGER NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    target_agent_id INTEGER NOT NULL REFERENCES agents(id),
    rel_type TEXT NOT NULL DEFAULT 'neutral',
    trust_level REAL NOT NULL DEFAULT 0.5,
    rationale TEXT,
    interaction_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    updated_at REAL NOT NULL,
    UNIQUE(agent_id, target_agent_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    speaker_id INTEGER NOT NULL REFERENCES agents(id),
    listener_id INTEGER REFERENCES agents(id),
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    location_id INTEGER REFERENCES landmarks(id)
);

CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposer_id INTEGER NOT NULL REFERENCES agents(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'others',
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','ACCEPTED','REJECTED','AWAITING_CLARIFICATION')),
    effect_type TEXT NOT NULL DEFAULT 'none',
    effect_payload TEXT,
    created_at REAL NOT NULL,
    resolved_at REAL
);

CREATE TABLE IF NOT EXISTS proposal_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id),
    voter_id INTEGER NOT NULL REFERENCES agents(id),
    vote TEXT NOT NULL CHECK(vote IN ('for','against')),
    created_at REAL NOT NULL,
    UNIQUE(proposal_id, voter_id)
);

CREATE TABLE IF NOT EXISTS pitch_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    cycle_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    evidence_url TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pitch_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES pitch_submissions(id),
    voter_id INTEGER NOT NULL REFERENCES agents(id),
    created_at REAL NOT NULL,
    UNIQUE(submission_id, voter_id)
);

CREATE TABLE IF NOT EXISTS credit_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_agent_id INTEGER REFERENCES agents(id),
    to_agent_id INTEGER REFERENCES agents(id),
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS constitution_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_number INTEGER NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    amended_at REAL
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    turn_number INTEGER NOT NULL,
    turn_type TEXT NOT NULL DEFAULT 'regular',
    tool_name TEXT NOT NULL,
    parameters_json TEXT,
    result_json TEXT,
    success INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS billboard_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    content TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS blogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host_id INTEGER NOT NULL REFERENCES agents(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    location_id INTEGER REFERENCES landmarks(id),
    sim_time REAL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS event_rsvps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id),
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    created_at REAL NOT NULL,
    UNIQUE(event_id, agent_id)
);

CREATE TABLE IF NOT EXISTS simulation_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    day_number INTEGER NOT NULL DEFAULT 1,
    turn_number INTEGER NOT NULL DEFAULT 0,
    sim_clock REAL NOT NULL DEFAULT 0,
    sim_seconds_per_turn REAL NOT NULL DEFAULT 7200,
    started_at REAL NOT NULL,
    last_turn_at REAL
);
