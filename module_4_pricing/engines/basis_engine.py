"""
Engine : Base physique vs Futures
Définition : Basis = Prix Cash local - Prix Futures CBOT
Utilité    : Le basis mesure les conditions locales du marché physique.
             Un basis qui se renforce (monte) = demande locale forte
             Un basis qui s'affaiblit (baisse) = offre abondante localement

C'est LE concept central du trading physique céréalier.
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

# Basis de référence par localisation et commodité (en cents/bushel vs CBOT)
# Ces valeurs reflètent les conditions normales de marché
# Positif = prime locale, Négatif = décote locale
REFERENCE_BASIS = {
    "wheat": {
        "us_gulf_export":        +20,   # Prime export Gulf
        "us_hrd_winter_kansas":  -15,   # HRD Kansas vs SRW Chicago
        "us_srw_ohio":           -10,   # SRW Ohio
        "france_rouen":          +45,   # Prime qualité blé meunerie France
        "ukraine_odesa_fob":     -80,   # Décote géopolitique Ukraine
        "argentina_rosario_fob": -40,   # Origine compétitive Argentine
        "australia_asx_fob":     -25,   # Australie
    },
    "corn": {
        "us_gulf_export":        +35,   # Prime export Gulf
        "us_iowa_elevator":      -20,   # Elevator Iowa (base campagne)
        "us_illinois_barge":     -10,   # Barge Illinois River
        "brazil_paranagua_fob":  -55,   # Brésil très compétitif
        "argentina_up_river":    -65,   # Argentine très compétitif
        "ukraine_odesa_fob":     -70,
    },
    "soybean": {
        "us_gulf_export":        +55,   # Forte prime export soja US
        "us_iowa_elevator":      -15,
        "brazil_paranagua_fob":  -30,   # Brésil compétitif
        "argentina_up_river":    -45,
    },
}


def compute_basis(
    commodity: str,
    location: str,
    cash_price: float = None,
    futures_price: float = None,
) -> dict:
    """
    Calcule ou estime la base pour une commodité/localisation.

    Si cash_price et futures_price sont fournis → calcul réel
    Sinon → utilise les basis de référence + prix futures récents
    """
    # Charge le prix futures actuel si non fourni
    if futures_price is None:
        path = DATA_RAW / f"{commodity}_futures.csv"
        if path.exists():
            df = pd.read_csv(path, index_col="date", parse_dates=True)
            futures_price = float(df["close"].iloc[-1])
        else:
            futures_price = {"wheat": 600, "corn": 440, "soybean": 1150}.get(commodity, 500)

    # Basis de référence pour cette localisation
    ref_basis = REFERENCE_BASIS.get(commodity, {}).get(location, 0)

    # Si pas de prix cash fourni, l'estime avec le basis de référence
    if cash_price is None:
        cash_price = futures_price + ref_basis

    actual_basis = cash_price - futures_price
    basis_vs_ref = actual_basis - ref_basis

    # Interprétation
    if basis_vs_ref > 10:
        interpretation = "🟢 Basis fort — demande locale élevée / offre serrée"
    elif basis_vs_ref < -10:
        interpretation = "🔴 Basis faible — offre abondante / demande atone"
    else:
        interpretation = "⚪ Basis normal — conditions de marché équilibrées"

    return {
        "commodity":       commodity,
        "location":        location,
        "futures_price":   round(futures_price, 2),
        "cash_price":      round(cash_price, 2),
        "actual_basis":    round(actual_basis, 2),
        "reference_basis": ref_basis,
        "basis_vs_ref":    round(basis_vs_ref, 2),
        "interpretation":  interpretation,
    }


def run_basis_analysis(save: bool = True) -> pd.DataFrame:
    """Calcule la base sur toutes les localisations de référence"""
    console.print("[cyan]📐 Analyse des bases physiques...[/cyan]")
    rows = []

    for commodity, locations in REFERENCE_BASIS.items():
        for location in locations:
            result = compute_basis(commodity, location)
            rows.append(result)

    df = pd.DataFrame(rows)

    # Affichage
    for commodity in ["wheat", "corn", "soybean"]:
        sub = df[df["commodity"] == commodity]
        table = Table(title=f"📐 Basis Analysis — {commodity.upper()}")
        table.add_column("Location",       style="cyan",        width=30)
        table.add_column("Futures",        style="white",       width=12)
        table.add_column("Cash",           style="white",       width=12)
        table.add_column("Basis",          style="bold yellow", width=10)
        table.add_column("vs Référence",   style="bold",        width=14)
        table.add_column("Signal",         style="dim",         width=40)

        for _, row in sub.iterrows():
            vs_ref = f"{row['basis_vs_ref']:+.0f}c"
            color  = "green" if row["basis_vs_ref"] > 10 else ("red" if row["basis_vs_ref"] < -10 else "white")
            table.add_row(
                row["location"],
                f"{row['futures_price']:.1f}c",
                f"{row['cash_price']:.1f}c",
                f"{row['actual_basis']:+.0f}c",
                f"[{color}]{vs_ref}[/{color}]",
                row["interpretation"],
            )
        console.print(table)

    if save:
        path = DATA_PROCESSED / "basis_analysis.csv"
        df.to_csv(path, index=False)
        console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

    return df