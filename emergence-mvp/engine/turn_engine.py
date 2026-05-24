import time
from config import TURN_TOOL_LIMIT, TURN_SLEEP_SECONDS, SECONDS_PER_SIM_DAY
from db.database import get_db
from engine.clock import sim_now, advance_sim_clock, sync_day_number, current_day
from engine.needs import update_agent_needs, check_death
from engine.system_prompt import build_system_prompt
from tools import registry
from engine import economy
from observer import terminal
from agents import llm_client


def _live_agents(db):
    return db.execute("SELECT id, name FROM agents WHERE is_alive=1 ORDER BY id").fetchall()


def run_simulation(num_turns, db=None, turn_runner=None, sleep=True):
    """Round-robin simulation loop.

    turn_runner: injectable for testing. Signature matches llm_client.run_agent_turn
        (system_prompt, tool_schemas, execute_fn, max_calls=...). Defaults to the real one.
    sleep: if True, sleep TURN_SLEEP_SECONDS (real) between turns for observability.
    """
    own_db = db is None
    if own_db:
        db = get_db()
    if turn_runner is None:
        turn_runner = llm_client.run_agent_turn

    # Build a stable round-robin order from currently-live agents.
    order = [row["id"] for row in _live_agents(db)]
    if not order:
        terminal.print_event("No live agents. Nothing to simulate.", kind="info")
        return
    rr = 0
    for _ in range(num_turns):
        # Skip dead agents; stop if everyone is dead.
        live_ids = {row["id"] for row in _live_agents(db)}
        if not live_ids:
            terminal.print_event("All agents are dead. Simulation over.", kind="death")
            break
        # advance round-robin pointer to next live agent
        for _scan in range(len(order)):
            agent_id = order[rr % len(order)]
            rr += 1
            if agent_id in live_ids:
                break
        else:
            break

        # increment turn_number
        db.execute("UPDATE simulation_state SET turn_number = turn_number + 1 WHERE id=1")
        db.commit()
        turn_number = db.execute("SELECT turn_number FROM simulation_state WHERE id=1").fetchone()["turn_number"]

        agent = db.execute(
            "SELECT id,name,location_id,credits,provider,model FROM agents WHERE id=?",
            (agent_id,),
        ).fetchone()
        agent_name = agent["name"]
        agent_provider = agent["provider"]  # None -> global default
        agent_model = agent["model"]        # None -> provider default

        # STEP 1: needs + death (on the simulated clock)
        needs = update_agent_needs(agent_id, db)
        if check_death(agent_id, db):
            terminal.print_death(agent_name)
            # still advance the clock for this turn
            advance_sim_clock(db)
            sync_day_number(db)
            economy.settle_completed_cycles(db, terminal)
            continue

        # STEP 2: prompt + tools
        prompt = build_system_prompt(agent_id, db)
        tool_names = registry.get_available_tool_names(agent_id, db)
        schemas = registry.get_tool_schemas(tool_names)

        # STEP 3: LLM tool-use loop
        def execute_fn(tool_name, inputs, _aid=agent_id, _tn=turn_number):
            return registry.execute_tool(_aid, tool_name, inputs, db, _tn, "regular")

        t0 = time.time()
        result = turn_runner(prompt, schemas, execute_fn, max_calls=TURN_TOOL_LIMIT,
                             provider=agent_provider, model=agent_model)
        elapsed = time.time() - t0

        # STEP 4: observer
        loc_row = db.execute(
            "SELECT l.name AS n FROM agents a LEFT JOIN landmarks l ON a.location_id=l.id WHERE a.id=?",
            (agent_id,),
        ).fetchone()
        location = loc_row["n"] if loc_row and loc_row["n"] else "?"
        credits = db.execute("SELECT credits FROM agents WHERE id=?", (agent_id,)).fetchone()["credits"]
        sim_hour = int(sim_now(db) // 3600)
        day = current_day(db)
        terminal.print_turn(
            turn_number, day, sim_hour, agent_name, location, needs, credits,
            result.get("tool_calls", []), result.get("final_text", ""), elapsed,
            model_label=(agent_model or agent_provider),
        )
        if result.get("error"):
            terminal.print_event(f"LLM error for {agent_name}: {result['error']}", kind="death")

        # STEP 5: reactive conversations — HOOK (implemented in a later task).
        # If engine.reactive exists, let it react to any say_to_agent calls this turn.
        try:
            from engine import reactive
            reactive.handle_reactions(agent_id, result.get("tool_calls", []), db, turn_runner, terminal)
        except ImportError:
            pass

        # STEP 6: advance simulated clock, sync day, settle finished pitch cycles
        advance_sim_clock(db)
        sync_day_number(db)
        economy.settle_completed_cycles(db, terminal)

        # STEP 7: pacing (real-time, observability only)
        if sleep and TURN_SLEEP_SECONDS:
            time.sleep(TURN_SLEEP_SECONDS)

    terminal.print_summary(db)
    if own_db:
        db.close()
