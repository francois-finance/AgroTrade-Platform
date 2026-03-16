"""
Stratégie 2 : Crush Spread Trading
Logique : Long crush quand la marge est anormalement basse (mean-reversion)
          Short crush quand la marge est anormalement haute
Le crush spread est moins volatile que les prix directs → stratégie plus stable.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW
from module_6_backtest.engine.backtest_engine import BacktestConfig, BacktestEngine


def compute_crush_series() -> pd.Series:
    """Calcule la série historique du crush spread net"""
    dfs = {}
    for c in ["soybean", "soyoil", "soymeal"]:
        path = DATA_RAW / f"{c}_futures.csv"
        if path.exists():
            dfs[c] = pd.read_csv(path, index_col="date", parse_dates=True)["close"]

    if len(dfs) < 3:
        return pd.Series()

    combined = pd.DataFrame(dfs).dropna()
    combined.columns = ["soybean", "soyoil", "soymeal"]

    # Gross crush = valeur huile + valeur tourteau - coût soja
    oil_value  = (combined["soyoil"]  * 11) / 100          # $/bu
    meal_value = (combined["soymeal"] / 2000) * 44          # $/bu
    soy_cost   = combined["soybean"] / 100                  # $/bu

    crush = oil_value + meal_value - soy_cost - 0.30       # Net of processing
    return crush


def prepare_crush_signals(start: str, end: str) -> pd.DataFrame:
    """Prépare les signaux de mean-reversion sur le crush"""
    crush = compute_crush_series()
    if crush.empty:
        return pd.DataFrame()

    # Charge le soja comme proxy de prix pour le backtest
    soy_path = DATA_RAW / "soybean_futures.csv"
    price_df  = pd.read_csv(soy_path, index_col="date", parse_dates=True)
    price_df  = price_df[["open", "high", "low", "close"]].dropna()

    df = price_df.join(crush.rename("crush"), how="inner")
    df = df.loc[start:end]

    # Bandes de Bollinger sur le crush (mean-reversion)
    df["crush_ma"]    = df["crush"].rolling(60).mean()
    df["crush_std"]   = df["crush"].rolling(60).std()
    df["crush_upper"] = df["crush_ma"] + 1.5 * df["crush_std"]
    df["crush_lower"] = df["crush_ma"] - 1.5 * df["crush_std"]

    # Percentile glissant 1 an
    df["crush_pctile"] = df["crush"].rolling(252).rank(pct=True) * 100

    # Signaux mean-reversion
    df["signal"] = 0
    # Crush très bas → long soja (crushers vont augmenter la demande)
    df.loc[df["crush_pctile"] < 20, "signal"] =  1
    # Crush très haut → short soja (crushers vont réduire la demande)
    df.loc[df["crush_pctile"] > 80, "signal"] = -1

    # Stops
    atr = (df["high"] - df["low"]).rolling(14).mean()
    df.loc[df["signal"] ==  1, "stop_price"]   = df["close"] - 2 * atr
    df.loc[df["signal"] == -1, "stop_price"]   = df["close"] + 2 * atr

    return df.dropna(subset=["crush_ma"])


def run_crush_backtest() -> dict:
    config = BacktestConfig(
        strategy_name="Crush Spread Mean-Reversion",
        commodity="soybean",
        start_date="2018-01-01",
        end_date="2025-12-31",
        initial_capital=100_000,
        risk_per_trade_pct=0.015,
    )
    signals = prepare_crush_signals(config.start_date, config.end_date)
    engine  = BacktestEngine(config)
    return engine.run(signals)