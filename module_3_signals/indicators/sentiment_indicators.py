"""
Indicators : Sentiment de marché enrichi
Sources    : COT Report CFTC + Baltic Dry Index + News sentiment proxy
"""

import pandas as pd
import numpy as np
from rich.console import Console
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED

console = Console()


def load_cot_data() -> pd.DataFrame:
    path = DATA_RAW / "cot_agricultural.csv"
    if not path.exists():
        raise FileNotFoundError("COT data manquante")
    return pd.read_csv(path, low_memory=False)


def compute_cot_signals(save: bool = True) -> pd.DataFrame:
    """
    Analyse COT enrichie :
    - Net Speculative Length (NSL) absolu
    - NSL percentile glissant 3 ans
    - Commercials net (les vrais acteurs physiques)
    - Ratio long/short spéculatifs
    - Divergence spec vs commercials (signal contrarian fort)
    """
    try:
        df = load_cot_data()
    except FileNotFoundError:
        console.print("[yellow]⚠ COT manquant — données synthétiques[/yellow]")
        return _synthetic_cot_signals()

    date_col = "As_of_Date_In_Form_YYMMDD"
    if date_col not in df.columns:
        return _synthetic_cot_signals()

    df["date"] = pd.to_datetime(
        df[date_col].astype(str), format="%y%m%d", errors="coerce"
    )
    df = df.dropna(subset=["date"]).sort_values("date")

    commodity_filters = {
        "wheat":   "WHEAT",
        "corn":    "CORN",
        "soybean": "SOYBEAN",
    }

    results = []
    for commodity, keyword in commodity_filters.items():
        mask = df["Market_and_Exchange_Names"].str.contains(
            keyword, na=False, case=False
        )
        sub = df[mask].copy()
        if sub.empty:
            continue

        # Positions nettes
        sub["net_spec"]  = (
            sub["NonComm_Positions_Long_All"] - sub["NonComm_Positions_Short_All"]
        )
        sub["net_comm"]  = (
            sub["Comm_Positions_Long_All"] - sub["Comm_Positions_Short_All"]
        )
        sub["open_interest"] = sub.get("Open_Interest_All", pd.Series(0, index=sub.index))

        # Percentile glissant 3 ans (156 semaines)
        sub["nsl_pctile"] = (
            sub["net_spec"].rolling(156, min_periods=52).rank(pct=True) * 100
        )

        # Ratio long/(long+short) spéculatifs
        total_spec = (
            sub["NonComm_Positions_Long_All"] + sub["NonComm_Positions_Short_All"]
        )
        sub["spec_long_ratio"] = (
            sub["NonComm_Positions_Long_All"] / total_spec.replace(0, np.nan)
        )

        # Divergence : quand spécs sont longs ET commercials sont nets courts
        # → signal contrarian bearish fort
        sub["divergence"] = np.where(
            (sub["net_spec"] > 0) & (sub["net_comm"] < 0), -1,
            np.where((sub["net_spec"] < 0) & (sub["net_comm"] > 0), 1, 0)
        )

        # Signal COT
        sub["cot_signal"] = 0
        sub.loc[sub["nsl_pctile"] > 80, "cot_signal"] = -1   # Spécs trop longs
        sub.loc[sub["nsl_pctile"] < 20, "cot_signal"] =  1   # Spécs très courts

        # Signal divergence (plus fort — override si divergence forte)
        sub.loc[(sub["divergence"] == -1) & (sub["nsl_pctile"] > 70), "cot_signal"] = -1
        sub.loc[(sub["divergence"] ==  1) & (sub["nsl_pctile"] < 30), "cot_signal"] =  1

        sub["commodity"] = commodity
        results.append(sub[[
            "date", "commodity",
            "net_spec", "net_comm", "open_interest",
            "nsl_pctile", "spec_long_ratio",
            "divergence", "cot_signal"
        ]])

    if not results:
        return _synthetic_cot_signals()

    final = pd.concat(results, ignore_index=True)

    if save:
        path = DATA_PROCESSED / "cot_signals.csv"
        final.to_csv(path, index=False)
        console.print(f"[blue]💾 COT signals sauvegardés[/blue]")

    return final


def _synthetic_cot_signals() -> pd.DataFrame:
    """Données synthétiques réalistes si COT non disponible"""
    np.random.seed(42)
    dates = pd.date_range("2022-01-01", periods=104, freq="W")
    rows  = []
    for commodity in ["wheat", "corn", "soybean"]:
        base_net = {"wheat": 30000, "corn": 50000, "soybean": 40000}[commodity]
        net_spec  = base_net + np.cumsum(np.random.normal(0, 5000, len(dates)))
        net_comm  = -net_spec * 0.85 + np.random.normal(0, 3000, len(dates))
        pctile    = pd.Series(net_spec).rank(pct=True) * 100
        signal    = pd.Series(0, index=range(len(dates)))
        signal[pctile > 80] = -1
        signal[pctile < 20] =  1

        for i, d in enumerate(dates):
            rows.append({
                "date":            d,
                "commodity":       commodity,
                "net_spec":        round(net_spec[i], 0),
                "net_comm":        round(net_comm[i], 0),
                "open_interest":   abs(round(net_spec[i] * 2.5, 0)),
                "nsl_pctile":      round(float(pctile.iloc[i]), 1),
                "spec_long_ratio": round(0.5 + net_spec[i]/200000, 3),
                "divergence":      int(np.sign(-net_spec[i])),
                "cot_signal":      int(signal.iloc[i]),
            })

    console.print("[dim]  (signaux COT synthétiques enrichis)[/dim]")
    return pd.DataFrame(rows)


def compute_bdi_signals(save: bool = True) -> pd.DataFrame:
    """
    Signaux BDI enrichis :
    - Trend (MA20 vs MA50)
    - ROC 1 mois et 3 mois
    - Régime de fret (low/normal/high/extreme)
    - Signal directionnel sur les grains
    """
    path = DATA_RAW / "baltic_bdi.csv"
    if not path.exists():
        console.print("[yellow]⚠ BDI manquant — données synthétiques[/yellow]")
        return _synthetic_bdi_signals()

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["bdi_ma20"] = df["close"].rolling(20).mean()
    df["bdi_ma50"] = df["close"].rolling(50).mean()
    df["bdi_roc1m"] = df["close"].pct_change(20) * 100
    df["bdi_roc3m"] = df["close"].pct_change(60) * 100

    # Percentile 3 ans pour classifier le régime
    df["bdi_pctile"] = df["close"].rolling(252*3, min_periods=100).rank(pct=True) * 100

    df["bdi_regime"] = pd.cut(
        df["bdi_pctile"],
        bins=[0, 20, 40, 60, 80, 100],
        labels=["very_low", "low", "normal", "high", "very_high"]
    )

    # Signal
    df["bdi_signal"] = 0
    df.loc[df["bdi_roc1m"] >  20, "bdi_signal"] =  1
    df.loc[df["bdi_roc1m"] < -20, "bdi_signal"] = -1
    # Renforcement si tendance confirmée sur 3 mois
    df.loc[(df["bdi_signal"] ==  1) & (df["bdi_roc3m"] >  15), "bdi_signal"] =  1
    df.loc[(df["bdi_signal"] == -1) & (df["bdi_roc3m"] < -15), "bdi_signal"] = -1

    if save:
        path_out = DATA_PROCESSED / "bdi_signals.csv"
        df.to_csv(path_out, index=False)

    return df


def _synthetic_bdi_signals() -> pd.DataFrame:
    np.random.seed(1)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq="B")
    bdi   = 1800 + np.cumsum(np.random.normal(0, 40, len(dates)))
    df    = pd.DataFrame({"date": dates, "close": bdi})
    df["bdi_ma50"]   = df["close"].rolling(50).mean()
    df["bdi_roc1m"]  = df["close"].pct_change(20) * 100
    df["bdi_roc3m"]  = df["close"].pct_change(60) * 100
    df["bdi_pctile"] = df["close"].rank(pct=True) * 100
    df["bdi_regime"] = "normal"
    df["bdi_signal"] = 0
    df.loc[df["bdi_roc1m"] >  20, "bdi_signal"] =  1
    df.loc[df["bdi_roc1m"] < -20, "bdi_signal"] = -1
    console.print("[dim]  (signaux BDI synthétiques)[/dim]")
    return df