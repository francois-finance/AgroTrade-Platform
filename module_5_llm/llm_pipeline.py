"""
AgroTrade Platform — Module 5 : LLM Intelligence Pipeline
"""

from rich.console import Console
from rich.table import Table
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_5_llm.generators.trade_idea_generator import (
    generate_trade_ideas, generate_daily_report,
    print_trade_ideas, print_daily_report
)

console = Console()


def run_llm_pipeline():
    console.print("\n[bold magenta]🤖 AgroTrade — Module 5 : LLM Intelligence[/bold magenta]\n")
    status = {}

    # 1. Rapport quotidien
    console.rule("[bold cyan]1/2 — Daily Market Report[/bold cyan]")
    try:
        report = generate_daily_report(save=True)
        print_daily_report(report)
        status["Daily Report"] = ("✅", 1, "rapport généré")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["Daily Report"] = ("❌", 0, str(e))

    # 2. Trade ideas
    console.rule("[bold cyan]2/2 — Trade Ideas Generator[/bold cyan]")
    try:
        ideas = generate_trade_ideas(save=True)
        print_trade_ideas(ideas)
        nb = len(ideas.get("trade_ideas", []))
        status["Trade Ideas"] = ("✅", nb, "ideas générées")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["Trade Ideas"] = ("❌", 0, str(e))

    # Rapport
    console.print()
    table = Table(title="📊 Module 5 — Rapport d'État")
    table.add_column("Composant", style="cyan")
    table.add_column("Status",    style="green")
    table.add_column("Volume",    style="yellow")
    table.add_column("Détail",    style="white")
    for comp, (st, vol, detail) in status.items():
        table.add_row(comp, st, str(vol), detail)
    console.print(table)


if __name__ == "__main__":
    run_llm_pipeline()