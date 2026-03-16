import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Market Overview", page_icon="📊", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');
    * { font-family: 'IBM Plex Sans', sans-serif !important; }
    [data-testid="stAppViewContainer"] { background: #070B14; }
    [data-testid="stSidebar"] { background: #0D1117; border-right: 1px solid #1C2333; }
    h1,h2,h3,h4 { color: #E6EDF3 !important; }
    #MainMenu, footer { visibility: hidden; }
    div[data-testid="metric-container"] {
        background: #0D1117; border: 1px solid #1C2333;
        border-radius: 8px; padding: 12px;
    }
    div[data-testid="metric-container"] label { color: #8B949E !important; font-size:0.75em !important; }
</style>
""", unsafe_allow_html=True)


def hex_to_rgba(h, a):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"

def pc(v): return "#3FB950" if v > 0 else ("#F85149" if v < 0 else "#8B949E")


COMM_CFG = {
    "wheat":   {"label": "🌾 Blé CBOT",   "color": "#F9A825", "unit": "¢/bu"},
    "corn":    {"label": "🌽 Maïs CBOT",  "color": "#58A6FF", "unit": "¢/bu"},
    "soybean": {"label": "🫘 Soja CBOT",  "color": "#3FB950", "unit": "¢/bu"},
    "soyoil":  {"label": "🫙 Huile Soja", "color": "#FF9800", "unit": "¢/lb"},
    "soymeal": {"label": "🐄 Tourteau",   "color": "#E040FB", "unit": "$/st"},
}

PERIOD_MAP = {"1M": 21, "3M": 63, "6M": 126, "1A": 252, "2A": 504, "5A": 1260, "Max": 9999}


@st.cache_data(ttl=300)
def load_data():
    try:
        from config import DATA_RAW, DATA_PROCESSED
    except:
        return {}

    data = {"prices": {}, "technical": {}, "cot": pd.DataFrame(),
            "crush": pd.DataFrame(), "forward": {}}

    for c in COMM_CFG:
        p = DATA_RAW / f"{c}_futures.csv"
        if p.exists():
            df = pd.read_csv(p, index_col="date", parse_dates=True)
            data["prices"][c] = df.dropna()

    for c in ["wheat", "corn", "soybean"]:
        p = DATA_PROCESSED / f"{c}_technical.csv"
        if p.exists():
            data["technical"][c] = pd.read_csv(p, index_col="date", parse_dates=True)

    p = DATA_PROCESSED / "cot_signals.csv"
    if p.exists():
        data["cot"] = pd.read_csv(p, parse_dates=["date"])
    else:
        try:
            from module_3_signals.indicators.sentiment_indicators import _synthetic_cot_signals
            data["cot"] = _synthetic_cot_signals()
        except:
            pass

    p = DATA_PROCESSED / "crush_history.csv"
    if p.exists():
        data["crush"] = pd.read_csv(p, parse_dates=["date"])

    for c in ["wheat", "corn", "soybean"]:
        p = DATA_PROCESSED / f"{c}_forward_curve.csv"
        if p.exists():
            data["forward"][c] = pd.read_csv(p)

    return data


data    = load_data()
prices  = data.get("prices", {})
tech    = data.get("technical", {})
cot_df  = data.get("cot", pd.DataFrame())
crush   = data.get("crush", pd.DataFrame())
forward = data.get("forward", {})


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 0 18px 0;border-bottom:1px solid #1C2333;margin-bottom:20px">
    <div>
        <span style="font-size:1.5em;font-weight:800;color:#E6EDF3">📊 Market Overview</span>
        <div style="font-size:0.78em;color:#8B949E;margin-top:3px">
            Prix · Indicateurs Techniques · COT · Crush · Courbe Forward
        </div>
    </div>
    <div style="font-size:0.75em;color:#8B949E">{datetime.now().strftime('%d %b %Y %H:%M')}</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CONTRÔLES
# ══════════════════════════════════════════════════════════════════════════════
ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
with ctrl1:
    commodity = st.selectbox(
        "Commodité",
        list(COMM_CFG.keys()),
        format_func=lambda x: COMM_CFG[x]["label"]
    )
with ctrl2:
    period = st.select_slider("Période", options=list(PERIOD_MAP.keys()), value="1A")
with ctrl3:
    show_ma  = st.checkbox("MAs", value=True)
    show_vol = st.checkbox("Volume", value=True)

n_days  = PERIOD_MAP[period]
cfg     = COMM_CFG[commodity]
color   = cfg["color"]
df_full = prices.get(commodity, pd.DataFrame())
tech_df = tech.get(commodity, pd.DataFrame())

if df_full.empty:
    st.error("Données non disponibles — lance `run_pipeline.py`.")
    st.stop()

df = df_full.iloc[-n_days:].copy()
if not tech_df.empty:
    tech_slice = tech_df.iloc[-n_days:].copy()
else:
    tech_slice = pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# MÉTRIQUES RAPIDES
# ══════════════════════════════════════════════════════════════════════════════
last    = float(df["close"].iloc[-1])
prev1d  = float(df["close"].iloc[-2])  if len(df) > 1  else last
prev1w  = float(df["close"].iloc[-6])  if len(df) > 5  else last
prev1m  = float(df["close"].iloc[-22]) if len(df) > 21 else last
prev3m  = float(df["close"].iloc[-63]) if len(df) > 62 else last
high52  = float(df_full["close"].iloc[-252:].max()) if len(df_full) > 251 else float(df_full["close"].max())
low52   = float(df_full["close"].iloc[-252:].min()) if len(df_full) > 251 else float(df_full["close"].min())
vol_avg = float(df["volume"].rolling(20).mean().iloc[-1]) if "volume" in df.columns else 0

rsi_val = None
if not tech_slice.empty and "rsi" in tech_slice.columns:
    rsi_vals = tech_slice["rsi"].dropna()
    if not rsi_vals.empty:
        rsi_val = float(rsi_vals.iloc[-1])

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric(f"{cfg['label']}", f"{last:.1f} {cfg['unit']}",
          f"{last - prev1d:+.1f} ({(last/prev1d-1)*100:+.2f}%)")
m2.metric("1 Semaine",  f"{last:.1f}", f"{(last/prev1w-1)*100:+.2f}%")
m3.metric("1 Mois",     f"{last:.1f}", f"{(last/prev1m-1)*100:+.2f}%")
m4.metric("3 Mois",     f"{last:.1f}", f"{(last/prev3m-1)*100:+.2f}%")
m5.metric("52W Range",  f"{low52:.0f} – {high52:.0f}",
          f"Position: {(last-low52)/(high52-low52)*100:.0f}%")
m6.metric("RSI(14)",
          f"{rsi_val:.1f}" if rsi_val else "—",
          "🔴 Suracheté" if rsi_val and rsi_val > 70 else
          ("🟢 Survendu" if rsi_val and rsi_val < 30 else "⚪ Neutre"))

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GRAPHIQUE PRINCIPAL — Prix + Indicateurs
# ══════════════════════════════════════════════════════════════════════════════
row_heights = [0.55, 0.20, 0.25] if show_vol else [0.65, 0.35]
n_rows      = 3 if show_vol else 2
row_titles  = (["Prix & MAs", "RSI(14)", "Volume"] if show_vol
               else ["Prix & MAs", "RSI(14)"])

fig = make_subplots(
    rows=n_rows, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    row_heights=row_heights,
)

# ── Candlesticks ──────────────────────────────────────────────────────────────
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["open"], high=df["high"],
    low=df["low"],   close=df["close"],
    name=cfg["label"],
    increasing_line_color="#3FB950",
    decreasing_line_color="#F85149",
    increasing_fillcolor="#3FB950",
    decreasing_fillcolor="#F85149",
), row=1, col=1)

# ── Moyennes mobiles ──────────────────────────────────────────────────────────
if show_ma and not tech_slice.empty:
    ma_cfg = [
        ("ma20",  "#F0B429", 1.2, "MA20"),
        ("ma50",  "#58A6FF", 1.5, "MA50"),
        ("ma200", "#E040FB", 1.8, "MA200"),
    ]
    for col_name, ma_col, width, ma_label in ma_cfg:
        if col_name in tech_slice.columns:
            ma_data = tech_slice[col_name].dropna()
            fig.add_trace(go.Scatter(
                x=ma_data.index, y=ma_data.values,
                name=ma_label,
                line=dict(color=ma_col, width=width),
                hovertemplate=f"{ma_label}: %{{y:.1f}}<extra></extra>",
            ), row=1, col=1)

    # Bollinger Bands
    if "bb_upper" in tech_slice.columns and "bb_lower" in tech_slice.columns:
        fig.add_trace(go.Scatter(
            x=tech_slice.index, y=tech_slice["bb_upper"],
            name="BB Upper", line=dict(color=hex_to_rgba(color, 0.4), width=1, dash="dot"),
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=tech_slice.index, y=tech_slice["bb_lower"],
            name="BB Lower", line=dict(color=hex_to_rgba(color, 0.4), width=1, dash="dot"),
            fill="tonexty", fillcolor=hex_to_rgba(color, 0.04),
            showlegend=False,
        ), row=1, col=1)

# ── RSI ───────────────────────────────────────────────────────────────────────
if not tech_slice.empty and "rsi" in tech_slice.columns:
    rsi_series = tech_slice["rsi"].dropna()
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(248,81,73,0.08)",
                  line_width=0, row=2, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(63,185,80,0.08)",
                  line_width=0, row=2, col=1)
    fig.add_trace(go.Scatter(
        x=rsi_series.index, y=rsi_series.values,
        name="RSI(14)", line=dict(color="#58A6FF", width=1.8),
        hovertemplate="RSI: %{y:.1f}<extra></extra>",
    ), row=2, col=1)
    for level, lc in [(70, "#F85149"), (30, "#3FB950"), (50, "#8B949E")]:
        fig.add_hline(y=level, line_dash="dash", line_color=lc,
                      opacity=0.4, row=2, col=1)

# ── Volume ────────────────────────────────────────────────────────────────────
if show_vol and "volume" in df.columns:
    vol_colors = [
        "#3FB950" if float(df["close"].iloc[i]) >= float(df["open"].iloc[i])
        else "#F85149"
        for i in range(len(df))
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["volume"],
        name="Volume", marker_color=vol_colors, opacity=0.6,
    ), row=3, col=1)
    # MA volume 20j
    vol_ma = df["volume"].rolling(20).mean()
    fig.add_trace(go.Scatter(
        x=vol_ma.index, y=vol_ma.values,
        name="Vol MA20", line=dict(color="#F0B429", width=1.2),
        showlegend=False,
    ), row=3, col=1)

fig.update_layout(
    paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
    font=dict(color="#8B949E", size=10, family="IBM Plex Mono"),
    height=520,
    margin=dict(l=5, r=10, t=10, b=5),
    xaxis_rangeslider_visible=False,
    legend=dict(
        bgcolor="rgba(13,17,23,0.8)",
        bordercolor="#1C2333", borderwidth=1,
        font=dict(size=10), orientation="h",
        yanchor="bottom", y=1.01, xanchor="left", x=0,
    ),
)
for r in range(1, n_rows + 1):
    fig.update_xaxes(gridcolor="#1C2333", zeroline=False, row=r, col=1)
    fig.update_yaxes(gridcolor="#1C2333", zeroline=False, row=r, col=1)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# ROW 2 : COT + Forward Curve
# ══════════════════════════════════════════════════════════════════════════════
col_cot, col_fwd = st.columns([1, 1])

# ── COT Chart ─────────────────────────────────────────────────────────────────
with col_cot:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">📋 COT REPORT — POSITIONING SPÉCULATIF</div>
    """, unsafe_allow_html=True)

    if not cot_df.empty and commodity in ["wheat", "corn", "soybean"]:
        sub_cot = (cot_df[cot_df["commodity"] == commodity]
                   .sort_values("date").tail(156))

        if not sub_cot.empty:
            fig_cot = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                vertical_spacing=0.04,
                row_heights=[0.40, 0.30, 0.30],
            )

            # Net Spec
            fig_cot.add_trace(go.Scatter(
                x=sub_cot["date"], y=sub_cot["net_spec"],
                name="Net Spec (Fonds)",
                line=dict(color="#58A6FF", width=2),
                fill="tozeroy", fillcolor="rgba(88,166,255,0.08)",
            ), row=1, col=1)
            # Net Comm
            fig_cot.add_trace(go.Scatter(
                x=sub_cot["date"], y=sub_cot["net_comm"],
                name="Net Comm (Hedgers)",
                line=dict(color="#F9A825", width=1.5, dash="dot"),
            ), row=1, col=1)
            fig_cot.add_hline(y=0, line_color="white", opacity=0.15, row=1, col=1)

            # Percentile 3 ans
            fig_cot.add_hrect(y0=80, y1=100,
                              fillcolor="rgba(248,81,73,0.1)", line_width=0, row=2, col=1)
            fig_cot.add_hrect(y0=0,  y1=20,
                              fillcolor="rgba(63,185,80,0.1)",  line_width=0, row=2, col=1)
            fig_cot.add_trace(go.Scatter(
                x=sub_cot["date"], y=sub_cot["nsl_pctile"],
                name="Percentile 3A",
                line=dict(color="#E040FB", width=2),
            ), row=2, col=1)
            for lvl, lc in [(80, "#F85149"), (20, "#3FB950")]:
                fig_cot.add_hline(y=lvl, line_dash="dash", line_color=lc,
                                  opacity=0.5, row=2, col=1)

            # Ratio Long/Short spéculatifs
            if "spec_long_ratio" in sub_cot.columns:
                fig_cot.add_trace(go.Scatter(
                    x=sub_cot["date"],
                    y=sub_cot["spec_long_ratio"] * 100,
                    name="% Long spécs",
                    line=dict(color="#3FB950", width=1.5),
                    fill="tozeroy", fillcolor="rgba(63,185,80,0.06)",
                ), row=3, col=1)
                fig_cot.add_hline(y=50, line_dash="dash",
                                  line_color="white", opacity=0.2, row=3, col=1)

            fig_cot.update_layout(
                paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
                font=dict(color="#8B949E", size=10),
                height=400,
                margin=dict(l=5, r=5, t=10, b=5),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
            )
            for r in [1, 2, 3]:
                fig_cot.update_xaxes(gridcolor="#1C2333", row=r, col=1)
                fig_cot.update_yaxes(gridcolor="#1C2333", row=r, col=1)

            st.plotly_chart(fig_cot, use_container_width=True,
                            config={"displayModeBar": False})

            # Statut COT actuel
            last_cot   = sub_cot.iloc[-1]
            pctile     = float(last_cot.get("nsl_pctile", 50))
            net_s      = float(last_cot.get("net_spec", 0))
            col_p      = "#F85149" if pctile > 75 else ("#3FB950" if pctile < 25 else "#F0B429")
            status     = ("🔴 EXTRÊME LONG — Signal bearish contrarian" if pctile > 80 else
                          "🟢 EXTRÊME SHORT — Signal bullish contrarian" if pctile < 20 else
                          "⚪ Neutre — Pas de signal contrarian")
            st.markdown(
                f'<div style="background:#0D1117;border:1px solid #1C2333;'
                f'border-left:3px solid {col_p};border-radius:6px;'
                f'padding:10px 14px;font-size:0.8em">'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:6px">'
                f'<span style="color:#8B949E">NSL Percentile 3A</span>'
                f'<span style="color:{col_p};font-weight:700">{pctile:.0f}%ile</span>'
                f'</div>'
                f'<div style="background:#1C2333;border-radius:3px;height:5px;margin-bottom:8px">'
                f'<div style="background:{col_p};width:{pctile:.0f}%;height:5px;'
                f'border-radius:3px"></div></div>'
                f'<div style="color:{col_p};font-size:0.85em">{status}</div>'
                f'<div style="color:#8B949E;font-size:0.78em;margin-top:4px">'
                f'Net Spec: {net_s:+,.0f} contrats</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("COT non disponible pour cette commodité.")


# ── Forward Curve ─────────────────────────────────────────────────────────────
with col_fwd:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">📈 COURBE FORWARD & STRUCTURE DE MARCHÉ</div>
    """, unsafe_allow_html=True)

    fwd_comm = commodity if commodity in ["wheat", "corn", "soybean"] else "wheat"
    df_fwd   = forward.get(fwd_comm, pd.DataFrame())

    if not df_fwd.empty:
        spot      = float(df_fwd["spot_price"].iloc[0])
        last_fwd  = float(df_fwd["theoretical_forward"].iloc[-1])
        structure = "CONTANGO" if last_fwd > spot else "BACKWARDATION"
        struct_col = "#F0B429" if structure == "CONTANGO" else "#3FB950"

        fig_fwd = go.Figure()

        # Zone sous la courbe
        fig_fwd.add_trace(go.Scatter(
            x=df_fwd["months_forward"],
            y=df_fwd["theoretical_forward"],
            name="Forward théorique",
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=7, color=color),
            fill="tozeroy",
            fillcolor=hex_to_rgba(color, 0.06),
        ))

        # Ligne spot
        fig_fwd.add_hline(
            y=spot, line_dash="dash", line_color="white",
            opacity=0.3,
            annotation_text=f"Spot: {spot:.0f}",
            annotation_font=dict(color="white", size=10),
        )

        # Annotation dernière valeur
        fig_fwd.add_annotation(
            x=df_fwd["months_forward"].iloc[-1],
            y=last_fwd,
            text=f" M+12: {last_fwd:.0f}",
            showarrow=False,
            font=dict(color=color, size=10),
            xanchor="left",
        )

        fig_fwd.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10),
            height=280,
            margin=dict(l=5, r=50, t=10, b=5),
            xaxis=dict(title="Mois forward", gridcolor="#1C2333"),
            yaxis=dict(title=f"Prix ({cfg['unit']})", gridcolor="#1C2333"),
            showlegend=False,
        )
        st.plotly_chart(fig_fwd, use_container_width=True,
                        config={"displayModeBar": False})

        # Stats structure
        carry_total = last_fwd - spot
        _str_html = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px">'

            f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;padding:10px">'
            f'<div style="font-size:0.65em;color:#8B949E">Structure</div>'
            f'<div style="font-size:0.95em;font-weight:700;color:{struct_col}">{structure}</div>'
            f'</div>'

            f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;padding:10px">'
            f'<div style="font-size:0.65em;color:#8B949E">Carry M+12</div>'
            f'<div style="font-size:0.95em;font-weight:700;color:{pc(carry_total)}">'
            f'{carry_total:+.1f}¢</div>'
            f'</div>'

            f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;padding:10px">'
            f'<div style="font-size:0.65em;color:#8B949E">Carry/mois</div>'
            f'<div style="font-size:0.95em;font-weight:700;color:#8B949E">'
            f'{carry_total/12:+.2f}¢</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(_str_html, unsafe_allow_html=True)

        # Lecture
        lecture = (
            "📈 Marché en CONTANGO — stocks abondants, pas de prime sur le spot. "
            "Les acheteurs peuvent attendre. Les vendeurs ont intérêt à livrer rapidement."
            if structure == "CONTANGO" else
            "📉 Marché en BACKWARDATION — marché tendu, prime sur le physique. "
            "Signal d'achat immédiat fort. Stocks serrés à l'origine."
        )
        st.markdown(
            f'<div style="background:#0D1117;border:1px solid #1C2333;'
            f'border-left:3px solid {struct_col};border-radius:6px;'
            f'padding:10px 14px;font-size:0.78em;color:#C9D1D9;line-height:1.5">'
            f'{lecture}</div>',
            unsafe_allow_html=True
        )

        # Table forward par mois
        st.markdown("""
        <div style="font-size:0.68em;color:#8B949E;font-weight:600;
                    margin:14px 0 8px 0">📋 COURBE DÉTAILLÉE</div>
        """, unsafe_allow_html=True)

        _fwd_rows = ""
        for _, frow in df_fwd.iterrows():
            m      = int(frow["months_forward"])
            fwd    = float(frow["theoretical_forward"])
            carry  = float(frow["carry_cost_total"])
            c_col  = "#3FB950" if carry > 0 else "#F85149"
            _fwd_rows += (
                f'<tr style="border-bottom:1px solid #1C2333">'
                f'<td style="padding:5px 8px;color:#8B949E">M+{m}</td>'
                f'<td style="padding:5px 8px;color:#E6EDF3;text-align:right;'
                f'font-family:IBM Plex Mono,monospace">{fwd:.1f}</td>'
                f'<td style="padding:5px 8px;color:{c_col};text-align:right;'
                f'font-family:IBM Plex Mono,monospace">{carry:+.2f}</td>'
                f'</tr>'
            )
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:0.8em">'
            f'<thead><tr style="border-bottom:1px solid #30363D">'
            f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:left">Échéance</th>'
            f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">Prix (¢/bu)</th>'
            f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">Carry</th>'
            f'</tr></thead>'
            f'<tbody>{_fwd_rows}</tbody>'
            f'</table>',
            unsafe_allow_html=True
        )
    else:
        st.info("Courbe forward non disponible — lance `pricing_pipeline.py`.")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# ROW 3 : Crush Margin (soja) + Corrélations
# ══════════════════════════════════════════════════════════════════════════════
col_crush, col_corr = st.columns([1, 1])

# ── Crush Margin ──────────────────────────────────────────────────────────────
with col_crush:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">⚙️ SOYBEAN CRUSH MARGIN</div>
    """, unsafe_allow_html=True)

    if not crush.empty:
        crush_recent = crush.sort_values("date").tail(n_days)

        fig_crush = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                  vertical_spacing=0.05, row_heights=[0.65, 0.35])

        # Net crush
        crush_vals = crush_recent["net_crush_usd_bu"]
        crush_cols = ["rgba(63,185,80,0.7)" if v > 1.0 else
                      "rgba(240,180,41,0.7)" if v > 0.5 else
                      "rgba(248,81,73,0.7)"
                      for v in crush_vals]

        fig_crush.add_trace(go.Bar(
            x=crush_recent["date"], y=crush_vals,
            name="Net Crush ($/bu)",
            marker_color=crush_cols,
        ), row=1, col=1)
        fig_crush.add_hline(y=1.0, line_dash="dash", line_color="#F0B429",
                            opacity=0.6,
                            annotation_text="Seuil rentabilité $1.00",
                            row=1, col=1)

        # Percentile
        if "crush_pctile" in crush_recent.columns:
            fig_crush.add_trace(go.Scatter(
                x=crush_recent["date"], y=crush_recent["crush_pctile"],
                name="Percentile hist.",
                line=dict(color="#58A6FF", width=1.8),
            ), row=2, col=1)
            fig_crush.add_hline(y=50, line_dash="dot", line_color="white",
                                opacity=0.2, row=2, col=1)

        fig_crush.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10),
            height=300,
            margin=dict(l=5, r=5, t=10, b=5),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
            showlegend=True,
        )
        for r in [1, 2]:
            fig_crush.update_xaxes(gridcolor="#1C2333", row=r, col=1)
            fig_crush.update_yaxes(gridcolor="#1C2333", row=r, col=1)

        st.plotly_chart(fig_crush, use_container_width=True,
                        config={"displayModeBar": False})

        last_crush   = float(crush["net_crush_usd_bu"].iloc[-1])
        last_crush_mt = float(crush["net_crush_usd_mt"].iloc[-1])
        last_pctile  = float(crush["crush_pctile"].iloc[-1]) if "crush_pctile" in crush.columns else 50
        crush_color  = "#3FB950" if last_crush > 1.0 else ("#F0B429" if last_crush > 0.5 else "#F85149")
        crush_signal = ("🟢 EXCELLENT — Crushers très profitables → forte demande soja" if last_crush > 1.5 else
                        "🟡 BON — Marges correctes" if last_crush > 0.8 else
                        "🔴 FAIBLE — Marges sous pression")

        st.markdown(
            f'<div style="background:#0D1117;border:1px solid #1C2333;'
            f'border-left:3px solid {crush_color};border-radius:6px;padding:10px 14px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<div>'
            f'<div style="font-size:1.2em;font-weight:700;color:{crush_color}">'
            f'${last_crush:.2f}/bu &nbsp;·&nbsp; ${last_crush_mt:.0f}/MT</div>'
            f'<div style="font-size:0.75em;color:#8B949E;margin-top:2px">{crush_signal}</div>'
            f'</div>'
            f'<div style="text-align:right">'
            f'<div style="font-size:1.1em;font-weight:700;color:{crush_color}">'
            f'{last_pctile:.0f}%ile</div>'
            f'<div style="font-size:0.68em;color:#8B949E">Percentile hist.</div>'
            f'</div></div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.info("Crush history non disponible — lance `pricing_pipeline.py`.")


# ── Corrélations rolling ──────────────────────────────────────────────────────
with col_corr:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">🔗 CORRÉLATIONS ROLLING (63J) & PERFORMANCE RELATIVE</div>
    """, unsafe_allow_html=True)

    if len(prices) >= 2:
        # Returns journaliers
        rets = {}
        for c, df_c in prices.items():
            if c in ["wheat", "corn", "soybean"]:
                rets[c] = df_c["close"].pct_change().dropna()

        if len(rets) >= 2:
            ret_df = pd.DataFrame(rets).dropna().iloc[-n_days:]

            # Corrélations rolling 63j
            fig_corr = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                     vertical_spacing=0.06,
                                     row_heights=[0.55, 0.45])

            pairs = [
                ("wheat", "corn",    "#F0B429", "Blé/Maïs"),
                ("wheat", "soybean", "#E040FB", "Blé/Soja"),
                ("corn",  "soybean", "#58A6FF", "Maïs/Soja"),
            ]
            for c1, c2, col_c, label in pairs:
                if c1 in ret_df.columns and c2 in ret_df.columns:
                    roll_corr = ret_df[c1].rolling(63).corr(ret_df[c2]).dropna()
                    fig_corr.add_trace(go.Scatter(
                        x=roll_corr.index, y=roll_corr.values,
                        name=label, line=dict(color=col_c, width=1.8),
                    ), row=1, col=1)

            fig_corr.add_hline(y=0, line_color="white", opacity=0.2, row=1, col=1)
            fig_corr.add_hline(y=0.7, line_dash="dash", line_color="#F0B429",
                               opacity=0.3, row=1, col=1)

            # Performance relative normalisée (base 100)
            for c, col_c in [("wheat","#F9A825"),("corn","#58A6FF"),("soybean","#3FB950")]:
                if c in ret_df.columns:
                    norm = (1 + ret_df[c]).cumprod() * 100
                    fig_corr.add_trace(go.Scatter(
                        x=norm.index, y=norm.values,
                        name=COMM_CFG[c]["label"],
                        line=dict(color=col_c, width=1.8),
                    ), row=2, col=1)

            fig_corr.add_hline(y=100, line_dash="dash", line_color="white",
                               opacity=0.2, row=2, col=1)

            fig_corr.update_layout(
                paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
                font=dict(color="#8B949E", size=10),
                height=320,
                margin=dict(l=5, r=5, t=10, b=5),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
            )
            for r in [1, 2]:
                fig_corr.update_xaxes(gridcolor="#1C2333", row=r, col=1)
                fig_corr.update_yaxes(gridcolor="#1C2333", row=r, col=1)

            st.plotly_chart(fig_corr, use_container_width=True,
                            config={"displayModeBar": False})

            # Corrélation actuelle
            _corr_html = '<div style="display:flex;gap:8px;flex-wrap:wrap">'
            for c1, c2, col_c, label in pairs:
                if c1 in ret_df.columns and c2 in ret_df.columns:
                    curr_corr = float(ret_df[c1].tail(63).corr(ret_df[c2].tail(63)))
                    corr_col  = ("#3FB950" if abs(curr_corr) < 0.4 else
                                 "#F0B429" if abs(curr_corr) < 0.7 else "#F85149")
                    _corr_html += (
                        f'<div style="flex:1;background:#0D1117;border:1px solid #1C2333;'
                        f'border-radius:6px;padding:8px;text-align:center;min-width:80px">'
                        f'<div style="font-size:0.65em;color:#8B949E">{label}</div>'
                        f'<div style="font-size:1.1em;font-weight:700;color:{corr_col}">'
                        f'{curr_corr:.2f}</div>'
                        f'</div>'
                    )
            _corr_html += '</div>'
            st.markdown(_corr_html, unsafe_allow_html=True)
    else:
        st.info("Données insuffisantes pour les corrélations.")