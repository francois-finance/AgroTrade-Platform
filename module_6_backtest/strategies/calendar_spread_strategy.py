"""
Stratégie 3 : Calendar Spread (Old Crop / New Crop)
Logique : Trade le spread entre contrat proche et contrat lointain.
          Quand le spread dépasse le full carry → short spread (trop cher)
          Quand le spread est en backwardation → long spread (marché tendu)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW
from module_6_backtest.engine.backtest_engine import BacktestConfig, BacktestEngine


def prepare_calendar_signals(commodity: str, start: str, end: str) -> pd.DataFrame:
    """
    Simule un calendar spread en utilisant le proxy :
    Spread = Prix actuel vs Prix décalé de 3 mois (approximation)
    """
    path = DATA_RAW / f"{commodity}_futures.csv"
    df   = pd.read_csv(path, index_col="date", parse_dates=True)
    df   = df[["open", "high", "low", "close"]].dropna()
    df   = df.loc[start:end]

    # Approximation du M+3 : prix décalé de 63 jours trading
    df["close_m3"] = df["close"].shift(-63)   # Prix futur (approximation)
    df["spread"]   = df["close_m3"] - df["close"]

    # Full carry théorique pour 3 mois (approximation : ~0.8% par mois)
    df["theoretical_carry_3m"] = df["close"] * 0.008 * 3

    # Ratio spread observé / full carry
    df["carry_ratio"] = df["spread"] / df["theoretical_carry_3m"].replace(0, np.nan)

    # Stats du spread
    df["spread_ma"]  = df["spread"].rolling(60).mean()
    df["spread_std"] = df["spread"].rolling(60).std()
    df["spread_z"]   = (df["spread"] - df["spread_ma"]) / df["spread_std"].replace(0, np.nan)

    # Signaux
    df["signal"] = 0
    # Spread trop grand (>full carry) → marché surévalué à terme → short futures proches
    df.loc[df["spread_z"] > 1.5,  "signal"] = -1
    # Backwardation (spread négatif) → marché physique tendu → long futures proches
    df.loc[df["spread_z"] < -1.5, "signal"] =  1

    # Stops basés sur z-score
    atr = (df["high"] - df["low"]).rolling(14).mean()
    df.loc[df["signal"] ==  1, "stop_price"]   = df["close"] - 1.5 * atr
    df.loc[df["signal"] == -1, "stop_price"]   = df["close"] + 1.5 * atr

    return df.dropna(subset=["spread_ma"])


def run_calendar_backtest(commodity: str = "wheat") -> dict:
    config = BacktestConfig(
        strategy_name="Calendar Spread Old/New Crop",
        commodity=commodity,
        start_date="2018-01-01",
        end_date="2025-12-31",
        initial_capital=100_000,
        risk_per_trade_pct=0.015,
    )
    signals = prepare_calendar_signals(commodity, config.start_date, config.end_date)
    engine  = BacktestEngine(config)
    return engine.run(signals)