"""
Stress Tester : Simule l'impact de scénarios extrêmes sur le portefeuille.

Scénarios historiques : Crises réelles (2008, 2012, Ukraine 2022...)
Scénarios hypothétiques : Événements plausibles futurs

C'est ce que les risk managers regardent tous les matins.
"""

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED

console = Console()

# ── Scénarios de stress ────────────────────────────────────────────────────────
STRESS_SCENARIOS = {

    # ── Historiques ────────────────────────────────────────────────────────────
    "ukraine_invasion_2022": {
        "type":        "historical",
        "date":        "2022-02-24",
        "description": "Invasion russe de l'Ukraine — spike prix céréales",
        "shocks": {
            "wheat":   +0.40,   # +40% en quelques semaines
            "corn":    +0.20,
            "soybean": +0.15,
        },
        "freight_shock": +0.35,
        "duration_days": 30,
    },

    "covid_crash_2020": {
        "type":        "historical",
        "date":        "2020-03-15",
        "description": "Crash COVID — disruption supply chains mondiales",
        "shocks": {
            "wheat":   +0.08,
            "corn":    -0.15,
            "soybean": -0.12,
        },
        "freight_shock": -0.40,   # Effondrement du BDI
        "duration_days": 20,
    },

    "us_drought_2012": {
        "type":        "historical",
        "date":        "2012-06-01",
        "description": "Grande sécheresse US Midwest — pires récoltes depuis 1988",
        "shocks": {
            "wheat":   +0.35,
            "corn":    +0.60,   # +60% — pic historique
            "soybean": +0.45,
        },
        "freight_shock": +0.20,
        "duration_days": 90,
    },

    "china_pork_crisis_2019": {
        "type":        "historical",
        "date":        "2019-09-01",
        "description": "Fièvre porcine africaine Chine — effondrement demande soja",
        "shocks": {
            "wheat":   -0.05,
            "corn":    -0.08,
            "soybean": -0.18,   # Chine = 60% des imports mondiaux soja
        },
        "freight_shock": -0.15,
        "duration_days": 60,
    },

    "black_sea_blockade_2022": {
        "type":        "historical",
        "date":        "2022-04-01",
        "description": "Blocage ports Mer Noire — Ukraine/Russie = 30% exports mondiaux blé",
        "shocks": {
            "wheat":   +0.55,   # Record historique
            "corn":    +0.25,
            "soybean": +0.10,
        },
        "freight_shock": +0.60,
        "duration_days": 45,
    },

    # ── Hypothétiques ──────────────────────────────────────────────────────────
    "el_nino_severe_2025": {
        "type":        "hypothetical",
        "date":        "2025-06-01",
        "description": "El Niño sévère — sécheresse simultanée Brésil + Australie",
        "shocks": {
            "wheat":   +0.25,
            "corn":    +0.20,
            "soybean": +0.35,   # Brésil = 40% exports mondiaux
        },
        "freight_shock": +0.15,
        "duration_days": 120,
    },

    "us_china_trade_war_escalation": {
        "type":        "hypothetical",
        "date":        "2025-01-01",
        "description": "Escalade guerre commerciale US-Chine — tarifs soja 25%",
        "shocks": {
            "wheat":   -0.05,
            "corn":    -0.10,
            "soybean": -0.25,   # Impact direct sur soja US
        },
        "freight_shock": -0.20,
        "duration_days": 180,
    },

    "suez_canal_blockage": {
        "type":        "hypothetical",
        "date":        "2025-01-01",
        "description": "Blocage prolongé Canal de Suez (60 jours)",
        "shocks": {
            "wheat":   +0.08,
            "corn":    +0.05,
            "soybean": +0.06,
        },
        "freight_shock": +0.80,   # Impact massif sur le fret
        "duration_days": 60,
    },

    "russia_export_ban": {
        "type":        "hypothetical",
        "date":        "2025-01-01",
        "description": "Interdiction d'exportation de blé par la Russie",
        "shocks": {
            "wheat":   +0.30,   # Russie = 20% exports mondiaux
            "corn":    +0.05,
            "soybean": +0.02,
        },
        "freight_shock": +0.10,
        "duration_days": 90,
    },
}


def run_stress_test(
    portfolio: dict,
    scenario_key: str,
) -> dict:
    """
    Calcule l'impact d'un scénario de stress sur le portefeuille.

    Args:
        portfolio: {"wheat": {"contracts": 10, "direction": 1, "entry_price": 611}, ...}
        scenario_key: clé du scénario dans STRESS_SCENARIOS
    """
    scenario = STRESS_SCENARIOS[scenario_key]
    shocks   = scenario["shocks"]

    total_pnl = 0
    pnl_by_commodity = {}

    for commodity, pos in portfolio.items():
        shock_pct = shocks.get(commodity, 0)

        # Prix actuel
        path = DATA_RAW / f"{commodity}_futures.csv"
        if path.exists():
            current_price = float(
                pd.read_csv(path, index_col="date")["close"].dropna().iloc[-1]
            )
        else:
            current_price = pos.get("entry_price", 500)

        # Variation de prix en $ par contrat
        price_change   = current_price * shock_pct
        pnl_per_contract = (price_change / 100) * 5000 * pos["direction"]
        total_pnl_commodity = pnl_per_contract * pos["contracts"]

        pnl_by_commodity[commodity] = {
            "shock_pct":        round(shock_pct * 100, 1),
            "price_change":     round(price_change, 2),
            "current_price":    round(current_price, 2),
            "stressed_price":   round(current_price * (1 + shock_pct), 2),
            "pnl_per_contract": round(pnl_per_contract, 0),
            "total_pnl":        round(total_pnl_commodity, 0),
        }
        total_pnl += total_pnl_commodity

    return {
        "scenario_key":       scenario_key,
        "scenario":           scenario,
        "pnl_by_commodity":   pnl_by_commodity,
        "total_pnl":          round(total_pnl, 0),
        "scenario_type":      scenario["type"],
    }


def run_all_stress_tests(portfolio: dict, save: bool = True) -> pd.DataFrame:
    """Lance tous les scénarios de stress et retourne un tableau comparatif"""
    console.print("\n[cyan]🔥 Lancement des stress tests...[/cyan]\n")

    rows = []
    details = {}

    for scenario_key in STRESS_SCENARIOS:
        result = run_stress_test(portfolio, scenario_key)
        details[scenario_key] = result
        rows.append({
            "scenario":    scenario_key,
            "type":        result["scenario_type"],
            "description": result["scenario"]["description"],
            "total_pnl":   result["total_pnl"],
            "duration":    result["scenario"]["duration_days"],
        })

    df = pd.DataFrame(rows).sort_values("total_pnl")

    # Affichage
    table = Table(
        title="🔥 Stress Test Results — Impact Portefeuille",
        show_lines=True
    )
    table.add_column("Scénario",       style="cyan",   width=35)
    table.add_column("Type",           style="dim",    width=12)
    table.add_column("P&L Impact",     style="bold",   width=16)
    table.add_column("Durée",          style="white",  width=10)
    table.add_column("Description",    style="dim",    width=45)

    for _, row in df.iterrows():
        pnl  = row["total_pnl"]
        color = "red" if pnl < -5000 else ("yellow" if pnl < 0 else "green")
        pnl_str = f"[{color}]${pnl:+,.0f}[/{color}]"
        table.add_row(
            row["scenario"].replace("_", " ").title(),
            row["type"],
            pnl_str,
            f"{row['duration']}j",
            row["description"][:42] + "...",
        )
    console.print(table)

    # Pire scénario
    worst = df.iloc[0]
    worst_detail = details[worst["scenario"]]
    console.print(Panel(
        f"[bold red]Pire scénario : {worst['scenario'].replace('_',' ').title()}[/bold red]\n"
        f"P&L Impact : [bold red]${worst['total_pnl']:+,.0f}[/bold red]\n"
        f"Description : {worst['description']}\n\n" +
        "\n".join([
            f"  {c.upper()}: shock {v['shock_pct']:+.0f}% → "
            f"${v['current_price']:.0f} → ${v['stressed_price']:.0f} | "
            f"P&L: ${v['total_pnl']:+,.0f}"
            for c, v in worst_detail["pnl_by_commodity"].items()
        ]),
        title="💀 Worst Case Scenario",
        border_style="red"
    ))

    if save:
        df.to_csv(DATA_PROCESSED / "stress_test_results.csv", index=False)
        console.print("[blue]💾 Sauvegardé : stress_test_results.csv[/blue]")

    return df, details