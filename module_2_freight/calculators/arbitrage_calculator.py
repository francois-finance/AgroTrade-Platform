"""
Calculator : Arbitrage géographique inter-origines
Question   : "Quelle est l'origine la moins chère livrée en CIF à destination X ?"
Exemple    : Blé livré en Égypte — US Gulf vs Black Sea vs Australie
"""

import pandas as pd
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import TRADE_ROUTES, DATA_RAW
from module_2_freight.calculators.freight_calculator import estimate_freight_cost

console = Console()


def compare_origins_for_destination(
    destination_key: str,
    commodity: str,
    fob_prices: dict,
    bdi_current: float = 1800.0,
) -> pd.DataFrame:
    """
    Compare toutes les origines disponibles pour livrer une commodité à une destination.

    Args:
        destination_key : Clé du port de destination (ex: 'egypt_damietta')
        commodity       : 'wheat', 'corn', ou 'soybean'
        fob_prices      : Dict {origin_key: fob_price_usd_per_ton}
                          ex: {'us_gulf': 220, 'black_sea_odesa': 195, 'australia_kwinana': 210}
        bdi_current     : BDI actuel

    Returns:
        DataFrame trié par prix CIF croissant — la meilleure origine en premier
    """
    results = []

    for route_key, route_info in TRADE_ROUTES.items():
        # Filtre : bonne destination ET bonne commodité
        if route_info["to"] != destination_key:
            continue
        if route_info["commodity"] != commodity:
            continue

        origin_key = route_info["from"]
        fob = fob_prices.get(origin_key)

        if fob is None:
            console.print(f"[dim]  Pas de prix FOB pour {origin_key} — ignoré[/dim]")
            continue

        try:
            calc = estimate_freight_cost(
                route_key=route_key,
                fob_price_per_ton=fob,
                bdi_current=bdi_current,
            )
            results.append({
                "route":           route_key,
                "origin":          calc["from"],
                "destination":     calc["to"],
                "fob_usd_t":       calc["fob_per_ton"],
                "freight_usd_t":   calc["freight_per_ton"],
                "insurance_usd_t": calc["insurance_per_ton"],
                "cif_usd_t":       calc["cif_per_ton"],
                "voyage_days":     calc["voyage_days"],
                "distance_nm":     calc["distance_nm"],
                "vessel":          calc["vessel_type"],
            })
        except Exception as e:
            console.print(f"[red]✗ Erreur pour {route_key}: {e}[/red]")

    if not results:
        console.print(f"[yellow]⚠ Aucune route trouvée pour {commodity} → {destination_key}[/yellow]")
        return pd.DataFrame()

    df = pd.DataFrame(results).sort_values("cif_usd_t").reset_index(drop=True)
    df["rank"] = df.index + 1
    df["spread_vs_cheapest"] = (df["cif_usd_t"] - df["cif_usd_t"].iloc[0]).round(2)

    return df


def print_arbitrage_table(df: pd.DataFrame, commodity: str, destination: str):
    """Affiche le tableau d'arbitrage formaté"""
    if df.empty:
        return

    title = f"🌾 Arbitrage {commodity.upper()} → {destination} (BDI actuel)"
    table = Table(title=title)

    table.add_column("Rang",       style="bold yellow", width=6)
    table.add_column("Origine",    style="cyan",        width=26)
    table.add_column("FOB $/t",    style="white",       width=10)
    table.add_column("Fret $/t",   style="white",       width=10)
    table.add_column("CIF $/t",    style="bold green",  width=10)
    table.add_column("Spread",     style="red",         width=10)
    table.add_column("Jours",      style="dim",         width=8)

    for _, row in df.iterrows():
        spread = f"+${row['spread_vs_cheapest']:.2f}" if row['spread_vs_cheapest'] > 0 else "✅ Best"
        table.add_row(
            str(int(row["rank"])),
            row["origin"],
            f"${row['fob_usd_t']:.0f}",
            f"${row['freight_usd_t']:.1f}",
            f"${row['cif_usd_t']:.1f}",
            spread,
            f"{row['voyage_days']:.0f}j",
        )

    console.print(table)


def run_full_arbitrage_analysis(bdi: float = 1800.0, save: bool = True):
    """
    Lance l'analyse d'arbitrage sur les cas les plus importants du marché.
    """
    console.print("\n[bold magenta]🔍 Analyse d'arbitrage inter-origines[/bold magenta]\n")

    analyses = [
        {
            "name": "Blé → Égypte (GASC)",
            "destination": "egypt_damietta",
            "commodity": "wheat",
            "fob_prices": {
                "us_gulf":           220.0,
                "black_sea_odesa":   195.0,
                "black_sea_novor":   192.0,
                "australia_kwinana": 210.0,
            }
        },
        {
            "name": "Maïs → Japon",
            "destination": "japan_osaka",
            "commodity": "corn",
            "fob_prices": {
                "us_gulf":        185.0,
                "brazil_santos":  175.0,
                "argentina_up":   170.0,
            }
        },
        {
            "name": "Soja → Chine",
            "destination": "china_shanghai",
            "commodity": "soybean",
            "fob_prices": {
                "brazil_paranagua": 380.0,
                "us_gulf":          395.0,
                "argentina_up":     365.0,
            }
        },
    ]

    all_results = {}
    for analysis in analyses:
        console.rule(f"[cyan]{analysis['name']}[/cyan]")
        df = compare_origins_for_destination(
            destination_key=analysis["destination"],
            commodity=analysis["commodity"],
            fob_prices=analysis["fob_prices"],
            bdi_current=bdi,
        )
        print_arbitrage_table(df, analysis["commodity"], analysis["name"])
        all_results[analysis["name"]] = df

        if save and not df.empty:
            fname = analysis["name"].replace(" ", "_").replace("→", "to").replace("(", "").replace(")", "")
            path = DATA_RAW / f"arb_{fname}.csv"
            df.to_csv(path, index=False)
            console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

    return all_results


if __name__ == "__main__":
    run_full_arbitrage_analysis(bdi=1800.0)