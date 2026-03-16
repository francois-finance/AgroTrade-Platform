"""
AgroTrade Platform — Module 6 : Backtesting Pipeline
"""

from rich.console import Console
from rich.table import Table
from rich.rule import Rule
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_6_backtest.strategies.momentum_strategy       import run_momentum_backtest
from module_6_backtest.strategies.crush_strategy          import run_crush_backtest
from module_6_backtest.strategies.calendar_spread_strategy import run_calendar_backtest
from module_6_backtest.analysis.performance_analyzer      import compute_metrics, print_performance_report, save_results

console = Console()


def run_backtest_pipeline():
    console.print("\n[bold magenta]📈 AgroTrade — Module 6 : Backtesting[/bold magenta]\n")

    backtests = [
        {"id": "momentum_wheat",   "label": "Momentum — Blé",          "fn": lambda: run_momentum_backtest("wheat")},
        {"id": "momentum_corn",    "label": "Momentum — Maïs",         "fn": lambda: run_momentum_backtest("corn")},
        {"id": "momentum_soybean", "label": "Momentum — Soja",         "fn": lambda: run_momentum_backtest("soybean")},
        {"id": "crush_soybean",    "label": "Crush Spread — Soja",     "fn": run_crush_backtest},
        {"id": "calendar_wheat",   "label": "Calendar Spread — Blé",   "fn": lambda: run_calendar_backtest("wheat")},
    ]

    summary_rows = []

    for bt in backtests:
        console.print(Rule(f"[bold cyan]{bt['label']}[/bold cyan]"))
        try:
            result  = bt["fn"]()
            metrics = compute_metrics(result)
            print_performance_report(metrics)
            save_results(metrics, bt["id"])

            summary_rows.append({
                "Stratégie":       bt["label"],
                "Rendement/an":    f"{metrics['annual_return_pct']:+.1f}%",
                "Sharpe":          f"{metrics['sharpe_ratio']:.2f}",
                "Max DD":          f"{metrics['max_drawdown_pct']:.1f}%",
                "Win Rate":        f"{metrics['win_rate_pct']:.1f}%",
                "Profit Factor":   f"{metrics['profit_factor']:.2f}",
                "Nb Trades":       str(metrics["nb_trades"]),
            })
        except Exception as e:
            console.print(f"[red]✗ Erreur : {e}[/red]")
            import traceback
            traceback.print_exc()

    # Tableau comparatif final
    if summary_rows:
        console.print(Rule("[bold magenta]📊 COMPARAISON STRATÉGIES[/bold magenta]"))
        table = Table(title="Résumé Backtest — Toutes Stratégies (2018-2025)")
        table.add_column("Stratégie",     style="cyan",        width=28)
        table.add_column("Rendement/an",  style="bold green",  width=14)
        table.add_column("Sharpe",        style="bold",        width=8)
        table.add_column("Max DD",        style="red",         width=10)
        table.add_column("Win Rate",      style="yellow",      width=10)
        table.add_column("Profit Factor", style="yellow",      width=14)
        table.add_column("Trades",        style="dim",         width=8)

        for row in summary_rows:
            table.add_row(*row.values())

        console.print(table)

        console.print("\n[bold]📖 Lecture :[/bold]")
        console.print("  Sharpe > 1.0  = stratégie acceptable")
        console.print("  Sharpe > 1.5  = stratégie solide")
        console.print("  Max DD < -20% = risque élevé")
        console.print("  Profit Factor > 1.5 = edge statistique confirmé")


if __name__ == "__main__":
    run_backtest_pipeline()