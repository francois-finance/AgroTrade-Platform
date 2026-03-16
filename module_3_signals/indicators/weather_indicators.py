"""
Indicators : Signaux météo sur zones agricoles clés
Logique    : Anomalies de précipitations + stress hydrique → impact sur rendements
"""

import pandas as pd
import numpy as np
from rich.console import Console
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED, AGRI_ZONES

console = Console()

# Fenêtres critiques par commodité (mois où la météo est la plus impactante)
CRITICAL_WINDOWS = {
    "wheat":   {"us_plains_wheat":        [4, 5, 6],      # Grain fill
                "black_sea_ukraine":       [5, 6, 7],      # Harvest
                "australia_wheatbelt":     [9, 10, 11]},   # Sowing
    "corn":    {"us_midwest_corn_belt":    [6, 7, 8],      # Pollination = critique
                "brazil_mato_grosso":      [1, 2, 3]},     # Safrinha season
    "soybean": {"us_midwest_corn_belt":    [7, 8],         # Pod fill
                "brazil_mato_grosso":      [12, 1, 2],     # Première récolte
                "argentina_pampas":        [1, 2, 3]},     # Récolte principale
}


def compute_precipitation_anomaly(zone_name: str, save: bool = True) -> pd.DataFrame:
    """
    Calcule l'anomalie de précipitation par rapport à la moyenne historique.
    Une anomalie négative persistante = sécheresse = signal haussier pour la commodité concernée.
    """
    path = DATA_RAW / f"weather_{zone_name}.csv"
    if not path.exists():
        console.print(f"[yellow]⚠ Météo manquante pour {zone_name}[/yellow]")
        return pd.DataFrame()

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Moyenne historique des précipitations par mois
    df["month"] = df["date"].dt.month
    monthly_avg = df.groupby("month")["precipitation_sum"].mean()
    df["precip_avg"] = df["month"].map(monthly_avg)

    # Anomalie en % vs moyenne historique
    df["precip_anomaly_pct"] = (
        (df["precipitation_sum"] - df["precip_avg"]) / (df["precip_avg"] + 0.1)
    ) * 100

    # Rolling 30 jours pour lisser
    df["precip_anomaly_30d"] = df["precip_anomaly_pct"].rolling(30).mean()

    # Stress hydrique composite
    # Combine précipitations + évapotranspiration
    if "et0_fao_evapotranspiration" in df.columns:
        df["water_balance"] = df["precipitation_sum"] - df["et0_fao_evapotranspiration"]
        df["water_stress_30d"] = df["water_balance"].rolling(30).mean()
    else:
        df["water_balance"]   = df["precipitation_sum"]
        df["water_stress_30d"] = df["precip_anomaly_30d"]

    # Signal météo
    df["weather_signal"] = 0
    df.loc[df["precip_anomaly_30d"] < -30, "weather_signal"] =  1   # Sécheresse → bullish prix
    df.loc[df["precip_anomaly_30d"] >  30, "weather_signal"] = -1   # Trop humide → bearish

    df["zone"] = zone_name
    return df


def compute_all_weather_signals(save: bool = True) -> dict:
    """Lance l'analyse météo sur toutes les zones disponibles"""
    results = {}

    zones = [
        "us_midwest_corn_belt", "us_plains_wheat",
        "brazil_mato_grosso", "argentina_pampas",
        "ukraine_black_earth", "australia_wheatbelt"
    ]

    for zone in zones:
        df = compute_precipitation_anomaly(zone)
        if not df.empty:
            results[zone] = df
            console.print(f"[green]✓ Signaux météo calculés : {zone}[/green]")

    if save and results:
        combined = pd.concat(results.values(), ignore_index=True)
        path = DATA_PROCESSED / "weather_signals.csv"
        combined.to_csv(path, index=False)
        console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

    return results


def get_weather_alert_summary() -> pd.DataFrame:
    """
    Résumé des alertes météo actives.
    Retourne les zones en stress actuellement.
    """
    path = DATA_PROCESSED / "weather_signals.csv"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path, parse_dates=["date"])
    latest = df.sort_values("date").groupby("zone").last().reset_index()

    alerts = latest[latest["weather_signal"] != 0][
        ["zone", "precip_anomaly_30d", "water_stress_30d", "weather_signal"]
    ].copy()

    alerts["alert_type"] = alerts["weather_signal"].map({
        1:  "🌵 SÉCHERESSE — Bullish",
        -1: "🌧️ EXCÈS EAU — Bearish"
    })

    return alerts