"""
Context Builder : Agrège tous les signaux de M1→M4 en un contexte
structuré prêt à être envoyé au LLM.

C'est le pont entre notre data pipeline et l'intelligence LLM.
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED

console = Console()


def load_latest_prices() -> dict:
    """Charge les derniers prix futures pour toutes les commodités"""
    prices = {}
    commodities = {
        "wheat":   {"name": "Blé CBOT",   "unit": "cents/bu"},
        "corn":    {"name": "Maïs CBOT",  "unit": "cents/bu"},
        "soybean": {"name": "Soja CBOT",  "unit": "cents/bu"},
        "soyoil":  {"name": "Huile Soja", "unit": "cents/lb"},
        "soymeal": {"name": "Tourteau",   "unit": "$/ton"},
    }

    for key, info in commodities.items():
        path = DATA_RAW / f"{key}_futures.csv"
        if path.exists():
            df = pd.read_csv(path, index_col="date", parse_dates=True)
            last = df["close"].dropna()
            prices[key] = {
                "name":    info["name"],
                "unit":    info["unit"],
                "current": round(float(last.iloc[-1]), 2),
                "prev_1w": round(float(last.iloc[-6]), 2) if len(last) > 5 else None,
                "prev_1m": round(float(last.iloc[-22]), 2) if len(last) > 21 else None,
                "prev_3m": round(float(last.iloc[-66]), 2) if len(last) > 65 else None,
                "chg_1w_pct":  round((float(last.iloc[-1]) / float(last.iloc[-6]) - 1) * 100, 2) if len(last) > 5 else None,
                "chg_1m_pct":  round((float(last.iloc[-1]) / float(last.iloc[-22]) - 1) * 100, 2) if len(last) > 21 else None,
                "chg_3m_pct":  round((float(last.iloc[-1]) / float(last.iloc[-66]) - 1) * 100, 2) if len(last) > 65 else None,
            }
    return prices


def load_technical_signals() -> dict:
    """Charge les derniers indicateurs techniques"""
    signals = {}
    for commodity in ["wheat", "corn", "soybean"]:
        path = DATA_PROCESSED / f"{commodity}_technical.csv"
        if path.exists():
            df = pd.read_csv(path, index_col="date", parse_dates=True)
            last = df.dropna(subset=["rsi"]).iloc[-1]
            signals[commodity] = {
                "rsi":             round(float(last.get("rsi", 50)), 1),
                "rsi_signal":      int(last.get("rsi_signal", 0)),
                "momentum_signal": int(last.get("momentum_signal", 0)),
                "bb_signal":       int(last.get("bb_signal", 0)),
                "roc_1m":          round(float(last.get("roc_1m", 0)), 2),
                "roc_3m":          round(float(last.get("roc_3m", 0)), 2),
                "ma50_above_ma200":int(last.get("ma50_above_ma200", 0)),
                "golden_cross":    int(last.get("golden_cross", 0)),
                "death_cross":     int(last.get("death_cross", 0)),
                "seasonal_signal": int(last.get("seasonal_signal", 0)),
            }
    return signals


def load_market_structure() -> dict:
    """Charge la structure de marché (carry/forward curve)"""
    structure = {}
    structure_map = {
        "wheat":   {"spot": 611, "m3": 618, "m6": 624},
        "corn":    {"spot": 447, "m3": 452, "m6": 458},
        "soybean": {"spot": 1185,"m3": 1195,"m6": 1202},
    }

    for commodity, defaults in structure_map.items():
        path = DATA_PROCESSED / f"{commodity}_technical.csv"
        spot = defaults["spot"]
        if path.exists():
            df = pd.read_csv(path, index_col="date", parse_dates=True)
            spot = round(float(df["close"].dropna().iloc[-1]), 2)

        spread_m1_m3 = defaults["m3"] - spot
        structure[commodity] = {
            "spot":         spot,
            "m3":           defaults["m3"],
            "m6":           defaults["m6"],
            "spread_m1_m3": round(spread_m1_m3, 2),
            "spread_m1_m6": round(defaults["m6"] - spot, 2),
            "market_type":  "contango" if spread_m1_m3 > 0 else "backwardation",
        }
    return structure


def load_crush_data() -> dict:
    """Charge la marge de crushing actuelle"""
    path = DATA_PROCESSED / "crush_history.csv"
    if not path.exists():
        return {}

    df = pd.read_csv(path, parse_dates=["date"])
    last = df.sort_values("date").iloc[-1]
    return {
        "net_crush_usd_bu":  round(float(last["net_crush_usd_bu"]), 3),
        "net_crush_usd_mt":  round(float(last["net_crush_usd_mt"]), 2),
        "crush_pctile":      round(float(last["crush_pctile"]), 1),
        "signal":            "bullish" if float(last["crush_signal"]) > 0 else
                             ("bearish" if float(last["crush_signal"]) < 0 else "neutral"),
    }


def load_weather_alerts() -> list:
    """Charge les alertes météo actives"""
    path = DATA_PROCESSED / "weather_signals.csv"
    if not path.exists():
        return []

    df = pd.read_csv(path, parse_dates=["date"])
    latest = df.sort_values("date").groupby("zone").last().reset_index()
    alerts = []

    for _, row in latest.iterrows():
        signal = int(row.get("weather_signal", 0))
        if signal != 0:
            alerts.append({
                "zone":            row["zone"],
                "signal":          "drought" if signal == 1 else "excess_water",
                "precip_anomaly":  round(float(row.get("precip_anomaly_30d", 0)), 1),
                "impact":          "bullish" if signal == 1 else "bearish",
            })
    return alerts


def load_basis_data() -> dict:
    """Charge les données de base physique"""
    path = DATA_PROCESSED / "basis_analysis.csv"
    if not path.exists():
        return {}

    df = pd.read_csv(path)
    basis = {}
    for _, row in df.iterrows():
        commodity = row["commodity"]
        if commodity not in basis:
            basis[commodity] = []
        basis[commodity].append({
            "location":    row["location"],
            "basis":       row["actual_basis"],
            "vs_ref":      row["basis_vs_ref"],
            "signal":      row["interpretation"],
        })
    return basis


def load_composite_signals() -> dict:
    """Charge les signaux composites du module 3"""
    path = DATA_PROCESSED / "signals_summary.csv"
    if not path.exists():
        return {}

    df = pd.read_csv(path)
    signals = {}
    for _, row in df.iterrows():
        signals[row["commodity"]] = {
            "composite_score": round(float(row.get("composite", 0)), 3),
            "direction":       row.get("direction", "NEUTRAL"),
            "momentum":        int(row.get("momentum", 0)),
            "cot":             int(row.get("cot", 0)),
            "weather":         int(row.get("weather", 0)),
            "bdi":             int(row.get("bdi", 0)),
        }
    return signals


def build_full_context() -> dict:
    """
    Assemble le contexte complet de tous les modules.
    C'est ce qui sera envoyé au LLM pour générer les trade ideas.
    """
    console.print("[cyan]🔄 Construction du contexte marché...[/cyan]")

    context = {
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "prices":           load_latest_prices(),
        "technical":        load_technical_signals(),
        "market_structure": load_market_structure(),
        "crush_margin":     load_crush_data(),
        "weather_alerts":   load_weather_alerts(),
        "basis":            load_basis_data(),
        "composite_signals":load_composite_signals(),
    }

    console.print("[green]✓ Contexte assemblé — "
                  f"{len(context['prices'])} commodités, "
                  f"{len(context['weather_alerts'])} alertes météo[/green]")
    return context


def context_to_text(context: dict) -> str:
    """
    Convertit le contexte JSON en texte structuré lisible par le LLM.
    Format optimisé pour maximiser la qualité des trade ideas générées.
    """
    ts = context["timestamp"]
    lines = [f"=== MARKET CONTEXT — {ts} ===\n"]

    # Prix et performance
    lines.append("## PRIX FUTURES CBOT")
    for key, p in context["prices"].items():
        chg1m = f"{p['chg_1m_pct']:+.1f}%" if p.get("chg_1m_pct") else "N/A"
        chg3m = f"{p['chg_3m_pct']:+.1f}%" if p.get("chg_3m_pct") else "N/A"
        lines.append(f"  {p['name']}: {p['current']} {p['unit']} | 1M: {chg1m} | 3M: {chg3m}")

    # Signaux techniques
    lines.append("\n## INDICATEURS TECHNIQUES")
    for commodity, tech in context["technical"].items():
        ma_str = "MA50 > MA200 (bullish)" if tech["ma50_above_ma200"] else "MA50 < MA200 (bearish)"
        lines.append(f"  {commodity.upper()}: RSI={tech['rsi']} | ROC 1M={tech['roc_1m']:+.1f}% | "
                     f"ROC 3M={tech['roc_3m']:+.1f}% | {ma_str}")
        if tech["golden_cross"]:
            lines.append(f"    ⚡ GOLDEN CROSS détecté sur {commodity}!")
        if tech["death_cross"]:
            lines.append(f"    ⚡ DEATH CROSS détecté sur {commodity}!")

    # Structure de marché
    lines.append("\n## STRUCTURE DE MARCHÉ (COURBE FORWARD)")
    for commodity, struct in context["market_structure"].items():
        lines.append(f"  {commodity.upper()}: Spot={struct['spot']} | "
                     f"M+3={struct['m3']} | Spread M1-M3={struct['spread_m1_m3']:+.1f}c | "
                     f"Structure={struct['market_type'].upper()}")

    # Crush margin
    if context["crush_margin"]:
        c = context["crush_margin"]
        lines.append(f"\n## SOYBEAN CRUSH MARGIN")
        lines.append(f"  Net Crush: ${c['net_crush_usd_bu']}/bu (${c['net_crush_usd_mt']}/MT) | "
                     f"Percentile historique: {c['crush_pctile']}% | Signal: {c['signal'].upper()}")

    # Alertes météo
    if context["weather_alerts"]:
        lines.append("\n## ALERTES MÉTÉO ACTIVES")
        for alert in context["weather_alerts"]:
            lines.append(f"  ⚠ {alert['zone']}: {alert['signal'].upper()} "
                         f"(anomalie: {alert['precip_anomaly']:+.1f}%) → Impact: {alert['impact'].upper()}")
    else:
        lines.append("\n## MÉTÉO: Aucune alerte active")

    # Signaux composites
    lines.append("\n## SIGNAUX COMPOSITES (Score: -1=très bearish, +1=très bullish)")
    for commodity, sig in context["composite_signals"].items():
        lines.append(f"  {commodity.upper()}: Score={sig['composite_score']:+.3f} | "
                     f"Direction={sig['direction']} | "
                     f"Momentum={sig['momentum']:+d} | COT={sig['cot']:+d} | "
                     f"Météo={sig['weather']:+d} | BDI={sig['bdi']:+d}")

    return "\n".join(lines)