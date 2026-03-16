"""
Signal Engine : Agrège tous les indicateurs en signaux tradables par commodité
Output        : Score directionnel -3 à +3 par commodité + conviction level
"""

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_PROCESSED

from module_3_signals.indicators.technical_indicators  import run_all_technical
from module_3_signals.indicators.sentiment_indicators  import compute_cot_signals, compute_bdi_signals
from module_3_signals.indicators.weather_indicators    import compute_all_weather_signals, get_weather_alert_summary

console = Console()

# Poids de chaque signal dans le score composite
SIGNAL_WEIGHTS = {
    "momentum":   0.25,   # Trend following
    "rsi":        0.10,   # Technique
    "bb":         0.10,   # Technique
    "cot":        0.25,   # Sentiment (très important en agri)
    "weather":    0.20,   # Fondamental (sécheresse = impact immédiat)
    "bdi":        0.10,   # Macro freight
}

# Mapping zones météo → commodités
WEATHER_COMMODITY_MAP = {
    "wheat":   ["us_plains_wheat", "ukraine_black_earth", "australia_wheatbelt"],
    "corn":    ["us_midwest_corn_belt", "brazil_mato_grosso"],
    "soybean": ["us_midwest_corn_belt", "brazil_mato_grosso", "argentina_pampas"],
}


def generate_signal_for_commodity(
    commodity: str,
    technical_df: pd.DataFrame,
    cot_df: pd.DataFrame,
    bdi_df: pd.DataFrame,
    weather_results: dict,
) -> dict:
    """
    Génère un signal composite pour une commodité donnée.
    Retourne un dict avec le score, la direction, et le détail par composant.
    """

    signals = {}

    # 1. Signaux techniques (dernière valeur disponible)
    last = technical_df.dropna(subset=["rsi"]).iloc[-1]
    signals["momentum"] = int(last.get("momentum_signal", 0))
    signals["rsi"]      = int(last.get("rsi_signal", 0))
    signals["bb"]       = int(last.get("bb_signal", 0))

    latest_price = last["close"]
    latest_rsi   = last["rsi"]
    latest_roc1m = last.get("roc_1m", 0)

    # 2. Signal COT
    cot_comm = cot_df[cot_df["commodity"] == commodity]
    if not cot_comm.empty:
        signals["cot"] = int(cot_comm.sort_values("date").iloc[-1]["cot_signal"])
    else:
        signals["cot"] = 0

    # 3. Signal BDI (même pour toutes les commodités)
    if not bdi_df.empty:
        signals["bdi"] = int(bdi_df.sort_values("date").iloc[-1]["bdi_signal"])
    else:
        signals["bdi"] = 0

    # 4. Signal météo (moyenne des zones pertinentes pour cette commodité)
    weather_signals = []
    for zone in WEATHER_COMMODITY_MAP.get(commodity, []):
        if zone in weather_results:
            wdf = weather_results[zone]
            if not wdf.empty:
                last_w = wdf.sort_values("date").iloc[-1]
                weather_signals.append(int(last_w.get("weather_signal", 0)))
    signals["weather"] = int(np.sign(np.mean(weather_signals))) if weather_signals else 0

    # 5. Score composite pondéré
    composite = sum(SIGNAL_WEIGHTS[k] * v for k, v in signals.items())

    # 6. Direction et conviction
    if composite > 0.15:
        direction = "BULLISH 🟢"
        conviction = min(int(composite / 0.15 * 33), 100)
    elif composite < -0.15:
        direction = "BEARISH 🔴"
        conviction = min(int(abs(composite) / 0.15 * 33), 100)
    else:
        direction = "NEUTRAL ⚪"
        conviction = 0

    return {
        "commodity":     commodity,
        "price":         round(latest_price, 2),
        "rsi":           round(latest_rsi, 1),
        "roc_1m_pct":    round(latest_roc1m, 1),
        "signals":       signals,
        "composite":     round(composite, 3),
        "direction":     direction,
        "conviction_pct": conviction,
    }


def run_signal_engine(save: bool = True) -> dict:
    """Lance le moteur de signaux enrichi"""
    console.print("\n[bold cyan]⚡ Calcul des signaux enrichis...[/bold cyan]\n")

    # Chargement données existantes
    console.print("[dim]Indicateurs techniques...[/dim]")
    technical = {c: run_all_technical(c, save=False) for c in ["wheat","corn","soybean"]}

    console.print("[dim]Signaux COT...[/dim]")
    cot_df = compute_cot_signals(save=False)

    console.print("[dim]Signaux BDI...[/dim]")
    bdi_df = compute_bdi_signals(save=False)

    console.print("[dim]Signaux météo...[/dim]")
    weather = compute_all_weather_signals(save=False)

    # NOUVEAU : chargement NDVI
    console.print("[dim]Signaux NDVI satellite...[/dim]")
    ndvi_df = pd.DataFrame()
    try:
        ndvi_path = DATA_RAW / "ndvi_vegetation.csv"
        if ndvi_path.exists():
            ndvi_df = pd.read_csv(ndvi_path, parse_dates=["date"])
            console.print(f"[green]✓ NDVI chargé — {ndvi_df['zone'].nunique()} zones[/green]")
        else:
            console.print("[yellow]⚠ NDVI non disponible — lance ndvi_collector.py[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠ NDVI erreur : {e}[/yellow]")

    # Génération signaux
    results = {}
    for commodity in ["wheat", "corn", "soybean"]:
        result = generate_signal_for_commodity(
            commodity=commodity,
            technical_df=technical[commodity],
            cot_df=cot_df,
            bdi_df=bdi_df,
            weather_results=weather,
            ndvi_df=ndvi_df,
        )
        results[commodity] = result

    if save:
        rows = []
        for c, r in results.items():
            rows.append({
                "commodity":    c,
                **r["signals"],
                "composite":    r["composite"],
                "direction":    r["direction"],
                "conviction":   r["conviction_pct"],
                "cot_pctile":   r["cot_pctile"],
                "ndvi_value":   r["ndvi_value"],
            })
        pd.DataFrame(rows).to_csv(DATA_PROCESSED / "signals_summary.csv", index=False)
        console.print("\n[blue]💾 Signaux enrichis sauvegardés[/blue]")

    return results


def print_signal_dashboard(results: dict):
    """Affiche le dashboard des signaux en console"""

    table = Table(title="🌾 AgroTrade — Signal Dashboard", show_lines=True)
    table.add_column("Commodité",   style="bold cyan",  width=12)
    table.add_column("Prix",        style="white",       width=10)
    table.add_column("RSI",         style="white",       width=8)
    table.add_column("ROC 1M",      style="white",       width=10)
    table.add_column("Momentum",    style="yellow",      width=10)
    table.add_column("COT",         style="yellow",      width=8)
    table.add_column("Météo",       style="yellow",      width=8)
    table.add_column("BDI",         style="yellow",      width=8)
    table.add_column("Score",       style="bold",        width=8)
    table.add_column("Direction",   style="bold",        width=18)
    table.add_column("Conviction",  style="bold green",  width=12)

    signal_icons = {1: "▲ Bull", -1: "▼ Bear", 0: "— Neu"}

    for c, r in results.items():
        s = r["signals"]
        table.add_row(
            c.upper(),
            f"{r['price']:.1f}",
            f"{r['rsi']:.1f}",
            f"{r['roc_1m_pct']:+.1f}%",
            signal_icons[s["momentum"]],
            signal_icons[s["cot"]],
            signal_icons[s["weather"]],
            signal_icons[s["bdi"]],
            f"{r['composite']:+.2f}",
            r["direction"],
            f"{r['conviction_pct']}%",
        )

    console.print(table)

    # Alertes météo
    alerts = get_weather_alert_summary()
    if not alerts.empty:
        console.print("\n[bold yellow]⚠️  Alertes Météo Actives :[/bold yellow]")
        for _, row in alerts.iterrows():
            console.print(f"  {row['alert_type']} — {row['zone']} "
                          f"(anomalie précip: {row['precip_anomaly_30d']:+.1f}%)")
            
# Dans signal_engine.py, remplace la fonction generate_signal_for_commodity

def generate_signal_for_commodity(
    commodity: str,
    technical_df: pd.DataFrame,
    cot_df: pd.DataFrame,
    bdi_df: pd.DataFrame,
    weather_results: dict,
    ndvi_df: pd.DataFrame = None,   # ← NOUVEAU
) -> dict:
    """Signal composite enrichi avec NDVI"""

    signals = {}

    # 1. Signaux techniques
    last = technical_df.dropna(subset=["rsi"]).iloc[-1]
    signals["momentum"] = int(last.get("momentum_signal", 0))
    signals["rsi"]      = int(last.get("rsi_signal", 0))
    signals["bb"]       = int(last.get("bb_signal", 0))

    latest_price  = last["close"]
    latest_rsi    = last["rsi"]
    latest_roc1m  = last.get("roc_1m", 0)

    # 2. Signal COT enrichi
    cot_comm = cot_df[cot_df["commodity"] == commodity]
    if not cot_comm.empty:
        last_cot          = cot_comm.sort_values("date").iloc[-1]
        signals["cot"]    = int(last_cot["cot_signal"])
        cot_pctile        = float(last_cot.get("nsl_pctile", 50))
        cot_divergence    = int(last_cot.get("divergence", 0))
    else:
        signals["cot"]    = 0
        cot_pctile        = 50
        cot_divergence    = 0

    # 3. Signal BDI
    if not bdi_df.empty:
        signals["bdi"] = int(bdi_df.sort_values("date").iloc[-1]["bdi_signal"])
    else:
        signals["bdi"] = 0

    # 4. Signal météo
    weather_signals = []
    for zone in WEATHER_COMMODITY_MAP.get(commodity, []):
        if zone in weather_results:
            wdf = weather_results[zone]
            if not wdf.empty:
                last_w = wdf.sort_values("date").iloc[-1]
                weather_signals.append(int(last_w.get("weather_signal", 0)))
    signals["weather"] = int(np.sign(np.mean(weather_signals))) if weather_signals else 0

    # 5. Signal NDVI ← NOUVEAU
    ndvi_signal = 0
    ndvi_value  = None
    ndvi_zone   = None
    if ndvi_df is not None and not ndvi_df.empty:
        # Zones NDVI pertinentes pour cette commodité
        ndvi_commodity_map = {
            "wheat":   ["us_wheat_plains", "ukraine_steppe", "australia_wheatbelt"],
            "corn":    ["us_corn_belt"],
            "soybean": ["us_corn_belt", "brazil_cerrado", "argentina_pampas"],
        }
        relevant_zones = ndvi_commodity_map.get(commodity, [])
        zone_signals   = []

        for zone in relevant_zones:
            zone_data = ndvi_df[ndvi_df["zone"] == zone]
            if not zone_data.empty:
                last_ndvi = zone_data.sort_values("date").iloc[-1]
                zone_signals.append(int(last_ndvi.get("price_signal", 0)))
                if ndvi_value is None:
                    ndvi_value = round(float(last_ndvi.get("ndvi_proxy", 0.5)), 3)
                    ndvi_zone  = zone

        ndvi_signal = int(np.sign(np.mean(zone_signals))) if zone_signals else 0

    signals["ndvi"] = ndvi_signal

    # 6. Score composite pondéré — poids mis à jour avec NDVI
    weights = {
        "momentum": 0.22,
        "rsi":      0.08,
        "bb":       0.08,
        "cot":      0.25,   # COT reste le plus important en agri
        "weather":  0.17,
        "bdi":      0.08,
        "ndvi":     0.12,   # NDVI satellite — signal avancé récolte
    }

    composite = sum(weights[k] * v for k, v in signals.items() if k in weights)

    # Bonus si divergence COT forte (signal contrarian de haute conviction)
    if cot_divergence != 0 and abs(cot_pctile - 50) > 30:
        composite += cot_divergence * 0.05

    # 7. Direction et conviction
    if composite > 0.15:
        direction = "BULLISH 🟢"
        conviction = min(int(abs(composite) / 0.3 * 100), 100)
    elif composite < -0.15:
        direction = "BEARISH 🔴"
        conviction = min(int(abs(composite) / 0.3 * 100), 100)
    else:
        direction  = "NEUTRAL ⚪"
        conviction = 0

    return {
        "commodity":      commodity,
        "price":          round(latest_price, 2),
        "rsi":            round(latest_rsi, 1),
        "roc_1m_pct":     round(latest_roc1m, 1),
        "signals":        signals,
        "composite":      round(composite, 3),
        "direction":      direction,
        "conviction_pct": conviction,
        "cot_pctile":     cot_pctile,
        "cot_divergence": cot_divergence,
        "ndvi_value":     ndvi_value,
        "ndvi_zone":      ndvi_zone,
    }