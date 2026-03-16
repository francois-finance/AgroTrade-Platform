"""
Calculator : Value at Risk (VaR) & Conditional VaR (CVaR / Expected Shortfall)
Méthodes   : 1) Historique  2) Paramétrique (normal)  3) Monte Carlo
Horizons   : 1 jour, 5 jours (1 semaine), 10 jours (2 semaines)
Niveaux    : 95%, 99%, 99.5%

Le VaR répond à : "Quelle est la perte maximale sur X jours avec Y% de confiance ?"
Le CVaR répond à : "Si on dépasse le VaR, quelle est la perte moyenne ?"
"""

import pandas as pd
import numpy as np
from scipy import stats
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED

console = Console()

# Taille d'un contrat CBOT en boisseaux
CONTRACT_SIZE = {
    "wheat":   5000,
    "corn":    5000,
    "soybean": 5000,
    "soyoil":  60000,  # livres
    "soymeal": 100,    # tonnes courtes
}


def load_returns(commodity: str, lookback_days: int = 756) -> pd.Series:
    """
    Charge les returns journaliers d'une commodité.
    756 jours = 3 ans de données historiques (standard bancaire).
    """
    path = DATA_RAW / f"{commodity}_futures.csv"
    if not path.exists():
        raise FileNotFoundError(f"Données manquantes : {path}")

    df = pd.read_csv(path, index_col="date", parse_dates=True)
    returns = df["close"].pct_change().dropna()
    return returns.iloc[-lookback_days:]


def compute_historical_var(
    returns: pd.Series,
    position_value: float,
    confidence_levels: list = [0.95, 0.99, 0.995],
    horizons: list = [1, 5, 10],
) -> dict:
    """
    VaR Historique : utilise la distribution réelle des returns passés.
    Avantage : capture les fat tails et la non-normalité des commodités.
    """
    results = {}

    for conf in confidence_levels:
        quantile = 1 - conf
        results[conf] = {}

        for h in horizons:
            # Scaling par sqrt(T) pour horizons multi-jours
            scaled_returns = returns * np.sqrt(h)
            var_pct  = abs(np.percentile(scaled_returns, quantile * 100))
            var_usd  = var_pct * position_value

            # CVaR = moyenne des pertes au-delà du VaR
            tail_returns = scaled_returns[scaled_returns < -var_pct]
            cvar_pct = abs(tail_returns.mean()) if len(tail_returns) > 0 else var_pct
            cvar_usd = cvar_pct * position_value

            results[conf][h] = {
                "var_pct":  round(var_pct * 100, 3),
                "var_usd":  round(var_usd, 0),
                "cvar_pct": round(cvar_pct * 100, 3),
                "cvar_usd": round(cvar_usd, 0),
            }

    return results


def compute_parametric_var(
    returns: pd.Series,
    position_value: float,
    confidence_levels: list = [0.95, 0.99, 0.995],
    horizons: list = [1, 5, 10],
) -> dict:
    """
    VaR Paramétrique : assume une distribution normale.
    Plus simple mais sous-estime les queues épaisses des commodités.
    Utile comme référence et pour les comparaisons réglementaires.
    """
    mu    = returns.mean()
    sigma = returns.std()
    results = {}

    for conf in confidence_levels:
        z_score = stats.norm.ppf(1 - conf)
        results[conf] = {}

        for h in horizons:
            var_pct  = abs(z_score * sigma * np.sqrt(h) - mu * h)
            var_usd  = var_pct * position_value

            # CVaR paramétrique
            pdf_z   = stats.norm.pdf(z_score)
            cvar_pct = abs((sigma * pdf_z / (1 - conf)) * np.sqrt(h))
            cvar_usd = cvar_pct * position_value

            results[conf][h] = {
                "var_pct":  round(var_pct * 100, 3),
                "var_usd":  round(var_usd, 0),
                "cvar_pct": round(cvar_pct * 100, 3),
                "cvar_usd": round(cvar_usd, 0),
            }

    return results


def compute_monte_carlo_var(
    returns: pd.Series,
    position_value: float,
    n_simulations: int = 10000,
    horizon: int = 10,
    confidence: float = 0.99,
) -> dict:
    """
    VaR Monte Carlo : simule N scénarios de prix sur l'horizon donné.
    Le plus robuste — capture les non-linéarités et les distributions complexes.
    """
    mu    = returns.mean()
    sigma = returns.std()

    # Simulation de marches aléatoires
    np.random.seed(42)
    simulated_returns = np.random.normal(mu, sigma, (n_simulations, horizon))
    cumulative_returns = simulated_returns.sum(axis=1)

    var_pct  = abs(np.percentile(cumulative_returns, (1 - confidence) * 100))
    var_usd  = var_pct * position_value

    tail = cumulative_returns[cumulative_returns < -var_pct]
    cvar_pct = abs(tail.mean()) if len(tail) > 0 else var_pct
    cvar_usd = cvar_pct * position_value

    return {
        "method":       "Monte Carlo",
        "n_simulations":n_simulations,
        "horizon":      horizon,
        "confidence":   confidence,
        "var_pct":      round(var_pct * 100, 3),
        "var_usd":      round(var_usd, 0),
        "cvar_pct":     round(cvar_pct * 100, 3),
        "cvar_usd":     round(cvar_usd, 0),
        "simulated_returns": cumulative_returns,
    }


def run_var_analysis(
    portfolio: dict,
    save: bool = True,
) -> dict:
    """
    Lance l'analyse VaR complète sur un portefeuille.

    Args:
        portfolio: dict {commodity: {"contracts": int, "direction": 1/-1}}
        Exemple:   {"wheat": {"contracts": 10, "direction": 1},
                    "soybean": {"contracts": 5, "direction": -1}}
    """
    console.print("[cyan]⚠️  Calcul VaR & CVaR du portefeuille...[/cyan]")

    results = {}

    for commodity, pos in portfolio.items():
        returns = load_returns(commodity)
        last_price = pd.read_csv(
            DATA_RAW / f"{commodity}_futures.csv",
            index_col="date"
        )["close"].dropna().iloc[-1]

        # Valeur de la position en USD
        contract_size = CONTRACT_SIZE.get(commodity, 5000)
        position_value = abs(
            (last_price / 100) * contract_size * pos["contracts"]
        )

        hist_var  = compute_historical_var(returns, position_value)
        param_var = compute_parametric_var(returns, position_value)
        mc_var    = compute_monte_carlo_var(returns, position_value)

        results[commodity] = {
            "position":       pos,
            "last_price":     round(float(last_price), 2),
            "position_value": round(position_value, 0),
            "historical_var": hist_var,
            "parametric_var": param_var,
            "monte_carlo_var":mc_var,
            "returns":        returns,
        }

        _print_var_table(commodity, position_value, hist_var, param_var, mc_var)

    if save:
        rows = []
        for c, r in results.items():
            hv = r["historical_var"][0.99][1]
            rows.append({
                "commodity":      c,
                "contracts":      r["position"]["contracts"],
                "direction":      r["position"]["direction"],
                "position_value": r["position_value"],
                "var_1d_99_hist": hv["var_usd"],
                "cvar_1d_99_hist":hv["cvar_usd"],
                "var_10d_99_mc":  r["monte_carlo_var"]["var_usd"],
            })
        pd.DataFrame(rows).to_csv(
            DATA_PROCESSED / "var_analysis.csv", index=False
        )
        console.print("[blue]💾 Sauvegardé : var_analysis.csv[/blue]")

    return results


def _print_var_table(commodity, position_value, hist_var, param_var, mc_var):
    """Affiche le tableau VaR pour une commodité"""
    table = Table(
        title=f"⚠️  VaR Analysis — {commodity.upper()} "
              f"(Position: ${position_value:,.0f})",
        show_lines=True
    )
    table.add_column("Méthode",        style="cyan",        width=16)
    table.add_column("Confiance",      style="white",       width=10)
    table.add_column("VaR 1j",         style="yellow",      width=14)
    table.add_column("VaR 5j",         style="yellow",      width=14)
    table.add_column("VaR 10j",        style="bold yellow", width=14)
    table.add_column("CVaR 1j",        style="red",         width=14)

    for conf, label in [(0.95, "95%"), (0.99, "99%"), (0.995, "99.5%")]:
        h = hist_var[conf]
        p = param_var[conf]
        table.add_row(
            "Historique",  label,
            f"${h[1]['var_usd']:,.0f}",
            f"${h[5]['var_usd']:,.0f}",
            f"${h[10]['var_usd']:,.0f}",
            f"${h[1]['cvar_usd']:,.0f}",
        )
        table.add_row(
            "Paramétrique", label,
            f"${p[1]['var_usd']:,.0f}",
            f"${p[5]['var_usd']:,.0f}",
            f"${p[10]['var_usd']:,.0f}",
            f"${p[1]['cvar_usd']:,.0f}",
        )

    # Monte Carlo (99%, 10j)
    table.add_row(
        "[bold]Monte Carlo[/bold]", "99%",
        "—", "—",
        f"[bold]${mc_var['var_usd']:,.0f}[/bold]",
        f"[bold]${mc_var['cvar_usd']:,.0f}[/bold]",
    )
    console.print(table)