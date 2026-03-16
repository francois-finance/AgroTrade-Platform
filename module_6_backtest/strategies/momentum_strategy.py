"""
Stratégie 1 : Momentum / Trend Following
Logique : Achète quand le prix casse au-dessus de sa MA50 avec RSI en zone neutre.
          Vend quand il passe sous la MA50.
C'est la stratégie de base du trend following — très utilisée sur les commodités.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW
from module_6_backtest.engine.backtest_engine import BacktestConfig, BacktestEngine


def prepare_signals(commodity: str, start: str, end: str) -> pd.DataFrame:
    """Prépare les signaux momentum"""
    path = DATA_RAW / f"{commodity}_futures.csv"
    df = pd.read_csv(path, index_col="date", parse_dates=True)
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    df = df.loc[start:end]

    # Indicateurs
    df["ma20"]  = df["close"].rolling(20).mean()
    df["ma50"]  = df["close"].rolling(50).mean()
    df["ma200"] = df["close"].rolling(200).mean()

    # RSI
    delta    = df["close"].diff()
    gain     = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss     = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    # ROC 1 mois
    df["roc_1m"] = df["close"].pct_change(21) * 100

    # ── Génération des signaux ────────────────────────────────────────────
    # Long  : MA50 > MA200 (golden cross actif) + RSI < 70 + momentum positif
    # Short : MA50 < MA200 (death cross actif)  + RSI > 30 + momentum négatif
    # Flat  : Sinon

    df["signal"] = 0
    long_cond  = (
        (df["ma50"] > df["ma200"]) &
        (df["rsi"] < 70) &
        (df["roc_1m"] > 0) &
        (df["close"] > df["ma50"])
    )
    short_cond = (
        (df["ma50"] < df["ma200"]) &
        (df["rsi"] > 30) &
        (df["roc_1m"] < 0) &
        (df["close"] < df["ma50"])
    )

    df.loc[long_cond,  "signal"] =  1
    df.loc[short_cond, "signal"] = -1

    # Stops et targets dynamiques
    atr = (df["high"] - df["low"]).rolling(14).mean()  # ATR simplifié
    df.loc[df["signal"] ==  1, "stop_price"]   = df["close"] - 2 * atr
    df.loc[df["signal"] ==  1, "target_price"] = df["close"] + 3 * atr
    df.loc[df["signal"] == -1, "stop_price"]   = df["close"] + 2 * atr
    df.loc[df["signal"] == -1, "target_price"] = df["close"] - 3 * atr

    return df.dropna(subset=["ma200"])


def run_momentum_backtest(commodity: str = "wheat") -> dict:
    config = BacktestConfig(
        strategy_name="Momentum MA50/MA200 + RSI Filter",
        commodity=commodity,
        start_date="2018-01-01",
        end_date="2025-12-31",
        initial_capital=100_000,
        risk_per_trade_pct=0.02,
    )
    signals = prepare_signals(commodity, config.start_date, config.end_date)
    engine  = BacktestEngine(config)
    return engine.run(signals)