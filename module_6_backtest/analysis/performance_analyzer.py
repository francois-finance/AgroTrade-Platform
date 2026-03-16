"""
Performance Analyzer : Calcule toutes les métriques de performance d'un backtest.
Métriques : Sharpe, Sortino, Max Drawdown, Calmar, Win Rate, Profit Factor...
"""

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_PROCESSED

console = Console()


def compute_metrics(backtest_result: dict) -> dict:
    """Calcule toutes les métriques de performance"""
    equity    = backtest_result["equity_curve"]["equity"]
    trades    = backtest_result["trades"]
    config    = backtest_result["config"]
    initial   = config.initial_capital
    final     = backtest_result["final_capital"]

    # ── Returns ───────────────────────────────────────────────────────────
    returns       = equity.pct_change().dropna()
    total_return  = (final / initial - 1) * 100
    n_years       = len(equity) / 252
    annual_return = ((final / initial) ** (1 / max(n_years, 0.1)) - 1) * 100

    # ── Sharpe Ratio ──────────────────────────────────────────────────────
    rf_daily   = 0.05 / 252   # Risk-free rate annuel 5%
    excess_ret = returns - rf_daily
    sharpe     = (excess_ret.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

    # ── Sortino Ratio ─────────────────────────────────────────────────────
    neg_ret    = returns[returns < 0]
    downside   = neg_ret.std() * np.sqrt(252) if len(neg_ret) > 0 else 1e-9
    sortino    = (annual_return / 100 - 0.05) / downside if downside > 0 else 0

    # ── Max Drawdown ──────────────────────────────────────────────────────
    roll_max   = equity.cummax()
    drawdown   = (equity - roll_max) / roll_max * 100
    max_dd     = drawdown.min()

    # Durée max drawdown
    in_dd      = drawdown < 0
    dd_periods = []
    start_dd   = None
    for i, (d, v) in enumerate(in_dd.items()):
        if v and start_dd is None:
            start_dd = i
        elif not v and start_dd is not None:
            dd_periods.append(i - start_dd)
            start_dd = None
    max_dd_duration = max(dd_periods) if dd_periods else 0

    # ── Calmar Ratio ──────────────────────────────────────────────────────
    calmar = (annual_return / abs(max_dd)) if max_dd != 0 else 0

    # ── Trade Statistics ──────────────────────────────────────────────────
    if trades:
        trade_df    = pd.DataFrame([t.__dict__ for t in trades])
        nb_trades   = len(trade_df)
        winners     = trade_df[trade_df["pnl_net"] > 0]
        losers      = trade_df[trade_df["pnl_net"] <= 0]
        win_rate    = len(winners) / nb_trades * 100 if nb_trades > 0 else 0

        avg_win     = winners["pnl_net"].mean() if len(winners) > 0 else 0
        avg_loss    = abs(losers["pnl_net"].mean()) if len(losers) > 0 else 1e-9
        profit_factor = (winners["pnl_net"].sum() / abs(losers["pnl_net"].sum())
                         if abs(losers["pnl_net"].sum()) > 0 else 0)

        avg_holding  = trade_df["holding_days"].mean()
        best_trade   = trade_df["pnl_net"].max()
        worst_trade  = trade_df["pnl_net"].min()

        # Exits par type
        exit_counts  = trade_df["exit_reason"].value_counts().to_dict()
    else:
        nb_trades = win_rate = avg_win = avg_loss = profit_factor = 0
        avg_holding = best_trade = worst_trade = 0
        exit_counts = {}
        trade_df    = pd.DataFrame()

    return {
        "strategy":          config.strategy_name,
        "commodity":         config.commodity,
        "start_date":        config.start_date,
        "end_date":          config.end_date,
        "initial_capital":   initial,
        "final_capital":     round(final, 2),
        "total_return_pct":  round(total_return, 2),
        "annual_return_pct": round(annual_return, 2),
        "sharpe_ratio":      round(sharpe, 3),
        "sortino_ratio":     round(sortino, 3),
        "max_drawdown_pct":  round(max_dd, 2),
        "max_dd_duration_days": max_dd_duration,
        "calmar_ratio":      round(calmar, 3),
        "nb_trades":         nb_trades,
        "win_rate_pct":      round(win_rate, 1),
        "profit_factor":     round(profit_factor, 3),
        "avg_win_usd":       round(avg_win, 2),
        "avg_loss_usd":      round(avg_loss, 2),
        "reward_risk_ratio": round(avg_win / avg_loss, 2) if avg_loss > 0 else 0,
        "avg_holding_days":  round(avg_holding, 1),
        "best_trade_usd":    round(best_trade, 2),
        "worst_trade_usd":   round(worst_trade, 2),
        "exit_breakdown":    exit_counts,
        "equity_curve":      backtest_result["equity_curve"],
        "trade_df":          trade_df,
    }


def print_performance_report(metrics: dict):
    """Affiche le rapport de performance complet"""

    # Score global
    sharpe   = metrics["sharpe_ratio"]
    score    = "🟢 EXCELLENT" if sharpe > 1.5 else (
               "🟡 BON"       if sharpe > 0.8 else (
               "🟠 MOYEN"     if sharpe > 0.3 else
               "🔴 FAIBLE"))

    console.print(Panel(
        f"[bold]{metrics['strategy']}[/bold] — {metrics['commodity'].upper()}\n"
        f"{metrics['start_date']} → {metrics['end_date']}\n"
        f"Score : {score}",
        title="📈 Backtest Performance Report",
        border_style="cyan"
    ))

    # Métriques de rendement
    ret_table = Table(title="💰 Rendement", show_header=True)
    ret_table.add_column("Métrique",        style="cyan",   width=30)
    ret_table.add_column("Valeur",          style="bold",   width=20)
    ret_table.add_column("Benchmark",       style="dim",    width=20)

    color_tr  = "green" if metrics["total_return_pct"] > 0 else "red"
    color_ar  = "green" if metrics["annual_return_pct"] > 5 else "red"

    ret_table.add_row("Capital initial",    f"${metrics['initial_capital']:,.0f}",     "—")
    ret_table.add_row("Capital final",      f"${metrics['final_capital']:,.0f}",        "—")
    ret_table.add_row("Rendement total",    f"[{color_tr}]{metrics['total_return_pct']:+.1f}%[/{color_tr}]", "> 0%")
    ret_table.add_row("Rendement annuel",   f"[{color_ar}]{metrics['annual_return_pct']:+.1f}%[/{color_ar}]", "> 8%")
    console.print(ret_table)

    # Métriques de risque
    risk_table = Table(title="⚠️  Risque", show_header=True)
    risk_table.add_column("Métrique",       style="cyan",   width=30)
    risk_table.add_column("Valeur",         style="bold",   width=20)
    risk_table.add_column("Benchmark",      style="dim",    width=20)

    color_sh  = "green" if sharpe > 1.0 else ("yellow" if sharpe > 0.5 else "red")
    color_dd  = "green" if metrics["max_drawdown_pct"] > -15 else (
                "yellow" if metrics["max_drawdown_pct"] > -25 else "red")

    risk_table.add_row("Sharpe Ratio",      f"[{color_sh}]{metrics['sharpe_ratio']:.3f}[/{color_sh}]", "> 1.0")
    risk_table.add_row("Sortino Ratio",     f"{metrics['sortino_ratio']:.3f}",                          "> 1.5")
    risk_table.add_row("Max Drawdown",      f"[{color_dd}]{metrics['max_drawdown_pct']:.1f}%[/{color_dd}]", "> -20%")
    risk_table.add_row("Durée max DD",      f"{metrics['max_dd_duration_days']} jours",                 "—")
    risk_table.add_row("Calmar Ratio",      f"{metrics['calmar_ratio']:.3f}",                           "> 0.5")
    console.print(risk_table)

    # Statistiques trades
    trade_table = Table(title="🎯 Statistiques Trades", show_header=True)
    trade_table.add_column("Métrique",      style="cyan",   width=30)
    trade_table.add_column("Valeur",        style="bold",   width=20)
    trade_table.add_column("Benchmark",     style="dim",    width=20)

    color_wr  = "green" if metrics["win_rate_pct"] > 50 else "red"
    color_pf  = "green" if metrics["profit_factor"] > 1.5 else (
                "yellow" if metrics["profit_factor"] > 1.0 else "red")

    trade_table.add_row("Nombre de trades", str(metrics["nb_trades"]),                                   "—")
    trade_table.add_row("Win Rate",         f"[{color_wr}]{metrics['win_rate_pct']:.1f}%[/{color_wr}]", "> 50%")
    trade_table.add_row("Profit Factor",    f"[{color_pf}]{metrics['profit_factor']:.3f}[/{color_pf}]", "> 1.5")
    trade_table.add_row("Avg Win",          f"${metrics['avg_win_usd']:,.0f}",                           "—")
    trade_table.add_row("Avg Loss",         f"${metrics['avg_loss_usd']:,.0f}",                          "—")
    trade_table.add_row("Reward/Risk",      f"{metrics['reward_risk_ratio']:.2f}x",                      "> 1.5x")
    trade_table.add_row("Durée moyenne",    f"{metrics['avg_holding_days']:.0f} jours",                  "—")
    trade_table.add_row("Meilleur trade",   f"${metrics['best_trade_usd']:,.0f}",                        "—")
    trade_table.add_row("Pire trade",       f"${metrics['worst_trade_usd']:,.0f}",                       "—")
    console.print(trade_table)

    # Exit breakdown
    if metrics["exit_breakdown"]:
        console.print("\n[dim]Sorties par type :[/dim]")
        for reason, count in metrics["exit_breakdown"].items():
            console.print(f"  {reason}: {count} trades")


def save_results(metrics: dict, strategy_id: str):
    """Sauvegarde les résultats du backtest"""
    # Equity curve
    eq_path = DATA_PROCESSED / f"backtest_{strategy_id}_equity.csv"
    metrics["equity_curve"].to_csv(eq_path)

    # Trades
    if not metrics["trade_df"].empty:
        tr_path = DATA_PROCESSED / f"backtest_{strategy_id}_trades.csv"
        metrics["trade_df"].to_csv(tr_path, index=False)

    console.print(f"[blue]💾 Résultats sauvegardés : backtest_{strategy_id}_*.csv[/blue]")