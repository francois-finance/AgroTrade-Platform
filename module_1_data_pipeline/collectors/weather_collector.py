"""
Collector : Données météo agricoles
Source    : Open-Meteo API — 100% gratuit, sans clé API
Données   : Température, précipitations sur zones de production clés
"""

import requests
import pandas as pd
from rich.console import Console
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW

console = Console()

# Zones agricoles stratégiques mondiales
AGRI_ZONES = {
    "us_midwest_corn_belt": {
        "lat": 41.5, "lon": -93.5,
        "description": "Iowa — cœur du Corn Belt US",
        "key_crops": ["corn", "soybean"]
    },
    "us_plains_wheat": {
        "lat": 38.0, "lon": -98.0,
        "description": "Kansas — Winter Wheat",
        "key_crops": ["wheat"]
    },
    "brazil_mato_grosso": {
        "lat": -13.0, "lon": -56.0,
        "description": "Mato Grosso — Soja Brésil",
        "key_crops": ["soybean", "corn"]
    },
    "argentina_pampas": {
        "lat": -34.0, "lon": -60.0,
        "description": "Pampas — Soja/Blé Argentine",
        "key_crops": ["soybean", "wheat"]
    },
    "ukraine_black_earth": {
        "lat": 49.0, "lon": 32.0,
        "description": "Ukraine — Tchernozem",
        "key_crops": ["wheat", "corn", "soybean"]
    },
    "australia_wheatbelt": {
        "lat": -31.5, "lon": 117.0,
        "description": "Western Australia — Blé",
        "key_crops": ["wheat"]
    },
}

def fetch_weather_zone(zone_name: str, zone_info: dict, days_back: int = 365) -> pd.DataFrame:
    url = "https://archive-api.open-meteo.com/v1/archive"

    from datetime import datetime, timedelta
    end_date   = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")   # ← fix
    start_date = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "latitude":  zone_info["lat"],
        "longitude": zone_info["lon"],
        "start_date": start_date,
        "end_date":   end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration",  # ← virgules, pas de liste
        "timezone": "UTC"
    }
    

    try:
        console.print(f"[cyan]⬇ Météo : {zone_info['description']}...[/cyan]")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()["daily"]
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["time"])
        df.drop("time", axis=1, inplace=True)
        df["zone"] = zone_name
        df["crops"] = str(zone_info["key_crops"])

        console.print(f"[green]✓ {len(df)} jours pour {zone_name}[/green]")
        return df

    except Exception as e:
        console.print(f"[red]✗ Erreur météo {zone_name}: {e}[/red]")
        return pd.DataFrame()


def fetch_all_weather(save: bool = True) -> dict:
    results = {}
    for zone_name, zone_info in AGRI_ZONES.items():
        df = fetch_weather_zone(zone_name, zone_info)
        if not df.empty:
            results[zone_name] = df
            if save:
                path = DATA_RAW / f"weather_{zone_name}.csv"
                df.to_csv(path, index=False)
                console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")
    return results


if __name__ == "__main__":
    fetch_all_weather(save=True)