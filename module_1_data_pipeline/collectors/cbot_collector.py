"""
Collector : Prix futures agricoles via yfinance (CBOT)
Source    : Yahoo Finance — gratuit, pas de clé API
Données   : OHLCV journalier, blé / maïs / soja et dérivés
"""

import yfinance as yf
import pandas as pd
from pathlib import Path
from rich.console import Console
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import COMMODITIES, DEFAULT_START, DATA_RAW

console = Console()

def fetch_futures_prices(
    ticker: str,
    name: str,
    start: str = DEFAULT_START,
    end: str = None
) -> pd.DataFrame:
    """
    Télécharge les prix OHLCV d'un contrat futures.
    Retourne un DataFrame propre avec colonnes standardisées.
    """
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")

    console.print(f"[cyan]⬇ Fetching {name} ({ticker}) from {start} to {end}...[/cyan]")

    try:
        raw = yf.download(ticker, start=start, end=end, progress=False)

        if raw.empty:
            console.print(f"[red]✗ Aucune donnée pour {ticker}[/red]")
            return pd.DataFrame()

        # Standardisation des colonnes
        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index.name = "date"
        df["ticker"] = ticker
        df["commodity"] = name

        console.print(f"[green]✓ {len(df)} jours téléchargés pour {name}[/green]")
        return df

    except Exception as e:
        console.print(f"[red]✗ Erreur pour {ticker}: {e}[/red]")
        return pd.DataFrame()


def fetch_all_commodities(save: bool = True) -> dict:
    """
    Lance le fetch pour toutes les commodités définies dans config.py
    Sauvegarde en CSV dans data/raw/
    """
    results = {}

    for key, info in COMMODITIES.items():
        df = fetch_futures_prices(
            ticker=info["ticker"],
            name=info["name"]
        )

        if not df.empty:
            results[key] = df

            if save:
                output_path = DATA_RAW / f"{key}_futures.csv"
                df.to_csv(output_path)
                console.print(f"[blue]💾 Sauvegardé : {output_path}[/blue]")

    console.print(f"\n[bold green]✅ Pipeline CBOT terminé — {len(results)}/{len(COMMODITIES)} commodités[/bold green]")
    return results


if __name__ == "__main__":
    fetch_all_commodities(save=True)