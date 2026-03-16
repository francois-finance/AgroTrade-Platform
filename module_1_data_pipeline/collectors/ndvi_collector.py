"""
Collector : NDVI (Normalized Difference Vegetation Index)
Source    : NASA MODIS via AppEEARS API — gratuit, inscription requise
            https://appeears.earthdatacloud.nasa.gov/
Alternative gratuite immédiate : Open-Meteo agro variables (pas besoin de clé)
Données   : Santé de la végétation par zone agricole, tous les 16 jours
Logique   : NDVI < 0.3 en période critique = stress végétatif = bullish prix
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from rich.console import Console
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW

console = Console()

# Zones agricoles stratégiques pour le NDVI
NDVI_ZONES = {
    "us_corn_belt":      {
        "lat": 41.5, "lon": -93.5,
        "description": "Iowa — Corn Belt US",
        "key_crops": ["corn", "soybean"],
        "critical_months": [6, 7, 8],   # Juin-Août : pollinisation maïs
    },
    "us_wheat_plains":   {
        "lat": 38.0, "lon": -98.0,
        "description": "Kansas — Winter Wheat",
        "key_crops": ["wheat"],
        "critical_months": [4, 5, 6],   # Avril-Juin : grain fill
    },
    "brazil_cerrado":    {
        "lat": -13.0, "lon": -56.0,
        "description": "Mato Grosso — Soja Brésil",
        "key_crops": ["soybean"],
        "critical_months": [12, 1, 2],  # Déc-Fév : floraison soja
    },
    "ukraine_steppe":    {
        "lat": 49.0, "lon": 32.0,
        "description": "Ukraine — Tchernozem",
        "key_crops": ["wheat", "corn"],
        "critical_months": [5, 6, 7],
    },
    "argentina_pampas":  {
        "lat": -34.0, "lon": -60.0,
        "description": "Pampas argentines",
        "key_crops": ["soybean", "wheat"],
        "critical_months": [1, 2, 3],
    },
    "australia_wheatbelt":{
        "lat": -31.5, "lon": 117.0,
        "description": "Western Australia — Blé",
        "key_crops": ["wheat"],
        "critical_months": [9, 10, 11],
    },
}

# Seuils NDVI par niveau de stress
NDVI_THRESHOLDS = {
    "severe_stress":  0.20,   # Catastrophe végétale — très bullish
    "moderate_stress":0.35,   # Stress modéré — bullish
    "normal":         0.55,   # Végétation normale
    "excellent":      0.70,   # Excellentes conditions — bearish prix
}


def fetch_ndvi_open_meteo(zone_name: str, zone_info: dict,
                          days_back: int = 180) -> pd.DataFrame:
    """
    Approximation du NDVI via Open-Meteo :
    On utilise l'évapotranspiration et l'humidité du sol comme proxies.
    Pas du vrai NDVI satellite mais accessible sans inscription.

    Pour le vrai NDVI NASA MODIS :
    → S'inscrire sur https://urs.earthdata.nasa.gov/
    → Utiliser l'API AppEEARS ou directement earthaccess
    """
    url = "https://archive-api.open-meteo.com/v1/archive"

    end_date   = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "latitude":   zone_info["lat"],
        "longitude":  zone_info["lon"],
        "start_date": start_date,
        "end_date":   end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration",
        "timezone": "UTC"
    }

    try:
        console.print(f"[cyan]🛰️  NDVI proxy : {zone_info['description']}...[/cyan]")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()["daily"]
        df   = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["time"])
        df.drop("time", axis=1, inplace=True)
        df["zone"]        = zone_name
        df["description"] = zone_info["description"]

        # ── Calcul du NDVI proxy via bilan hydrique ──────────────────────
        pr = df["precipitation_sum"].rolling(30).sum().fillna(0)
        et = df["et0_fao_evapotranspiration"].rolling(30).sum().fillna(10)

        water_balance = (pr - et)
        wb_norm       = (water_balance - water_balance.min()) / (
                         water_balance.max() - water_balance.min() + 1e-9)

        # NDVI proxy entre 0.1 et 0.9
        df["ndvi_proxy"] = (0.25 + 0.65 * wb_norm).clip(0.1, 0.9)

        # ── Catégorie de stress ───────────────────────────────────────────
        df["stress_category"] = "normal"
        df.loc[df["ndvi_proxy"] < NDVI_THRESHOLDS["severe_stress"],
               "stress_category"] = "severe_stress"
        df.loc[
            (df["ndvi_proxy"] >= NDVI_THRESHOLDS["severe_stress"]) &
            (df["ndvi_proxy"] <  NDVI_THRESHOLDS["moderate_stress"]),
            "stress_category"
        ] = "moderate_stress"
        df.loc[df["ndvi_proxy"] >= NDVI_THRESHOLDS["excellent"],
               "stress_category"] = "excellent"

        # ── Signal de prix ────────────────────────────────────────────────
        current_month = datetime.today().month
        is_critical   = current_month in zone_info["critical_months"]

        df["price_signal"] = 0
        if is_critical:
            df.loc[df["ndvi_proxy"] < NDVI_THRESHOLDS["moderate_stress"],
                   "price_signal"] =  1   # Bullish
            df.loc[df["ndvi_proxy"] > NDVI_THRESHOLDS["excellent"],
                   "price_signal"] = -1   # Bearish
        else:
            df.loc[df["ndvi_proxy"] < NDVI_THRESHOLDS["severe_stress"],
                   "price_signal"] =  1
            df.loc[df["ndvi_proxy"] > NDVI_THRESHOLDS["excellent"],
                   "price_signal"] = -1

        df["is_critical_window"] = is_critical
        df["crops"]              = str(zone_info["key_crops"])

        console.print(f"[green]✓ {len(df)} jours NDVI proxy pour {zone_name}[/green]")
        return df

    except Exception as e:
        console.print(f"[red]✗ Erreur NDVI {zone_name}: {e}[/red]")
        return pd.DataFrame()


def get_ndvi_alert_summary(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    Résumé des alertes NDVI actives.
    Retourne les zones en stress végétatif actuellement.
    """
    if df_all.empty:
        return pd.DataFrame()

    latest = df_all.sort_values("date").groupby("zone").last().reset_index()

    alerts = []
    for _, row in latest.iterrows():
        ndvi     = row.get("ndvi_proxy", 0.5)
        signal   = int(row.get("price_signal", 0))
        critical = bool(row.get("is_critical_window", False))

        alerts.append({
            "zone":            row["zone"],
            "description":     row["description"],
            "ndvi_proxy":      round(ndvi, 3),
            "stress_category": row["stress_category"],
            "price_signal":    signal,
            "critical_window": critical,
            "alert": (
                "🚨 STRESS SÉVÈRE" if ndvi < NDVI_THRESHOLDS["severe_stress"] else
                "⚠️  Stress modéré" if ndvi < NDVI_THRESHOLDS["moderate_stress"] else
                "✅ Normal"         if ndvi < NDVI_THRESHOLDS["excellent"] else
                "🌿 Excellent"
            )
        })

    result = pd.DataFrame(alerts)

    if not result.empty:
        result = result.sort_values("ndvi_proxy")

    return result


def fetch_all_ndvi(save: bool = True) -> pd.DataFrame:
    """Lance le fetch NDVI sur toutes les zones"""
    console.print("\n[bold cyan]🛰️  Collecte NDVI — Santé végétation agricole[/bold cyan]\n")

    all_dfs = []
    for zone_name, zone_info in NDVI_ZONES.items():
        df = fetch_ndvi_open_meteo(zone_name, zone_info)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        console.print("[red]✗ Aucune donnée NDVI collectée[/red]")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)

    if save:
        path = DATA_RAW / "ndvi_vegetation.csv"
        combined.to_csv(path, index=False)
        console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

    # Affiche le résumé des alertes
    alerts = get_ndvi_alert_summary(combined)
    if not alerts.empty:
        console.print("\n[bold]🛰️  Résumé NDVI par zone :[/bold]")
        for _, row in alerts.iterrows():
            critical_tag = " [FENÊTRE CRITIQUE]" if row["critical_window"] else ""
            console.print(
                f"  {row['alert']}{critical_tag} — {row['description']} "
                f"(NDVI: {row['ndvi_proxy']:.2f})"
            )
    else:
        console.print("[dim]Aucune alerte NDVI active[/dim]")

    return combined


if __name__ == "__main__":
    fetch_all_ndvi(save=True)