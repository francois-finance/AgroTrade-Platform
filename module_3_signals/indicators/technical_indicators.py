"""
Indicators : Signaux techniques sur prix futures CBOT
Signaux    : Momentum, MA Cross, RSI, Bollinger Bands, Calendar Spreads
"""

import pandas as pd
import numpy as np
from rich.console import Console
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED

console = Console()


def load_futures_data(commodity: str) -> pd.DataFrame:
    """Charge les données futures depuis data/raw/"""
    path = DATA_RAW / f"{commodity}_futures.csv"
    if not path.exists():
        raise FileNotFoundError(f"Fichier manquant : {path}. Lance d'abord run_pipeline.py")
    df = pd.read_csv(path, index_col="date", parse_dates=True)
    df = df.sort_index()
    return df


def compute_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les moyennes mobiles clés.
    MA20  = court terme (1 mois)
    MA50  = moyen terme (2.5 mois)
    MA200 = long terme (10 mois) — la référence institutionnelle
    """
    df = df.copy()
    df["ma20"]  = df["close"].rolling(20).mean()
    df["ma50"]  = df["close"].rolling(50).mean()
    df["ma200"] = df["close"].rolling(200).mean()

    # Golden Cross / Death Cross
    df["ma50_above_ma200"] = (df["ma50"] > df["ma200"]).astype(int)
    df["golden_cross"] = (
        (df["ma50_above_ma200"] == 1) &
        (df["ma50_above_ma200"].shift(1) == 0)
    ).astype(int)
    df["death_cross"] = (
        (df["ma50_above_ma200"] == 0) &
        (df["ma50_above_ma200"].shift(1) == 1)
    ).astype(int)

    return df


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    RSI (Relative Strength Index).
    > 70 = suracheté (signal baissier potentiel)
    < 30 = survendu  (signal haussier potentiel)
    """
    df = df.copy()
    delta = df["close"].diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # Signal RSI
    df["rsi_signal"] = 0
    df.loc[df["rsi"] < 30, "rsi_signal"] =  1  # Survendu  → bullish
    df.loc[df["rsi"] > 70, "rsi_signal"] = -1  # Suracheté → bearish

    return df


def compute_bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    """
    Bollinger Bands — détecte les extensions de prix.
    Prix > upper band = extension haussière (potentiel retour)
    Prix < lower band = extension baissière (potentiel rebond)
    """
    df = df.copy()
    rolling = df["close"].rolling(period)
    df["bb_mid"]   = rolling.mean()
    df["bb_upper"] = df["bb_mid"] + std * rolling.std()
    df["bb_lower"] = df["bb_mid"] - std * rolling.std()
    df["bb_width"]  = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]  # Volatilité normalisée

    # Position dans les bandes (0 = lower, 1 = upper)
    df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    df["bb_signal"] = 0
    df.loc[df["close"] > df["bb_upper"], "bb_signal"] = -1  # Extension haute → bearish
    df.loc[df["close"] < df["bb_lower"], "bb_signal"] =  1  # Extension basse → bullish

    return df


def compute_momentum(df: pd.DataFrame) -> pd.DataFrame:
    """
    Momentum multi-périodes.
    ROC (Rate of Change) sur 1, 3, 6 et 12 mois.
    Très utilisé en trend following sur les commodités.
    """
    df = df.copy()
    for days, label in [(21, "1m"), (63, "3m"), (126, "6m"), (252, "12m")]:
        df[f"roc_{label}"] = df["close"].pct_change(days) * 100

    # Signal momentum composite (moyenne des 4 ROC normalisés)
    roc_cols = ["roc_1m", "roc_3m", "roc_6m", "roc_12m"]
    df["momentum_score"] = df[roc_cols].mean(axis=1)

    df["momentum_signal"] = 0
    df.loc[df["momentum_score"] > 5,  "momentum_signal"] =  1  # Trend haussier
    df.loc[df["momentum_score"] < -5, "momentum_signal"] = -1  # Trend baissier

    return df


def compute_seasonality(df: pd.DataFrame, commodity: str) -> pd.DataFrame:
    """
    Calcule la saisonnalité historique.
    Compare le prix actuel à la moyenne historique du même mois.
    Très pertinent en agri (planting/harvest cycles).
    """
    df = df.copy()

    # Moyenne historique par mois (sur toutes les années disponibles)
    df["month"] = df.index.month
    monthly_avg = df.groupby("month")["close"].mean().rename("seasonal_avg")
    df = df.join(monthly_avg, on="month")

    # Déviation par rapport à la saisonnalité
    df["seasonal_deviation"] = (df["close"] - df["seasonal_avg"]) / df["seasonal_avg"] * 100

    # Mois typiquement haussiers/baissiers selon la commodité
    seasonal_patterns = {
        "wheat":   {"bullish_months": [5, 6],      "bearish_months": [7, 8, 9]},   # Pre-harvest tension / post-harvest pressure
        "corn":    {"bullish_months": [6, 7],      "bearish_months": [9, 10, 11]}, # Pollination stress / harvest
        "soybean": {"bullish_months": [7, 8],      "bearish_months": [9, 10, 11]}, # Pod fill stress / harvest
    }

    pattern = seasonal_patterns.get(commodity, {"bullish_months": [], "bearish_months": []})
    df["seasonal_signal"] = 0
    df.loc[df["month"].isin(pattern["bullish_months"]),  "seasonal_signal"] =  1
    df.loc[df["month"].isin(pattern["bearish_months"]), "seasonal_signal"] = -1

    return df


def run_all_technical(commodity: str, save: bool = True) -> pd.DataFrame:
    """Lance tous les indicateurs techniques sur une commodité"""
    console.print(f"[cyan]📊 Calcul indicateurs techniques : {commodity}...[/cyan]")

    df = load_futures_data(commodity)
    df = compute_moving_averages(df)
    df = compute_rsi(df)
    df = compute_bollinger_bands(df)
    df = compute_momentum(df)
    df = compute_seasonality(df, commodity)

    if save:
        path = DATA_PROCESSED / f"{commodity}_technical.csv"
        df.to_csv(path)
        console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

    console.print(f"[green]✓ {len(df)} jours d'indicateurs pour {commodity}[/green]")
    return df


if __name__ == "__main__":
    for c in ["wheat", "corn", "soybean"]:
        run_all_technical(c, save=True)