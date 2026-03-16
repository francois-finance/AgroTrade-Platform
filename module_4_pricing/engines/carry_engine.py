"""
Engine : Coût de portage (Carry) & Courbe Forward
Définition : Le carry = coût de détenir du grain dans le temps
             Carry = Stockage + Intérêts + Assurance - Convenience yield
Utilité    : Explique la structure de la courbe forward (contango vs backwardation)
             Contango    = marché bien approvisionné, stocks abondants
             Backwardation = marché tendu, stocks faibles, prime sur le spot
"""

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_PROCESSED

console = Console()

# Coûts de stockage céréalier (cents/boisseau/mois)
STORAGE_COSTS = {
    "wheat":   {"us_commercial": 0.055, "farm_storage": 0.030, "europe_port": 2.5},
    "corn":    {"us_commercial": 0.050, "farm_storage": 0.028, "europe_port": 2.3},
    "soybean": {"us_commercial": 0.060, "farm_storage": 0.032, "europe_port": 2.8},
}

# Contrats futures disponibles (mois d'expiration CBOT)
FUTURES_EXPIRY_MONTHS = {
    "wheat":   [3, 5, 7, 9, 12],     # Mar, Mai, Jul, Sep, Déc
    "corn":    [3, 5, 7, 9, 12],
    "soybean": [1, 3, 5, 7, 8, 9, 11],
}


def compute_full_carry(
    commodity: str,
    spot_price: float,
    months_forward: int,
    interest_rate: float = 0.055,      # Taux d'intérêt annuel (Fed funds ~5.5%)
    storage_type: str = "us_commercial",
    convenience_yield: float = 0.0,
) -> dict:
    """
    Calcule le prix forward théorique basé sur le coût de portage complet.

    Prix forward théorique = Spot × e^((r + s - c) × T)
    Où : r = taux d'intérêt
         s = taux de stockage
         c = convenience yield
         T = temps en années
    """
    T = months_forward / 12.0

    # Coûts mensuels
    storage_monthly = STORAGE_COSTS[commodity].get(storage_type, 0.055)
    storage_annual_rate = (storage_monthly * 12) / spot_price

    # Taux de carry total
    carry_rate = interest_rate + storage_annual_rate - convenience_yield

    # Prix forward théorique (formule cost-of-carry)
    theoretical_forward = spot_price * np.exp(carry_rate * T)

    # Coût de portage absolu
    carry_cost_total = theoretical_forward - spot_price
    carry_cost_monthly = carry_cost_total / months_forward if months_forward > 0 else 0

    return {
        "commodity":              commodity,
        "spot_price":             round(spot_price, 2),
        "months_forward":         months_forward,
        "interest_rate_pct":      round(interest_rate * 100, 2),
        "storage_cost_monthly":   round(storage_monthly, 4),
        "storage_annual_rate_pct":round(storage_annual_rate * 100, 2),
        "convenience_yield_pct":  round(convenience_yield * 100, 2),
        "total_carry_rate_pct":   round(carry_rate * 100, 2),
        "theoretical_forward":    round(theoretical_forward, 2),
        "carry_cost_total":       round(carry_cost_total, 2),
        "carry_cost_per_month":   round(carry_cost_monthly, 2),
    }


def build_forward_curve(
    commodity: str,
    spot_price: float,
    interest_rate: float = 0.055,
    save: bool = True,
) -> pd.DataFrame:
    """
    Construit la courbe forward théorique complète sur 12 mois.
    Compare avec les prix futures réels pour identifier les anomalies.
    """
    console.print(f"[cyan]📈 Construction courbe forward : {commodity}...[/cyan]")

    rows = []
    for months in range(1, 13):
        carry = compute_full_carry(
            commodity=commodity,
            spot_price=spot_price,
            months_forward=months,
            interest_rate=interest_rate,
        )
        rows.append({
            "months_forward":      months,
            "theoretical_forward": carry["theoretical_forward"],
            "carry_cost_total":    carry["carry_cost_total"],
            "carry_per_month":     carry["carry_cost_per_month"],
        })

    df = pd.DataFrame(rows)
    df["commodity"]  = commodity
    df["spot_price"] = spot_price

    if save:
        path = DATA_PROCESSED / f"{commodity}_forward_curve.csv"
        df.to_csv(path, index=False)
        console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

    return df


def analyze_market_structure(
    commodity: str,
    spot_price: float,
    m3_price: float,    # Prix du contrat à 3 mois
    m6_price: float,    # Prix du contrat à 6 mois
) -> dict:
    """
    Analyse la structure de marché : contango vs backwardation.
    Compare les spreads calendar avec le carry théorique.
    """
    # Carry théorique sur 3 mois
    carry_3m = compute_full_carry(commodity, spot_price, 3)
    carry_6m = compute_full_carry(commodity, spot_price, 6)

    # Spreads observés
    spread_m1_m3 = m3_price - spot_price
    spread_m1_m6 = m6_price - spot_price

    # Spreads théoriques (full carry)
    theoretical_3m = carry_3m["carry_cost_total"]
    theoretical_6m = carry_6m["carry_cost_total"]

    # Pourcentage du full carry réalisé
    pct_carry_3m = (spread_m1_m3 / theoretical_3m * 100) if theoretical_3m != 0 else 0
    pct_carry_6m = (spread_m1_m6 / theoretical_6m * 100) if theoretical_6m != 0 else 0

    # Structure de marché
    if spread_m1_m3 > theoretical_3m * 0.80:
        structure = "FULL CARRY 🟡 — Stocks abondants, pas de prime sur le spot"
    elif spread_m1_m3 > 0:
        structure = "CONTANGO PARTIEL 🟠 — Marché bien approvisionné"
    elif spread_m1_m3 > -theoretical_3m * 0.30:
        structure = "QUASI FLAT ⚪ — Marché équilibré"
    else:
        structure = "BACKWARDATION 🟢 — Marché tendu, prime sur le spot !"

    return {
        "commodity":         commodity,
        "spot_price":        spot_price,
        "m3_price":          m3_price,
        "m6_price":          m6_price,
        "spread_m1_m3":      round(spread_m1_m3, 2),
        "spread_m1_m6":      round(spread_m1_m6, 2),
        "theoretical_3m":    round(theoretical_3m, 2),
        "theoretical_6m":    round(theoretical_6m, 2),
        "pct_carry_3m":      round(pct_carry_3m, 1),
        "pct_carry_6m":      round(pct_carry_6m, 1),
        "market_structure":  structure,
    }


def run_carry_analysis(save: bool = True) -> dict:
    """Lance l'analyse de carry et de structure de marché"""
    console.print("[cyan]📉 Analyse courbe forward & carry...[/cyan]")

    results = {}
    # Prix de référence actuels (chargés depuis data/raw si disponibles)
    reference_prices = {
        "wheat":   {"spot": 611, "m3": 618, "m6": 624},
        "corn":    {"spot": 447, "m3": 452, "m6": 458},
        "soybean": {"spot": 1185,"m3": 1195,"m6": 1202},
    }

    for commodity, prices in reference_prices.items():
        # Essaie de charger le vrai prix spot
        path = DATA_PROCESSED / f"{commodity}_technical.csv"
        if path.exists():
            df = pd.read_csv(path, index_col="date", parse_dates=True)
            prices["spot"] = float(df["close"].dropna().iloc[-1])

        curve = build_forward_curve(commodity, prices["spot"], save=save)
        structure = analyze_market_structure(
            commodity, prices["spot"], prices["m3"], prices["m6"]
        )
        results[commodity] = {"curve": curve, "structure": structure}

        # Affichage structure
        s = structure
        table = Table(title=f"📉 Structure de marché — {commodity.upper()}")
        table.add_column("Métrique",           style="cyan",   width=30)
        table.add_column("Valeur",             style="yellow", width=20)

        table.add_row("Prix Spot",             f"{s['spot_price']:.1f}c/bu")
        table.add_row("Prix M+3",              f"{s['m3_price']:.1f}c/bu")
        table.add_row("Prix M+6",              f"{s['m6_price']:.1f}c/bu")
        table.add_row("Spread M1-M3 observé",  f"{s['spread_m1_m3']:+.1f}c")
        table.add_row("Spread M1-M3 théorique",f"{s['theoretical_3m']:+.1f}c (full carry)")
        table.add_row("% du full carry réalisé",f"{s['pct_carry_3m']:.1f}%")
        table.add_row("Structure",             s["market_structure"])
        console.print(table)

    return results