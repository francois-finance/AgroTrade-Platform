"""
AgroTrade Platform — Module 7 : Risk Dashboard Pipeline
"""

from rich.console import Console
from rich.table import Table
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_7_risk.calculators.var_calculator  import run_var_analysis
from module_7_risk.calculators.portfolio_risk  import compute_portfolio_var, print_portfolio_risk
from module_7_risk.stress.stress_tester        import run_all_stress_tests
from module_7_risk.reports.risk_report         import generate_risk_report

console = Console()

# ── Portefeuille de démonstration ──────────────────────────────────────────────
# Simule un desk trading agri typique
DEMO_PORTFOLIO = {
    "wheat":   {"contracts": 10, "direction":  1, "entry_price": 600},  # Long 10 contrats blé
    "corn":    {"contracts":  8, "direction": -1, "entry_price": 450},  # Short 8 contrats maïs
    "soybean": {"contracts":  5, "direction":  1, "entry_price": 1180}, # Long 5 contrats soja
}


def run_risk_pipeline():
    console.print(
        "\n[bold magenta]⚠️  AgroTrade — Module 7 : Risk Dashboard[/bold magenta]\n"
    )
    status = {}

    # 1. VaR par commodité
    from rich.rule import Rule
    console.print(Rule("[bold cyan]1/4 — VaR & CVaR par Position[/bold cyan]"))
    try:
        var_results = run_var_analysis(DEMO_PORTFOLIO, save=True)
        status["VaR Analysis"] = ("✅", len(var_results), "positions analysées")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["VaR Analysis"] = ("❌", 0, str(e))
        var_results = {}

    # 2. Risque portefeuille agrégé
    console.print(Rule("[bold cyan]2/4 — Risque Portefeuille Agrégé[/bold cyan]"))
    try:
        port_risk = compute_portfolio_var(DEMO_PORTFOLIO)
        print_portfolio_risk(port_risk, DEMO_PORTFOLIO)
        status["Portfolio Risk"] = ("✅", 1, "matrice corrélation calculée")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["Portfolio Risk"] = ("❌", 0, str(e))
        port_risk = {"portfolio_var": 0, "total_position_value": 0,
                     "diversification_benefit": 0, "diversification_pct": 0,
                     "individual_vars": {}}

    # 3. Stress Tests
    console.print(Rule("[bold cyan]3/4 — Stress Tests[/bold cyan]"))
    try:
        stress_df, stress_details = run_all_stress_tests(DEMO_PORTFOLIO, save=True)
        status["Stress Tests"] = ("✅", len(stress_df), "scénarios testés")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        import traceback; traceback.print_exc()
        status["Stress Tests"] = ("❌", 0, str(e))
        import pandas as pd
        stress_df = pd.DataFrame({"total_pnl": [0]})

    # 4. Rapport de risque final
    console.print(Rule("[bold cyan]4/4 — Daily Risk Report[/bold cyan]"))
    try:
        generate_risk_report(DEMO_PORTFOLIO, var_results, stress_df, port_risk)
        status["Risk Report"] = ("✅", 1, "rapport généré")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["Risk Report"] = ("❌", 0, str(e))

    # Rapport d'état
    console.print()
    table = Table(title="📊 Module 7 — Rapport d'État")
    table.add_column("Composant", style="cyan")
    table.add_column("Status",    style="green")
    table.add_column("Volume",    style="yellow")
    table.add_column("Détail",    style="white")
    for comp, (st, vol, detail) in status.items():
        table.add_row(comp, st, str(vol), detail)
    console.print(table)


if __name__ == "__main__":
    run_risk_pipeline()