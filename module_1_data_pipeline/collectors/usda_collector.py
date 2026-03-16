"""
Collector : Données USDA — WASDE & PSD (Production Supply Distribution)
Source    : api.usda.gov — gratuit, clé API requise
Clé       : https://apps.fas.usda.gov/psdonline/app/index.html#/app/downloads
Données   : Production, stocks, exports, imports par pays & commodité
"""

import requests
import pandas as pd
from rich.console import Console
from pathlib import Path
import sys, time
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import USDA_API_KEY, DATA_RAW

console = Console()

# Codes USDA pour nos commodités
USDA_COMMODITIES = {
    "wheat":   "0410000",
    "corn":    "0440000",
    "soybean": "2222000",
}

# Pays clés à monitorer
KEY_COUNTRIES = {
    "US": "United States",
    "BR": "Brazil",
    "AR": "Argentina",
    "UA": "Ukraine",
    "RU": "Russia",
    "AU": "Australia",
    "EU": "European Union",
}

BASE_URL = "https://apps.fas.usda.gov/psdonline/api/psd/file"

def fetch_usda_psd(commodity_code: str, commodity_name: str) -> pd.DataFrame:
    """
    Récupère les données PSD (Production Supply Distribution) de l'USDA.
    Contient : production, stocks de début/fin, exports, imports, consommation.
    """
    if not USDA_API_KEY:
        console.print("[yellow]⚠ Pas de clé USDA — utilisation des données de démo[/yellow]")
        return _get_demo_data(commodity_name)

    url = f"https://apps.fas.usda.gov/psdonline/api/psd/commodity/{commodity_code}"
    headers = {"Accept": "application/json"}
    params = {"API_KEY": USDA_API_KEY}

    try:
        console.print(f"[cyan]⬇ Fetching USDA PSD pour {commodity_name}...[/cyan]")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        df = pd.DataFrame(data)
        df["commodity"] = commodity_name

        console.print(f"[green]✓ {len(df)} enregistrements USDA pour {commodity_name}[/green]")
        return df

    except requests.exceptions.RequestException as e:
        console.print(f"[red]✗ Erreur USDA API: {e}[/red]")
        return _get_demo_data(commodity_name)


def _get_demo_data(commodity_name: str) -> pd.DataFrame:
    """
    Données de démonstration quand l'API n'est pas disponible.
    Reproduit la structure réelle des données USDA PSD.
    """
    demo = {
        "commodity_desc": [commodity_name] * 4,
        "country_name": ["United States", "Brazil", "Argentina", "Ukraine"],
        "market_year": [2023, 2023, 2023, 2023],
        "production":  [49690, 15400, 12500, 20000],  # 1000 MT
        "exports":     [21000,  9500,  9000, 10000],
        "imports":     [  100,    50,    20,    50],
        "ending_stocks":[7500,  1200,   800,  1500],
    }
    return pd.DataFrame(demo)


def fetch_all_usda(save: bool = True) -> dict:
    """Fetch USDA pour toutes les commodités"""
    results = {}

    for key, code in USDA_COMMODITIES.items():
        df = fetch_usda_psd(code, key)
        if not df.empty:
            results[key] = df
            if save:
                path = DATA_RAW / f"{key}_usda_psd.csv"
                df.to_csv(path, index=False)
                console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")
        time.sleep(0.5)  # Rate limiting

    return results


if __name__ == "__main__":
    fetch_all_usda(save=True)