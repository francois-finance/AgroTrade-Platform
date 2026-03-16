"""
Calculator : Risque portefeuille multi-commodités
Concepts   : Corrélations, diversification, VaR portefeuille agrégé
"""

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED

console = Console()


def compute_correlation_matrix(
    commodities: list = ["wheat", "corn", "soybean"],
    lookback_days: int = 252,
) -> pd.DataFrame:
    """
    Calcule la matrice de corrélation entre commodités.
    Essentiel pour comprendre la diversification réelle du portefeuille.
    """
    returns_dict = {}

    for c in commodities:
        path = DATA_RAW / f"{c}_futures.csv"
        if path.exists():
            df = pd.read_csv(path, index_col="date", parse_dates=True)
            returns_dict[c] = df["close"].pct_change().dropna().iloc[-lookback_days:]

    returns_df  = pd.DataFrame(returns_dict).dropna()
    corr_matrix = returns_df.corr()
    return corr_matrix, returns_df


def compute_portfolio_var(
    portfolio: dict,
    confidence: float = 0.99,
    horizon: int = 1,
    lookback_days: int = 252,
) -> dict:
    """
    VaR portefeuille en tenant compte des corrélations.

    VaR agrégé < Somme des VaR individuels grâce à la diversification.
    La différence = bénéfice de diversification.
    """
    commodities = list(portfolio.keys())
    corr_matrix, returns_df = compute_correlation_matrix(
        commodities, lookback_days
    )

    # Vecteur des positions en USD
    position_values = []
    for c in commodities:
        path = DATA_RAW / f"{c}_futures.csv"
        last_price = pd.read_csv(
            path, index_col="date"
        )["close"].dropna().iloc[-1]
        contracts = portfolio[c]["contracts"]
        direction = portfolio[c]["direction"]
        pos_val = direction * (float(last_price) / 100) * 5000 * contracts
        position_values.append(pos_val)

    w = np.array(position_values)
    total_abs = sum(abs(p) for p in position_values)

    # VaR marginal par asset (paramétrique)
    z = 2.326 if confidence == 0.99 else 1.645
    sigmas = returns_df.std().values * np.sqrt(horizon)

    # VaR portefeuille = sqrt(w' * Σ * w) * z
    cov_matrix = returns_df.cov().values * horizon
    portfolio_variance = w @ cov_matrix @ w
    portfolio_std = np.sqrt(max(portfolio_variance, 0))

    portfolio_var = abs(z * portfolio_std)

    # Somme des VaR individuels (sans diversification)
    individual_vars = [abs(z * s * p) for s, p in zip(sigmas, position_values)]
    sum_individual_var = sum(individual_vars)

    diversification_benefit = sum_individual_var - portfolio_var
    diversification_pct = (
        diversification_benefit / sum_individual_var * 100
        if sum_individual_var > 0 else 0
    )

    return {
        "portfolio_var":          round(portfolio_var, 0),
        "sum_individual_var":     round(sum_individual_var, 0),
        "diversification_benefit":round(diversification_benefit, 0),
        "diversification_pct":    round(diversification_pct, 1),
        "total_position_value":   round(total_abs, 0),
        "var_to_portfolio_pct":   round(portfolio_var / total_abs * 100, 2) if total_abs > 0 else 0,
        "correlation_matrix":     corr_matrix,
        "individual_vars":        dict(zip(commodities, [round(v, 0) for v in individual_vars])),
    }


def print_portfolio_risk(result: dict, portfolio: dict):
    """Affiche le rapport de risque portefeuille"""

    # Matrice de corrélation
    corr = result["correlation_matrix"]
    table = Table(title="📊 Matrice de Corrélation (252j)")
    table.add_column("",         style="cyan", width=12)
    for c in corr.columns:
        table.add_column(c.upper(), style="white", width=12)

    for idx, row in corr.iterrows():
        values = []
        for c in corr.columns:
            val = row[c]
            color = "green" if val > 0.7 else ("yellow" if val > 0.3 else "white")
            if idx == c:
                values.append("[bold]1.00[/bold]")
            else:
                values.append(f"[{color}]{val:.2f}[/{color}]")
        table.add_row(idx.upper(), *values)
    console.print(table)

    # VaR portefeuille
    table2 = Table(title="⚠️  VaR Portefeuille Agrégé (99%, 1j)")
    table2.add_column("Métrique",              style="cyan",        width=35)
    table2.add_column("Valeur",                style="bold yellow", width=20)

    table2.add_row("Valeur totale du portefeuille",
                   f"${result['total_position_value']:,.0f}")
    table2.add_row("Somme VaR individuels (sans diversif.)",
                   f"${result['sum_individual_var']:,.0f}")
    table2.add_row("VaR portefeuille (avec corrélations)",
                   f"[bold]${result['portfolio_var']:,.0f}[/bold]")
    table2.add_row("Bénéfice de diversification",
                   f"[green]${result['diversification_benefit']:,.0f} "
                   f"(-{result['diversification_pct']:.1f}%)[/green]")
    table2.add_row("VaR / Valeur portefeuille",
                   f"{result['var_to_portfolio_pct']:.2f}%")

    console.print(table2)

    # VaR par ligne
    table3 = Table(title="📋 VaR par Commodité")
    table3.add_column("Commodité",   style="cyan",   width=14)
    table3.add_column("Direction",   style="white",  width=10)
    table3.add_column("Contrats",    style="white",  width=10)
    table3.add_column("VaR 1j 99%",  style="yellow", width=16)

    for c, var in result["individual_vars"].items():
        direction = "🟢 LONG" if portfolio[c]["direction"] == 1 else "🔴 SHORT"
        table3.add_row(
            c.upper(),
            direction,
            str(portfolio[c]["contracts"]),
            f"${var:,.0f}",
        )
    console.print(table3)