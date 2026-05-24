"""
Terminal observer for Emergence World — rich-formatted simulation output.

All functions are module-level so the engine and economy modules can import
this module and call terminal.print_event(...) directly.
"""

import io
import json
import sys
from rich.console import Console
from rich.rule import Rule
from rich.text import Text
from rich.table import Table

# On Windows, Python may default stdout to cp1252 which cannot encode many
# Unicode characters. Wrap stdout in a UTF-8 TextIOWrapper so rich always has
# a UTF-8-capable stream, then force_terminal=True so rich doesn't fall back
# to the legacy Windows renderer that re-encodes through the original codec.
def _make_console():
    if hasattr(sys.stdout, "buffer"):
        try:
            utf8_out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
            return Console(file=utf8_out, force_terminal=True, highlight=False)
        except Exception:
            pass
    return Console(highlight=False)

console = _make_console()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _short_inputs(inputs, max_len=60):
    """Return a compact string representation of tool inputs, capped at max_len chars."""
    if not inputs:
        return ""
    try:
        s = json.dumps(inputs, ensure_ascii=False)
    except Exception:
        s = str(inputs)
    if len(s) > max_len:
        s = s[:max_len - 3] + "..."
    return s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def print_turn(
    turn_number,
    day,
    sim_hour,
    agent_name,
    location,
    needs,
    credits,
    tool_calls,
    final_text,
    elapsed_s,
    model_label=None,
):
    """Render one agent turn as a rich terminal block."""
    console.print(Rule(
        f"TURN {turn_number} | Day {day} | sim {sim_hour}h",
        style="bold white",
    ))

    model_suffix = f"  [dim]({model_label})[/dim]" if model_label else ""
    console.print(f"[bold cyan]  \U0001f916 {agent_name}[/bold cyan]  @  [yellow]{location}[/yellow]{model_suffix}")

    # Needs line — colour energy based on urgency
    energy = needs.get("energy", 0.0)
    knowledge = needs.get("knowledge", 0.0)
    influence = needs.get("influence", 0.0)

    if energy > 0.70:
        energy_style = "bold red"
    elif energy > 0.50:
        energy_style = "yellow"
    else:
        energy_style = "green"

    energy_text = Text()
    energy_text.append("     ⚡ Energy ")
    energy_text.append(f"{energy:.0%}", style=energy_style)
    energy_text.append(f"   \U0001f4da Knowledge {knowledge:.0%}")
    energy_text.append(f"   \U0001f4ab Influence {influence:.0%}")
    energy_text.append(f"   \U0001f4b0 {credits:g} CC", style="bold yellow")
    console.print(energy_text)

    # Tool call lines
    for tc in tool_calls:
        tool_name = tc.get("tool_name", "?")
        inputs = tc.get("inputs", {})
        success = tc.get("success", False)

        # For say_to_agent, show the message content specially
        if tool_name == "say_to_agent":
            target = inputs.get("target_name", "?")
            message = inputs.get("message", "")
            if len(message) > 55:
                message = message[:52] + "..."
            display_args = f'to={target} "{message}"'
        else:
            display_args = _short_inputs(inputs)

        tick = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"
        console.print(f"     [dim]→[/dim] [cyan]{tool_name}[/cyan]({display_args}) {tick}")

    # Summary line
    n_calls = len(tool_calls)
    console.print(f"     [dim]{n_calls} tool call{'s' if n_calls != 1 else ''} | {elapsed_s:.1f}s[/dim]")

    # Optional final text
    if final_text and final_text.strip():
        console.print(f"     [dim italic]{final_text[:200]}[/dim italic]")

    console.print()


def print_event(text, kind="info"):
    """Print a single-line coloured banner event."""
    style_map = {
        "economy": "bold green",
        "governance": "bold yellow",
        "death": "bold red",
        "info": "bold cyan",
    }
    style = style_map.get(kind, "bold cyan")
    console.print(f"[{style}]  {text}[/{style}]")


def print_death(agent_name, cause="energy depletion"):
    """Bold red separator block for agent death."""
    console.print(Rule(style="bold red"))
    console.print(
        f"[bold red]  \U0001f480 {agent_name} HAS DIED — {cause}[/bold red]"
    )
    console.print(Rule(style="bold red"))
    console.print()


def print_reaction(listener_name, speaker_name, tool_calls):
    """Print an indented dim block for an overheard reaction turn."""
    console.print(
        f"  [dim]↳ [REACTION] {listener_name} (overheard {speaker_name})[/dim]"
    )
    for tc in tool_calls:
        tool_name = tc.get("tool_name", "?")
        inputs = tc.get("inputs", {})
        success = tc.get("success", False)

        if tool_name == "say_to_agent":
            target = inputs.get("target_name", "?")
            message = inputs.get("message", "")
            if len(message) > 55:
                message = message[:52] + "..."
            display_args = f'to={target} "{message}"'
        else:
            display_args = _short_inputs(inputs)

        tick = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"
        console.print(f"       [dim]→[/dim] [dim cyan]{tool_name}[/dim cyan]({display_args}) {tick}")

    console.print()


def print_header(text):
    """Print a bold header rule."""
    console.print(Rule(text, style="bold magenta"))


def print_summary(db):
    """Print end-of-run summary: agent states and any proposals."""
    console.print(Rule("SIMULATION SUMMARY", style="bold magenta"))

    # Agent summary table
    agents = db.execute(
        "SELECT name, credits, is_alive, energy_need FROM agents ORDER BY name"
    ).fetchall()

    if agents:
        table = Table(title="Agents", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Credits", justify="right")
        table.add_column("Energy Need", justify="right")
        table.add_column("Status", justify="center")

        for a in agents:
            status = "[green]alive[/green]" if a["is_alive"] else "[bold red]DEAD[/bold red]"
            energy_val = a["energy_need"] if a["energy_need"] is not None else 0.0
            table.add_row(
                a["name"],
                f"{a['credits']:g} CC",
                f"{energy_val:.0%}",
                status,
            )
        console.print(table)

    # Proposals summary
    proposals = db.execute(
        "SELECT title, status FROM proposals ORDER BY id"
    ).fetchall()

    if proposals:
        ptable = Table(title="Proposals", show_header=True, header_style="bold yellow")
        ptable.add_column("Title", style="white")
        ptable.add_column("Status", justify="center")

        for p in proposals:
            ptable.add_row(p["title"], p["status"])
        console.print(ptable)

    # Agent World Indicators
    from engine.awi import compute_awi, format_awi
    try:
        awi = compute_awi(db)
        awi_text = format_awi(awi)
        console.print()
        console.print(Rule("AGENT WORLD INDICATORS", style="bold blue"))
        for line in awi_text.splitlines():
            console.print(f"  [cyan]{line}[/cyan]")
    except Exception as exc:  # pragma: no cover
        console.print(f"[yellow]  (AWI unavailable: {exc})[/yellow]")

    console.print(Rule(style="bold magenta"))
