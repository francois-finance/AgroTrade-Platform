"""
Composants graphiques Plotly réutilisables pour le dashboard.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


COLORS = {
    "bullish":    "#00C853",
    "bearish":    "#FF1744",
    "neutral":    "#FFD600",
    "background": "#0E1117",
    "surface":    "#1E2130",
    "text":       "#FAFAFA",
    "wheat":      "#F9A825",
    "corn":       "#FFD600",
    "soybean":    "#66BB6A",
    "accent":     "#448AFF",
}

LAYOUT_BASE = dict(
    paper_bgcolor=COLORS["background"],
    plot_bgcolor=COLORS["surface"],
    font=dict(color=COLORS["text"], family="Inter, sans-serif"),
    margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)"),
)


def price_chart(df: pd.DataFrame, commodity: str, show_ma: bool = True) -> go.Figure:
    """Graphique de prix OHLCV avec moyennes mobiles"""
    color = COLORS.get(commodity, COLORS["accent"])

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"], high=df["high"],
        low=df["low"],   close=df["close"],
        name=commodity.upper(),
        increasing_line_color=COLORS["bullish"],
        decreasing_line_color=COLORS["bearish"],
    ), row=1, col=1)

    # Moyennes mobiles
    if show_ma and "ma50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["ma50"],
            name="MA50", line=dict(color="#FF9800", width=1.5),
        ), row=1, col=1)
    if show_ma and "ma200" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["ma200"],
            name="MA200", line=dict(color="#E040FB", width=1.5),
        ), row=1, col=1)

    # Volume
    colors_vol = [
        COLORS["bullish"] if c >= o else COLORS["bearish"]
        for c, o in zip(df["close"], df["open"])
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["volume"],
        name="Volume", marker_color=colors_vol, opacity=0.6,
    ), row=2, col=1)

    fig.update_layout(
        **LAYOUT_BASE,
        title=f"{commodity.upper()} — Prix Futures CBOT",
        xaxis_rangeslider_visible=False,
        height=500,
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


def rsi_chart(df: pd.DataFrame, commodity: str) -> go.Figure:
    """Graphique RSI avec zones de surachat/survendu"""
    fig = go.Figure()

    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,23,68,0.1)",
                  line_width=0, annotation_text="Suracheté")
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(0,200,83,0.1)",
                  line_width=0, annotation_text="Survendu")
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["bearish"], opacity=0.5)
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["bullish"], opacity=0.5)
    fig.add_hline(y=50, line_dash="dot",  line_color="gray", opacity=0.3)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["rsi"],
        name="RSI(14)",
        line=dict(color=COLORS["accent"], width=2),
        fill="tozeroy",
        fillcolor="rgba(68,138,255,0.1)",
    ))

    fig.update_layout(
        **LAYOUT_BASE,
        title=f"RSI — {commodity.upper()}",
        yaxis=dict(range=[0, 100]),
        height=250,
    )
    return fig


def forward_curve_chart(df: pd.DataFrame, commodity: str) -> go.Figure:
    """Courbe forward théorique"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["months_forward"],
        y=df["theoretical_forward"],
        name="Forward théorique",
        mode="lines+markers",
        line=dict(color=COLORS.get(commodity, COLORS["accent"]), width=3),
        marker=dict(size=8),
    ))

    # Ligne spot
    spot = df["spot_price"].iloc[0]
    fig.add_hline(y=spot, line_dash="dash",
                  line_color="white", opacity=0.4,
                  annotation_text=f"Spot: {spot:.0f}")

    # Zone de couleur contango/backwardation
    last_forward = df["theoretical_forward"].iloc[-1]
    color_fill = "rgba(255,23,68,0.1)" if last_forward > spot else "rgba(0,200,83,0.1)"

    fig.update_layout(
        **LAYOUT_BASE,
        title=f"Courbe Forward — {commodity.upper()} (12 mois)",
        xaxis_title="Mois forward",
        yaxis_title="Prix (cents/bu)",
        height=320,
    )
    return fig


def crush_history_chart(df: pd.DataFrame) -> go.Figure:
    """Historique marge de crushing avec percentile"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["net_crush_usd_bu"],
        name="Net Crush ($/bu)",
        line=dict(color=COLORS["soybean"], width=2),
        fill="tozeroy",
        fillcolor="rgba(102,187,106,0.15)",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["crush_pctile"],
        name="Percentile historique",
        line=dict(color=COLORS["accent"], width=1, dash="dot"),
    ), secondary_y=True)

    fig.add_hline(y=1.0, line_dash="dash", line_color="white",
                  opacity=0.3, annotation_text="Seuil rentabilité")

    fig.update_layout(
        **LAYOUT_BASE,
        title="Soybean Crush Margin — Historique",
        height=350,
    )
    fig.update_yaxes(title_text="$/bu", secondary_y=False,
                     gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(title_text="Percentile (%)", secondary_y=True,
                     range=[0, 100])
    return fig


def correlation_heatmap(corr_matrix: pd.DataFrame) -> go.Figure:
    """Heatmap de corrélation"""
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.str.upper(),
        y=corr_matrix.index.str.upper(),
        colorscale="RdYlGn",
        zmid=0, zmin=-1, zmax=1,
        text=corr_matrix.round(2).values,
        texttemplate="%{text}",
        textfont={"size": 14},
        showscale=True,
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title="Matrice de Corrélation (252j)",
        height=280,
    )
    return fig


def equity_curve_chart(results: dict) -> go.Figure:
    """Courbes d'equity des backtests"""
    fig = go.Figure()
    palette = [COLORS["wheat"], COLORS["soybean"], COLORS["accent"],
               "#FF9800", "#E040FB"]

    for i, (name, result) in enumerate(results.items()):
        eq = result["equity_curve"]["equity"]
        normalized = (eq / eq.iloc[0] - 1) * 100  # En % de rendement
        color = palette[i % len(palette)]
        fig.add_trace(go.Scatter(
            x=eq.index, y=normalized,
            name=name, line=dict(color=color, width=2),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
    fig.update_layout(
        **LAYOUT_BASE,
        title="Equity Curves — Toutes Stratégies (base 100)",
        yaxis_title="Rendement (%)",
        height=400,
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


def stress_test_chart(stress_df: pd.DataFrame) -> go.Figure:
    """Barres horizontales des stress tests"""
    df = stress_df.sort_values("total_pnl")
    colors = [COLORS["bearish"] if v < 0 else COLORS["bullish"]
              for v in df["total_pnl"]]

    labels = df["scenario"].str.replace("_", " ").str.title()
    fig = go.Figure(go.Bar(
        x=df["total_pnl"],
        y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"${v:+,.0f}" for v in df["total_pnl"]],
        textposition="outside",
    ))

    fig.add_vline(x=0, line_color="white", opacity=0.5)
    fig.update_layout(
        **LAYOUT_BASE,
        title="Stress Tests — Impact P&L",
        xaxis_title="P&L ($)",
        height=400,
    )
    return fig


def signal_radar_chart(signals: dict) -> go.Figure:
    """Radar chart des signaux par commodité"""
    categories = ["Momentum", "RSI", "Bollinger", "COT", "Météo", "BDI"]
    fig = go.Figure()

    colors_comm = {
        "wheat":   COLORS["wheat"],
        "corn":    COLORS["corn"],
        "soybean": COLORS["soybean"],
    }

    for commodity, sig in signals.items():
        values = [
            sig.get("momentum", 0),
            -sig.get("rsi", 0),      # Inversé : RSI haut = bearish
            sig.get("bb", 0),
            sig.get("cot", 0),
            sig.get("weather", 0),
            sig.get("bdi", 0),
        ]
        # Normalise de [-1,1] vers [0,1] pour le radar
        values_norm = [(v + 1) / 2 for v in values]
        values_norm.append(values_norm[0])  # Ferme le polygone

        fig.add_trace(go.Scatterpolar(
            r=values_norm,
            theta=categories + [categories[0]],
            fill="toself",
            name=commodity.upper(),
            line_color=colors_comm.get(commodity, COLORS["accent"]),
            opacity=0.7,
        ))

    fig.update_layout(
        **LAYOUT_BASE,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1],
                            gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            bgcolor=COLORS["surface"],
        ),
        title="Signal Radar — Toutes Commodités",
        height=380,
    )
    return fig