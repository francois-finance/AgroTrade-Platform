"""
Backtest Engine : Moteur vectorisé pour tester les stratégies sur données historiques.
Approche vectorisée (pandas/numpy) — rapide et lisible.

Un backtest sérieux doit inclure :
- Coûts de transaction (slippage + commissions)
- Gestion du capital (position sizing)
- Pas de look-ahead bias (on ne regarde pas le futur)
- Walk-forward validation
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from rich.console import Console
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED

console = Console()


@dataclass
class BacktestConfig:
    """Configuration complète d'un backtest"""
    strategy_name:      str
    commodity:          str
    start_date:         str   = "2018-01-01"
    end_date:           str   = "2025-12-31"
    initial_capital:    float = 100_000.0    # $ initial
    commission_per_contract: float = 3.0     # $ par contrat aller-retour
    slippage_ticks:     int   = 1            # Ticks de slippage à l'exécution
    tick_size:          float = 0.25         # Cents/bu par tick
    contract_size:      int   = 5000         # Boisseaux par contrat CBOT
    max_position_pct:   float = 0.20         # Max 20% du capital par trade
    risk_per_trade_pct: float = 0.02         # Risk 2% du capital par trade


@dataclass
class Trade:
    """Représente un trade individuel"""
    entry_date:    str
    exit_date:     str
    direction:     int    # 1=long, -1=short
    entry_price:   float
    exit_price:    float
    contracts:     int
    pnl_gross:     float
    commission:    float
    pnl_net:       float
    holding_days:  int
    exit_reason:   str    # 'signal', 'stop', 'target', 'end_of_test'


class BacktestEngine:
    """
    Moteur de backtest vectorisé.
    Prend une stratégie (DataFrame avec colonne 'signal') et simule les trades.
    """

    def __init__(self, config: BacktestConfig):
        self.config  = config
        self.trades  = []
        self.equity  = []

    def load_price_data(self) -> pd.DataFrame:
        """Charge et prépare les données de prix"""
        path = DATA_RAW / f"{self.config.commodity}_futures.csv"
        if not path.exists():
            raise FileNotFoundError(f"Données manquantes : {path}")

        df = pd.read_csv(path, index_col="date", parse_dates=True)
        df = df[["open", "high", "low", "close", "volume"]].copy()
        df = df.loc[self.config.start_date:self.config.end_date]
        df = df.dropna()
        return df

    def compute_position_size(self, capital: float, price: float,
                               stop_distance: float) -> int:
        """
        Position sizing basé sur le risque fixe (Fixed Fractional).
        Nombre de contrats = (Capital × Risk%) / (Stop distance × Contract size)
        """
        if stop_distance <= 0:
            return 1

        risk_amount   = capital * self.config.risk_per_trade_pct
        dollar_per_contract = (stop_distance / 100) * self.config.contract_size
        contracts = int(risk_amount / dollar_per_contract)

        # Cap sur la taille max
        max_contracts = int(
            (capital * self.config.max_position_pct) /
            (price / 100 * self.config.contract_size)
        )
        return max(1, min(contracts, max_contracts))

    def run(self, signals_df: pd.DataFrame) -> dict:
        """
        Lance le backtest sur un DataFrame contenant les colonnes :
        - 'close'        : prix de clôture
        - 'signal'       : 1 (long), -1 (short), 0 (flat)
        - 'stop_price'   : niveau de stop (optionnel)
        - 'target_price' : niveau de target (optionnel)

        Retourne un dict avec equity curve et liste des trades.
        """
        df = signals_df.copy().dropna(subset=["close", "signal"])

        capital      = self.config.initial_capital
        position     = 0       # 0=flat, 1=long, -1=short
        entry_price  = 0.0
        entry_date   = None
        contracts    = 0
        equity_curve = [capital]
        dates        = [df.index[0]]

        slippage_cost = self.config.slippage_ticks * self.config.tick_size

        for i in range(1, len(df)):
            row       = df.iloc[i]
            prev_row  = df.iloc[i - 1]
            price     = row["close"]
            signal    = int(prev_row["signal"])  # Signal du jour précédent → exécution aujourd'hui
            stop      = prev_row.get("stop_price", np.nan)
            target    = prev_row.get("target_price", np.nan)

            exit_triggered = False
            exit_reason    = ""
            exit_price     = price

            # ── Vérification stop/target si en position ──────────────────
            if position != 0:
                if position == 1:  # Long
                    if not np.isnan(stop) and row["low"] <= stop:
                        exit_triggered = True
                        exit_price     = stop
                        exit_reason    = "stop"
                    elif not np.isnan(target) and row["high"] >= target:
                        exit_triggered = True
                        exit_price     = target
                        exit_reason    = "target"
                elif position == -1:  # Short
                    if not np.isnan(stop) and row["high"] >= stop:
                        exit_triggered = True
                        exit_price     = stop
                        exit_reason    = "stop"
                    elif not np.isnan(target) and row["low"] <= target:
                        exit_triggered = True
                        exit_price     = target
                        exit_reason    = "target"

            # ── Changement de signal → sortie + entrée ────────────────────
            if not exit_triggered and position != 0 and signal != position and signal != 0:
                exit_triggered = True
                exit_reason    = "signal_reverse"
            elif not exit_triggered and position != 0 and signal == 0:
                exit_triggered = True
                exit_reason    = "signal_exit"

            # ── Enregistrement du trade sortant ──────────────────────────
            if exit_triggered and position != 0:
                exec_exit   = exit_price + position * slippage_cost
                pnl_cents   = (exec_exit - entry_price) * position
                pnl_dollars = (pnl_cents / 100) * self.config.contract_size * contracts
                commission  = self.config.commission_per_contract * contracts
                pnl_net     = pnl_dollars - commission

                capital += pnl_net
                holding  = (df.index[i] - entry_date).days

                self.trades.append(Trade(
                    entry_date=str(entry_date.date()),
                    exit_date=str(df.index[i].date()),
                    direction=position,
                    entry_price=entry_price,
                    exit_price=exec_exit,
                    contracts=contracts,
                    pnl_gross=round(pnl_dollars, 2),
                    commission=round(commission, 2),
                    pnl_net=round(pnl_net, 2),
                    holding_days=holding,
                    exit_reason=exit_reason,
                ))
                position = 0

            # ── Entrée en position ────────────────────────────────────────
            if position == 0 and signal != 0:
                stop_dist   = abs(price - stop) if not np.isnan(stop) else price * 0.02
                contracts   = self.compute_position_size(capital, price, stop_dist)
                entry_price = price + signal * slippage_cost
                entry_date  = df.index[i]
                position    = signal

            equity_curve.append(capital)
            dates.append(df.index[i])

        # Clôture position finale si ouverte
        if position != 0:
            last_price = df["close"].iloc[-1]
            pnl_cents  = (last_price - entry_price) * position
            pnl_net    = (pnl_cents / 100) * self.config.contract_size * contracts
            capital   += pnl_net
            self.trades.append(Trade(
                entry_date=str(entry_date.date()),
                exit_date=str(df.index[-1].date()),
                direction=position,
                entry_price=entry_price,
                exit_price=last_price,
                contracts=contracts,
                pnl_gross=round(pnl_net, 2),
                commission=0,
                pnl_net=round(pnl_net, 2),
                holding_days=(df.index[-1] - entry_date).days,
                exit_reason="end_of_test",
            ))

        equity_df = pd.DataFrame({"date": dates, "equity": equity_curve})
        equity_df = equity_df.set_index("date")

        return {
            "config":       self.config,
            "equity_curve": equity_df,
            "trades":       self.trades,
            "final_capital":capital,
        }