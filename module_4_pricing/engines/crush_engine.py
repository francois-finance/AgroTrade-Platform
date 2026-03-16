"""
Engine : Soybean Crush Margin
Définition : La marge de crushing = valeur des produits obtenus - coût du soja brut
Formule    : Crush = (Huile soja × 11 lbs) + (Tourteau × 44 lbs) - Prix Soja
             → 1 boisseau de soja (60 lbs) → 11 lbs d'huile + 44 lbs de tourteau + 5 lbs pertes

C'est l'indicateur clé pour les crushers industriels (Bunge, Cargill, ADM, Louis Dreyfus).
Un crush élevé → les usines tournent à plein régime → forte demande de soja physique.
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

# Rendements de crushing (par boisseau de soja de 60 lbs)
CRUSH_YIELDS = {
    "soyoil_lbs_per_bushel":   11.0,   # livres d'huile
    "soymeal_lbs_per_bushel":  44.0,   # livres de tourteau
    "waste_lbs":                5.0,   # pertes process
}

# Coûts de crushing (variables selon l'usine)
CRUSHING_COSTS = {
    "us_midwest":   0.30,   # $/boisseau — coût opératoire typique US
    "brazil":       0.28,
    "argentina":    0.25,
    "europe":       0.35,
}


def load_prices() -> dict:
    """Charge les derniers prix des 3 composantes du crush"""
    prices = {}
    for commodity in ["soybean", "soyoil", "soymeal"]:
        path = DATA_RAW / f"{commodity}_futures.csv"
        if path.exists():
            df = pd.read_csv(path, index_col="date", parse_dates=True)
            prices[commodity] = float(df["close"].iloc[-1])
        else:
            # Fallback prix de référence
            defaults = {"soybean": 1150.0, "soyoil": 45.0, "soymeal": 350.0}
            prices[commodity] = defaults[commodity]
            console.print(f"[yellow]⚠ Prix {commodity} manquant — fallback {defaults[commodity]}[/yellow]")
    return prices


def compute_crush_margin(
    soybean_price: float,   # cents/boisseau
    soyoil_price: float,    # cents/livre
    soymeal_price: float,   # $/tonne courte
    location: str = "us_midwest",
    processing_cost: float = None,
) -> dict:
    """
    Calcule la marge de crushing brute et nette.

    Conversions importantes :
    - Soja    : cents/boisseau → 1 boisseau = 27.216 kg
    - Huile   : cents/livre    → 1 livre = 0.4536 kg
    - Tourteau: $/tonne courte → 1 tonne courte = 907.18 kg
    """
    if processing_cost is None:
        processing_cost = CRUSHING_COSTS.get(location, 0.30)

    yields = CRUSH_YIELDS

    # Valeur des produits obtenus (par boisseau de soja)
    # Huile : (cents/livre × lbs/bushel) / 100 = $ par boisseau
    oil_value_per_bushel = (soyoil_price * yields["soyoil_lbs_per_bushel"]) / 100

    # Tourteau : ($/tonne courte / 2000 lbs par tonne courte) × lbs/bushel
    meal_value_per_bushel = (soymeal_price / 2000) * yields["soymeal_lbs_per_bushel"]

    gross_product_value = oil_value_per_bushel + meal_value_per_bushel

    # Coût du soja (cents → dollars)
    soybean_cost = soybean_price / 100

    # Marges
    gross_crush = gross_product_value - soybean_cost          # Marge brute $/bu
    net_crush   = gross_crush - processing_cost                # Marge nette $/bu

    # Conversion en $/tonne métrique pour référence internationale
    bushels_per_mt = 36.744  # 1 tonne métrique de soja = 36.744 boisseaux
    gross_crush_mt = gross_crush * bushels_per_mt
    net_crush_mt   = net_crush   * bushels_per_mt

    # Signal
    if net_crush > 1.50:
        signal = "🟢 EXCELLENT — Crushers très profitables, forte demande soja"
        crush_signal = 1
    elif net_crush > 0.80:
        signal = "🟡 BON — Marges correctes, activité normale"
        crush_signal = 0
    elif net_crush > 0.20:
        signal = "🟠 FAIBLE — Marges serrées, ralentissement possible"
        crush_signal = -1
    else:
        signal = "🔴 NÉGATIF — Crushers sous pression, réduction d'activité"
        crush_signal = -1

    return {
        "soybean_price_cents_bu":   round(soybean_price, 2),
        "soyoil_price_cents_lb":    round(soyoil_price, 2),
        "soymeal_price_usd_st":     round(soymeal_price, 2),
        "oil_value_per_bu":         round(oil_value_per_bushel, 3),
        "meal_value_per_bu":        round(meal_value_per_bushel, 3),
        "gross_product_value":      round(gross_product_value, 3),
        "soybean_cost_per_bu":      round(soybean_cost, 3),
        "processing_cost_per_bu":   round(processing_cost, 3),
        "gross_crush_usd_bu":       round(gross_crush, 3),
        "net_crush_usd_bu":         round(net_crush, 3),
        "gross_crush_usd_mt":       round(gross_crush_mt, 2),
        "net_crush_usd_mt":         round(net_crush_mt, 2),
        "location":                 location,
        "signal":                   signal,
        "crush_signal":             crush_signal,
    }


def compute_historical_crush(save: bool = True) -> pd.DataFrame:
    """Calcule l'historique de la marge de crushing"""
    console.print("[cyan]⚙️  Calcul historique crush margin...[/cyan]")

    dfs = {}
    for commodity in ["soybean", "soyoil", "soymeal"]:
        path = DATA_RAW / f"{commodity}_futures.csv"
        if path.exists():
            dfs[commodity] = pd.read_csv(path, index_col="date", parse_dates=True)["close"]

    if len(dfs) < 3:
        console.print("[yellow]⚠ Données incomplètes pour l'historique crush[/yellow]")
        return pd.DataFrame()

    # Aligne sur les dates communes
    combined = pd.DataFrame(dfs).dropna()
    combined.columns = ["soybean", "soyoil", "soymeal"]

    results = []
    for date, row in combined.iterrows():
        crush = compute_crush_margin(
            soybean_price=row["soybean"],
            soyoil_price=row["soyoil"],
            soymeal_price=row["soymeal"],
        )
        results.append({
            "date":               date,
            "gross_crush_usd_bu": crush["gross_crush_usd_bu"],
            "net_crush_usd_bu":   crush["net_crush_usd_bu"],
            "net_crush_usd_mt":   crush["net_crush_usd_mt"],
            "crush_signal":       crush["crush_signal"],
        })

    df = pd.DataFrame(results)

    # Stats historiques
    df["crush_pctile"] = df["net_crush_usd_bu"].rank(pct=True) * 100

    if save:
        path = DATA_PROCESSED / "crush_history.csv"
        df.to_csv(path, index=False)
        console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

    # Affiche résumé
    current = df.iloc[-1]
    console.print(f"\n[bold]Crush Margin actuelle : ${current['net_crush_usd_bu']:.2f}/bu "
                  f"(${current['net_crush_usd_mt']:.1f}/MT) — "
                  f"Percentile historique : {current['crush_pctile']:.0f}%[/bold]")

    return df


def print_crush_summary(result: dict):
    table = Table(title="⚙️  Soybean Crush Margin Breakdown")
    table.add_column("Composante",    style="cyan",        width=32)
    table.add_column("Valeur",        style="yellow",      width=18)
    table.add_column("Unité",         style="white",       width=15)

    rows = [
        ("Soja (coût intrant)",       f"{result['soybean_price_cents_bu']:.1f}",  "cents/boisseau"),
        ("Huile soja (prix)",         f"{result['soyoil_price_cents_lb']:.2f}",   "cents/livre"),
        ("Tourteau soja (prix)",      f"{result['soymeal_price_usd_st']:.1f}",    "$/tonne courte"),
        ("─" * 25,                    "─" * 12, "─" * 10),
        ("Valeur huile produite",     f"${result['oil_value_per_bu']:.3f}",       "$/boisseau"),
        ("Valeur tourteau produit",   f"${result['meal_value_per_bu']:.3f}",      "$/boisseau"),
        ("Valeur totale produits",    f"${result['gross_product_value']:.3f}",    "$/boisseau"),
        ("─" * 25,                    "─" * 12, "─" * 10),
        ("Coût soja brut",            f"${result['soybean_cost_per_bu']:.3f}",    "$/boisseau"),
        ("Marge brute (Gross Crush)", f"${result['gross_crush_usd_bu']:.3f}",     "$/boisseau"),
        ("Coûts process",             f"${result['processing_cost_per_bu']:.3f}", "$/boisseau"),
        ("MARGE NETTE (Net Crush)",   f"${result['net_crush_usd_bu']:.3f}",       "$/boisseau"),
        ("MARGE NETTE",               f"${result['net_crush_usd_mt']:.2f}",       "$/tonne MT"),
    ]

    for name, val, unit in rows:
        table.add_row(name, str(val), unit)

    console.print(table)
    console.print(f"\n  Signal : {result['signal']}\n")