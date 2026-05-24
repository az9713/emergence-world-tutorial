"""batch.py — run multiple simulations and aggregate AWI metrics.

Usage:
    python batch.py --runs N [--scenario NAME] [--turns T] [--dry-run]

For each run:
  1. Apply scenario config overrides (if any)
  2. Re-seed sim.db via db.seed.seed()
  3. Run the simulation for T turns
  4. Copy sim.db to runs/batch-{i}.db
  5. Compute AWI metrics on the copy

After all runs:
  - Print a comparison table (alive count, total credits, Gini, safety incidents)
  - Write runs/batch-summary.csv (all 9 AWI metrics + run index)
"""

import sys
import os
import csv
import shutil
import argparse

# Windows-safe unicode output
sys.stdout.reconfigure(encoding="utf-8")

# Project root on sys.path so all emergence-mvp modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Fake turn_runner for --dry-run (no API key needed)
# ---------------------------------------------------------------------------

def _make_dry_run_runner():
    """Return a minimal scripted fake turn_runner for offline testing.

    Signature matches llm_client.run_agent_turn:
        (system_prompt, tool_schemas, execute_fn, max_calls=None, **kw) -> dict

    Executes one go_to_place("Town Hall") per turn via execute_fn so the
    full pipeline (tool execution, DB writes, observer, clock) is exercised.
    """
    def fake_runner(system_prompt, tool_schemas, execute_fn, max_calls=None, **kw):
        ok, res = execute_fn("go_to_place", {"landmark_name": "Town Hall"})
        tool_calls = [
            {
                "tool_name": "go_to_place",
                "inputs": {"landmark_name": "Town Hall"},
                "success": ok,
                "result": res,
            }
        ]
        return {
            "tool_calls": tool_calls,
            "final_text": "",
            "stop_reason": "no_tool_use",
            "error": None,
        }

    return fake_runner


# ---------------------------------------------------------------------------
# AWI helper — lazy import so batch loads even when awi.py isn't ready
# ---------------------------------------------------------------------------

def _try_compute_awi(db_path):
    """Open db_path and compute AWI metrics. Returns a dict of metrics or a
    fallback dict of zeros if engine.awi is not yet available."""
    try:
        from engine.awi import compute_awi
        import sqlite3
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        metrics = compute_awi(db)
        db.close()
        return metrics
    except ImportError:
        print("  [warning] engine.awi not available — AWI metrics will be zero for this run.")
        return {
            "M1_population": 0,
            "M2_safety_incidents": 0,
            "M3_space_exploration": 0,
            "M4_tool_exploration": 0,
            "M5_governance_participation": 0,
            "M6_public_expression": 0,
            "M7_social_fabric": 0,
            "M8_economic_gini": 0,
            "M9_constitutional_growth": 0,
        }
    except Exception as exc:
        print(f"  [warning] compute_awi failed: {exc}")
        return {
            "M1_population": 0,
            "M2_safety_incidents": 0,
            "M3_space_exploration": 0,
            "M4_tool_exploration": 0,
            "M5_governance_participation": 0,
            "M6_public_expression": 0,
            "M7_social_fabric": 0,
            "M8_economic_gini": 0,
            "M9_constitutional_growth": 0,
        }


def _query_run_stats(db_path):
    """Return (alive_count, total_credits) by querying the copied DB directly."""
    import sqlite3
    try:
        db = sqlite3.connect(db_path)
        row = db.execute(
            "SELECT COUNT(*) AS alive, SUM(credits) AS total FROM agents WHERE is_alive=1"
        ).fetchone()
        alive = row[0] if row[0] is not None else 0
        total_credits = round(row[1], 2) if row[1] is not None else 0.0
        db.close()
        return alive, total_credits
    except Exception as exc:
        print(f"  [warning] could not query run stats from {db_path}: {exc}")
        return 0, 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run multiple Emergence World simulations and aggregate results."
    )
    parser.add_argument("--runs", type=int, required=True, help="number of simulation runs")
    parser.add_argument("--scenario", type=str, default=None, help="named scenario preset")
    parser.add_argument("--turns", type=int, default=12, help="agent turns per run (default 12)")
    parser.add_argument("--dry-run", action="store_true",
                        help="use a scripted fake LLM runner (no API key required)")
    args = parser.parse_args()

    # Resolve seed overrides from scenario (if any)
    seed_overrides = {}
    if args.scenario:
        from scenarios import apply_scenario
        seed_overrides = apply_scenario(args.scenario)
        print(f"Scenario: {args.scenario!r} applied.")

    # Ensure runs/ directory exists
    runs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")
    os.makedirs(runs_dir, exist_ok=True)

    turn_runner = _make_dry_run_runner() if args.dry_run else None
    if args.dry_run:
        print("Mode: dry-run (scripted fake LLM, no API calls)")

    # Collect per-run results
    run_results = []  # list of dicts: {run, alive, total_credits, gini, safety_incidents, ...awi}

    for i in range(1, args.runs + 1):
        print(f"\n--- Run {i}/{args.runs} ({args.turns} turns) ---")

        # Re-seed for a clean slate on every run
        from db.seed import seed
        seed(seed_overrides)

        # Run simulation
        from engine.turn_engine import run_simulation
        run_simulation(args.turns, sleep=False, turn_runner=turn_runner)

        # Copy sim.db to runs/
        db_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim.db")
        db_dest = os.path.join(runs_dir, f"batch-{i}.db")
        shutil.copy(db_src, db_dest)
        print(f"  Saved: runs/batch-{i}.db")

        # Compute AWI metrics from the copy
        awi = _try_compute_awi(db_dest)

        # Query alive / credits directly (M1_population may be alive count, but
        # total_credits requires a SUM query not covered by AWI)
        alive, total_credits = _query_run_stats(db_dest)

        # Gini from AWI; safety incidents from AWI
        gini = awi.get("M8_economic_gini", 0)
        safety = awi.get("M2_safety_incidents", 0)

        record = {"run": i, "alive": alive, "total_credits": total_credits,
                  "gini": gini, "safety_incidents": safety}
        record.update(awi)
        run_results.append(record)

    # ------------------------------------------------------------------
    # Print comparison table
    # ------------------------------------------------------------------
    print("\n" + "=" * 62)
    print(f"{'Run':>4}  {'Alive':>6}  {'Credits':>10}  {'Gini':>6}  {'Safety':>7}")
    print("-" * 62)
    for r in run_results:
        print(
            f"{r['run']:>4}  {r['alive']:>6}  {r['total_credits']:>10.2f}"
            f"  {r['gini']:>6.4f}  {r['safety_incidents']:>7}"
        )
    print("=" * 62)

    # ------------------------------------------------------------------
    # Write runs/batch-summary.csv
    # ------------------------------------------------------------------
    awi_keys = [
        "M1_population", "M2_safety_incidents", "M3_space_exploration",
        "M4_tool_exploration", "M5_governance_participation",
        "M6_public_expression", "M7_social_fabric",
        "M8_economic_gini", "M9_constitutional_growth",
    ]
    csv_path = os.path.join(runs_dir, "batch-summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["run_index"] + awi_keys, extrasaction="ignore")
        writer.writeheader()
        for r in run_results:
            row = {"run_index": r["run"]}
            for k in awi_keys:
                row[k] = r.get(k, 0)
            writer.writerow(row)

    print(f"\nSummary written to: runs/batch-summary.csv")


if __name__ == "__main__":
    main()
