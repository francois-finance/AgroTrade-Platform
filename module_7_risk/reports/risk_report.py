"""
Risk Report : Rapport de risque quotidien complet
Agrège VaR + Stress Tests + Positions en un rapport exécutif
"""

import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_PROCESSED

console = Console()


def generate_risk_report(
    portfolio: dict,
    var_results: dict,
    stress_df: pd.DataFrame,
    portfolio_risk: dict,
):
    """Génère et affiche le rapport de risque quotidien complet"""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Header ────────────────────────────────────────────────────────────
    console.print(Panel(
        f"[bold white]AgroTrade Platform — Daily Risk Report[/bold white]\n"
        f"Généré le : {timestamp}\n"
        f"Portefeuille : {len(portfolio)} positions | "
        f"Valeur totale : ${portfolio_risk['total_position_value']:,.0f}",
        title="📋 RISK REPORT",
        border_style="magenta"
    ))

    # ── Risk Summary ──────────────────────────────────────────────────────
    var_1d_99 = portfolio_risk.get("portfolio_var", 0)
    worst_stress = stress_df["total_pnl"].min()
    best_stress  = stress_df["total_pnl"].max()

    summary_table = Table(title="🎯 Risk Summary", show_header=False)
    summary_table.add_column("Métrique",   style="cyan",   width=35)
    summary_table.add_column("Valeur",     style="bold",   width=20)
    summary_table.add_column("Statut",     style="bold",   width=15)

    def risk_status(var, threshold_warn, threshold_danger):
        if var > threshold_danger:
            return "[red]🔴 DANGER[/red]"
        elif var > threshold_warn:
            return "[yellow]🟡 ATTENTION[/yellow]"
        return "[green]🟢 OK[/green]"

    portfolio_value = portfolio_risk["total_position_value"]
    var_pct = (var_1d_99 / portfolio_value * 100) if portfolio_value > 0 else 0

    summary_table.add_row(
        "VaR 1j 99% (portefeuille)",
        f"${var_1d_99:,.0f} ({var_pct:.2f}%)",
        risk_status(var_pct, 2, 5)
    )
    summary_table.add_row(
        "Pire stress test",
        f"${worst_stress:+,.0f}",
        risk_status(abs(worst_stress) / portfolio_value * 100, 10, 25)
        if portfolio_value > 0 else "—"
    )
    summary_table.add_row(
        "Meilleur stress test",
        f"${best_stress:+,.0f}",
        "[dim]—[/dim]"
    )
    summary_table.add_row(
        "Bénéfice diversification",
        f"${portfolio_risk['diversification_benefit']:,.0f} "
        f"(-{portfolio_risk['diversification_pct']:.1f}%)",
        "[green]🟢 Actif[/green]"
    )
    console.print(summary_table)

    # ── Top 3 risques à surveiller ────────────────────────────────────────
    top_risks = stress_df.nsmallest(3, "total_pnl")
    console.print(Panel(
        "\n".join([
            f"  {i+1}. [bold]{row['scenario'].replace('_',' ').title()}[/bold] — "
            f"Impact: [red]${row['total_pnl']:+,.0f}[/red] "
            f"({row['type']})"
            for i, (_, row) in enumerate(top_risks.iterrows())
        ]),
        title="🚨 Top 3 Scénarios de Risque",
        border_style="red"
    ))

    # ── Recommandations ───────────────────────────────────────────────────
    recommendations = []
    if var_pct > 3:
        recommendations.append("⚠️  VaR élevé — réduire la taille des positions")
    if portfolio_risk["diversification_pct"] < 5:
        recommendations.append("⚠️  Faible diversification — positions trop corrélées")
    if abs(worst_stress) > portfolio_value * 0.20:
        recommendations.append("⚠️  Exposition stress élevée — envisager des hedges optionnels")
    if not recommendations:
        recommendations.append("✅ Profil de risque dans les limites acceptables")

    console.print(Panel(
        "\n".join(f"  {r}" for r in recommendations),
        title="💡 Recommandations Risk Management",
        border_style="yellow"
    ))