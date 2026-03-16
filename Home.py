"""
AgroTrade Intelligence Platform — Home
Bloomberg-style dark premium dashboard
"""

import streamlit as st
import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="AgroTrade Platform",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Bloomberg Premium ─────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

    * { font-family: 'IBM Plex Sans', sans-serif !important; }
    code, .mono { font-family: 'IBM Plex Mono', monospace !important; }

    [data-testid="stAppViewContainer"] { background: #070B14; }
    [data-testid="stSidebar"] {
        background: #0D1117;
        border-right: 1px solid #1C2333;
    }
    .main .block-container { padding: 1.5rem 2rem; max-width: 100%; }
    h1, h2, h3, h4 { color: #E6EDF3 !important; }

    [data-testid="stSidebarNav"] a {
        color: #8B949E !important;
        border-radius: 6px;
        transition: all 0.2s;
    }
    [data-testid="stSidebarNav"] a:hover {
        background: #1C2333 !important;
        color: #E6EDF3 !important;
    }
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background: #1C2333 !important;
        color: #58A6FF !important;
        border-left: 2px solid #58A6FF;
    }

    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu, footer { visibility: hidden; }

    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0D1117; }
    ::-webkit-scrollbar-thumb { background: #30363D; border-radius: 3px; }

    .stButton button {
        background: #1C2333;
        border: 1px solid #30363D;
        color: #E6EDF3;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton button:hover {
        background: #21262D;
        border-color: #58A6FF;
        color: #58A6FF;
    }

    .stSpinner > div { border-top-color: #58A6FF !important; }

    div[data-testid="metric-container"] {
        background: #0D1117;
        border: 1px solid #1C2333;
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="metric-container"] label { color: #8B949E !important; font-size: 0.75em !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #E6EDF3 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def load_prices() -> dict:
    try:
        from config import DATA_RAW
        prices = {}
        for c in ["wheat", "corn", "soybean", "soyoil", "soymeal"]:
            path = DATA_RAW / f"{c}_futures.csv"
            if path.exists():
                df   = pd.read_csv(path, index_col="date", parse_dates=True)
                last = df["close"].dropna()
                if len(last) < 22:
                    continue
                prices[c] = {
                    "price":      round(float(last.iloc[-1]), 2),
                    "chg_1d":     round(float(last.iloc[-1] - last.iloc[-2]), 2),
                    "chg_1d_pct": round(float((last.iloc[-1]/last.iloc[-2]-1)*100), 2),
                    "chg_1w_pct": round(float((last.iloc[-1]/last.iloc[-6]-1)*100), 2)  if len(last)>5  else 0,
                    "chg_1m_pct": round(float((last.iloc[-1]/last.iloc[-22]-1)*100), 2) if len(last)>21 else 0,
                    "chg_3m_pct": round(float((last.iloc[-1]/last.iloc[-66]-1)*100), 2) if len(last)>65 else 0,
                    "high_52w":   round(float(last.iloc[-252:].max()), 2) if len(last)>251 else round(float(last.max()), 2),
                    "low_52w":    round(float(last.iloc[-252:].min()), 2) if len(last)>251 else round(float(last.min()), 2),
                    "series":     last.iloc[-90:].tolist(),
                    "dates":      last.iloc[-90:].index.strftime("%Y-%m-%d").tolist(),
                }
        return prices
    except Exception:
        return {}


def load_signals() -> pd.DataFrame:
    try:
        from config import DATA_PROCESSED
        path = DATA_PROCESSED / "signals_summary.csv"
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except:
        return pd.DataFrame()


def load_trade_ideas() -> dict:
    try:
        from config import DATA_PROCESSED
        path = DATA_PROCESSED / "trade_ideas_latest.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except:
        pass
    return {}


def load_crush() -> dict:
    try:
        from config import DATA_PROCESSED
        path = DATA_PROCESSED / "crush_history.csv"
        if path.exists():
            df   = pd.read_csv(path)
            last = df.iloc[-1]
            return {
                "net_crush":    round(float(last["net_crush_usd_bu"]), 2),
                "net_crush_mt": round(float(last["net_crush_usd_mt"]), 1),
                "pctile":       round(float(last["crush_pctile"]), 0),
            }
    except:
        pass
    return {}


def load_var() -> dict:
    try:
        from config import DATA_PROCESSED
        path = DATA_PROCESSED / "var_analysis.csv"
        if path.exists():
            df        = pd.read_csv(path)
            total_var = df["var_1d_99_hist"].sum()
            total_pos = df["position_value"].sum()
            return {
                "total_var": round(total_var, 0),
                "total_pos": round(total_pos, 0),
                "var_pct":   round(total_var/total_pos*100, 2) if total_pos > 0 else 0,
            }
    except:
        pass
    return {}


def load_basis() -> pd.DataFrame:
    try:
        from config import DATA_PROCESSED
        path = DATA_PROCESSED / "basis_analysis.csv"
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except:
        return pd.DataFrame()


def price_color(chg): return "#3FB950" if chg > 0 else ("#F85149" if chg < 0 else "#8B949E")
def price_arrow(chg): return "▲" if chg > 0 else ("▼" if chg < 0 else "—")


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
now = datetime.now().strftime("%A %d %B %Y — %H:%M")
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:12px 0 20px 0;border-bottom:1px solid #1C2333;margin-bottom:20px">
    <div>
        <span style="font-size:1.7em;font-weight:800;color:#E6EDF3;letter-spacing:-0.5px">
            🌾 AgroTrade
        </span>
        <span style="font-size:1.7em;font-weight:300;color:#58A6FF;margin-left:8px">
            Intelligence Platform
        </span>
        <div style="font-size:0.78em;color:#8B949E;margin-top:4px">
            Agricultural Commodities · Data · Freight · Signals · Pricing · Risk · LLM
        </div>
    </div>
    <div style="text-align:right">
        <div style="font-size:0.85em;color:#8B949E">{now}</div>
        <div style="font-size:0.75em;color:#3FB950;margin-top:2px">● CBOT Data J-1</div>
        <div style="font-size:0.72em;color:#8B949E;margin-top:2px">
            Sources : CME · CFTC · Open-Meteo · Baltic Exchange
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TICKER BAR — string concaténée, UN SEUL st.markdown à la fin
# ══════════════════════════════════════════════════════════════════════════════
prices = load_prices()

ticker_config = {
    "wheat":   ("ZW", "BLÉ",      "¢/bu"),
    "corn":    ("ZC", "MAÏS",     "¢/bu"),
    "soybean": ("ZS", "SOJA",     "¢/bu"),
    "soyoil":  ("ZL", "HUILE",    "¢/lb"),
    "soymeal": ("ZM", "TOURTEAU", "$/st"),
}

_ticker_html = ""
for key, (code, name, unit) in ticker_config.items():
    if key in prices:
        p       = prices[key]
        col     = price_color(p["chg_1d"])
        arr     = price_arrow(p["chg_1d"])
        rng     = p["high_52w"] - p["low_52w"]
        pos_pct = int(((p["price"] - p["low_52w"]) / rng * 100)) if rng > 0 else 50
        pos_pct = max(3, min(97, pos_pct))

        _ticker_html += (
            '<div style="display:flex;flex-direction:column;gap:6px;'
            'padding:10px 16px;background:#0D1117;'
            'border-radius:8px;border:1px solid #1C2333;min-width:155px">'

            '<div style="display:flex;justify-content:space-between;align-items:flex-start">'
            '<div>'
            f'<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px">{code} &nbsp;{name}</div>'
            f'<div style="font-size:1.15em;font-weight:700;color:#E6EDF3;margin-top:2px">'
            f'{p["price"]:.1f}'
            f'<span style="font-size:0.65em;color:#8B949E"> {unit}</span></div>'
            '</div>'
            '<div style="text-align:right">'
            f'<div style="color:{col};font-weight:600;font-size:0.85em">{arr} {abs(p["chg_1d"]):.1f}</div>'
            f'<div style="color:{col};font-size:0.78em">{p["chg_1d_pct"]:+.2f}%</div>'
            '</div></div>'

            '<div>'
            '<div style="display:flex;justify-content:space-between;font-size:0.62em;color:#8B949E;margin-bottom:3px">'
            f'<span>{p["low_52w"]:.0f}</span><span>52W</span><span>{p["high_52w"]:.0f}</span>'
            '</div>'
            '<div style="background:#1C2333;border-radius:2px;height:3px;position:relative">'
            f'<div style="position:absolute;left:{pos_pct}%;top:-2px;width:7px;height:7px;'
            f'background:{col};border-radius:50%;transform:translateX(-50%)"></div>'
            '</div></div>'

            '</div>'
        )

# UN SEUL st.markdown — jamais de st.markdown intermédiaire dans la boucle
st.markdown(
    f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px">{_ticker_html}</div>',
    unsafe_allow_html=True
)


# ══════════════════════════════════════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════════════════════════════════════
crush      = load_crush()
var        = load_var()
signals_df = load_signals()
basis_df   = load_basis()

market_score = 0.0
if not signals_df.empty and "composite" in signals_df.columns:
    market_score = round(float(signals_df["composite"].mean()), 3)
market_color = "#3FB950" if market_score > 0.1 else ("#F85149" if market_score < -0.1 else "#F0B429")
market_label = "BULLISH" if market_score > 0.1 else ("BEARISH" if market_score < -0.1 else "NEUTRAL")

best_basis_str = "—"
if not basis_df.empty and "basis_vs_ref" in basis_df.columns:
    best = basis_df.loc[basis_df["basis_vs_ref"].abs().idxmax()]
    best_basis_str = f"{best['location'][:18]} ({best['actual_basis']:+.0f}¢)"

kpis = [
    {
        "title":  "MARKET PULSE",
        "value":  market_label,
        "sub":    f"Score composite : {market_score:+.3f}",
        "color":  market_color,
        "icon":   "⚡",
        "border": market_color,
    },
    {
        "title":  "CRUSH MARGIN SOJA",
        "value":  f"${crush.get('net_crush_mt','—')}/MT" if crush else "—",
        "sub":    f"Percentile {crush.get('pctile','—')}% | ${crush.get('net_crush','—')}/bu" if crush else "Lance run_pipeline.py",
        "color":  "#3FB950" if crush and crush.get("pctile", 0) > 70 else "#F0B429",
        "icon":   "⚙️",
        "border": "#3FB950" if crush and crush.get("pctile", 0) > 70 else "#F0B429",
    },
    {
        "title":  "VAR 1J 99% PORTFOLIO",
        "value":  f"${var.get('total_var', 0):,.0f}" if var else "—",
        "sub":    f"{var.get('var_pct','—')}% du portfolio | Pos: ${var.get('total_pos',0):,.0f}" if var else "Lance risk_pipeline.py",
        "color":  "#3FB950" if var and var.get("var_pct", 0) < 3 else "#F0B429",
        "icon":   "⚠️",
        "border": "#3FB950" if var and var.get("var_pct", 0) < 3 else "#F85149",
    },
    {
        "title":  "BLÉ — 52W RANGE",
        "value":  f"{prices.get('wheat',{}).get('price','—')} ¢" if prices.get("wheat") else "—",
        "sub":    (f"L: {prices['wheat']['low_52w']:.0f}¢  ·  H: {prices['wheat']['high_52w']:.0f}¢  ·  1M: {prices['wheat']['chg_1m_pct']:+.1f}%"
                   if prices.get("wheat") else ""),
        "color":  "#58A6FF",
        "icon":   "🌾",
        "border": "#58A6FF",
    },
    {
        "title":  "BASIS ALERT",
        "value":  "Voir Pricing" if basis_df.empty else "Actif",
        "sub":    best_basis_str,
        "color":  "#F0B429",
        "icon":   "📐",
        "border": "#F0B429",
    },
]

kpi_cols = st.columns(5)
for col, kpi in zip(kpi_cols, kpis):
    with col:
        st.markdown(f"""
        <div style="background:#0D1117;border:1px solid #1C2333;
                    border-top:3px solid {kpi['border']};
                    border-radius:8px;padding:14px;min-height:90px">
            <div style="font-size:0.65em;color:#8B949E;font-weight:600;
                        letter-spacing:1px;margin-bottom:6px">
                {kpi['icon']} {kpi['title']}
            </div>
            <div style="font-size:1.25em;font-weight:700;color:{kpi['color']}">
                {kpi['value']}
            </div>
            <div style="font-size:0.72em;color:#8B949E;margin-top:4px;line-height:1.4">
                {kpi['sub']}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN GRID
# ══════════════════════════════════════════════════════════════════════════════
col_left, col_mid, col_right = st.columns([1.2, 1.6, 1.3])


# ── LEFT : Signals ────────────────────────────────────────────────────────────
with col_left:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #1C2333">
        ⚡ MARKET SIGNALS
    </div>
    """, unsafe_allow_html=True)

    comm_config = {
        "wheat":   ("🌾", "BLÉ CBOT",  "#F9A825"),
        "corn":    ("🌽", "MAÏS CBOT", "#58A6FF"),
        "soybean": ("🫘", "SOJA CBOT", "#3FB950"),
    }

    if not signals_df.empty:
        for _, row in signals_df.iterrows():
            c         = row.get("commodity", "")
            icon, label, accent = comm_config.get(c, ("", c.upper(), "#58A6FF"))
            score     = float(row.get("composite", 0))
            direction = str(row.get("direction", "NEUTRAL"))
            bar_pct   = int((score + 1) / 2 * 100)
            bar_col   = "#3FB950" if score > 0.1 else ("#F85149" if score < -0.1 else "#F0B429")
            sig_col   = bar_col

            mom  = int(row.get("momentum", 0))
            cot  = int(row.get("cot",      0))
            wthr = int(row.get("weather",  0))
            bdi_ = int(row.get("bdi",      0))

            def s_icon(v):
                return ('<span style="color:#3FB950;font-weight:700">▲</span>' if v > 0 else
                        '<span style="color:#F85149;font-weight:700">▼</span>' if v < 0 else
                        '<span style="color:#8B949E">—</span>')

            price_str = f"{prices.get(c, {}).get('price', '—')}" if c in prices else "—"
            chg1m     = prices.get(c, {}).get("chg_1m_pct", 0)
            chg_col   = price_color(chg1m)

            st.markdown(f"""
            <div style="background:#0D1117;border:1px solid #1C2333;border-radius:8px;
                        padding:14px;margin-bottom:10px;border-left:3px solid {accent}">
                <div style="display:flex;justify-content:space-between;
                            align-items:center;margin-bottom:8px">
                    <div>
                        <div style="font-size:0.95em;font-weight:700;color:#E6EDF3">
                            {icon} {label}
                        </div>
                        <div style="font-size:0.75em;color:#8B949E;margin-top:1px">
                            {price_str}¢ &nbsp;
                            <span style="color:{chg_col}">{chg1m:+.1f}% 1M</span>
                        </div>
                    </div>
                    <div style="text-align:right">
                        <div style="font-size:1.1em;font-weight:700;color:{sig_col}">
                            {score:+.3f}
                        </div>
                        <div style="font-size:0.7em;color:{sig_col};font-weight:600">
                            {direction.split()[0]}
                        </div>
                    </div>
                </div>
                <div style="background:#1C2333;border-radius:3px;height:4px;margin-bottom:10px">
                    <div style="background:{bar_col};width:{bar_pct}%;height:4px;border-radius:3px"></div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;
                            font-size:0.72em;text-align:center">
                    <div style="color:#8B949E">MOM<br>{s_icon(mom)}</div>
                    <div style="color:#8B949E">COT<br>{s_icon(cot)}</div>
                    <div style="color:#8B949E">WTH<br>{s_icon(wthr)}</div>
                    <div style="color:#8B949E">BDI<br>{s_icon(bdi_)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="font-size:0.68em;color:#8B949E;margin-top:6px;padding:8px;
                    background:#0D1117;border-radius:6px;border:1px solid #1C2333">
            Score : -1.0 (très bearish) → +1.0 (très bullish)<br>
            MOM=Momentum · COT=Positions fonds · WTH=Météo · BDI=Fret
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#0D1117;border:1px dashed #30363D;border-radius:8px;
                    padding:24px;text-align:center;color:#8B949E">
            <div style="font-size:1.5em;margin-bottom:8px">⚡</div>
            Lance <code>signals_pipeline.py</code><br>pour activer les signaux
        </div>
        """, unsafe_allow_html=True)


# ── MID : Spark Charts + Perf Table ──────────────────────────────────────────
with col_mid:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #1C2333">
        📊 PRICE OVERVIEW — 90 JOURS
    </div>
    """, unsafe_allow_html=True)

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    try:
        from config import DATA_RAW

        spark_cfg = [
            ("wheat",   "🌾 BLÉ",  "#F9A825"),
            ("corn",    "🌽 MAÏS", "#58A6FF"),
            ("soybean", "🫘 SOJA", "#3FB950"),
        ]

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05)

        for i, (c, label, color) in enumerate(spark_cfg, 1):
            path = DATA_RAW / f"{c}_futures.csv"
            if path.exists():
                df_c   = pd.read_csv(path, index_col="date", parse_dates=True)
                series = df_c["close"].dropna().iloc[-90:]
                ma20   = series.rolling(20).mean()

                fig.add_trace(go.Scatter(
                    x=series.index, y=series.values,
                    name=label,
                    line=dict(color=color, width=2),
                    fill="tozeroy",
                    fillcolor=hex_to_rgba(color, 0.07),
                    hovertemplate=f"<b>{label}</b><br>%{{x|%d %b %Y}}<br>%{{y:.1f}}¢<extra></extra>",
                ), row=i, col=1)

                fig.add_trace(go.Scatter(
                    x=ma20.index, y=ma20.values,
                    line=dict(color=hex_to_rgba(color, 0.5), width=1, dash="dot"),
                    showlegend=False, hoverinfo="skip",
                ), row=i, col=1)

                last_val = float(series.iloc[-1])
                chg_1m   = float((series.iloc[-1]/series.iloc[-22]-1)*100) if len(series)>21 else 0
                fig.add_annotation(
                    x=series.index[-1], y=last_val,
                    text=f"  {last_val:.0f}  {chg_1m:+.1f}%",
                    showarrow=False,
                    font=dict(size=10, color=color),
                    xanchor="left",
                    row=i, col=1
                )

        fig.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10, family="IBM Plex Mono"),
            showlegend=False, height=310,
            margin=dict(l=5, r=70, t=8, b=5),
        )
        for i in range(1, 4):
            fig.update_xaxes(gridcolor="#1C2333", showgrid=True, zeroline=False,
                             tickfont=dict(size=9), row=i, col=1)
            fig.update_yaxes(gridcolor="#1C2333", showgrid=True, zeroline=False,
                             tickfont=dict(size=9), row=i, col=1)

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    except Exception as e:
        st.warning(f"Graphiques non disponibles : {e}")

    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin:14px 0 8px 0">📈 PERFORMANCE COMPARÉE</div>
    """, unsafe_allow_html=True)

    _perf_rows = ""
    for key, (name, unit) in [
        ("wheat",   ("BLÉ",      "¢/bu")),
        ("corn",    ("MAÏS",     "¢/bu")),
        ("soybean", ("SOJA",     "¢/bu")),
        ("soyoil",  ("HUILE",    "¢/lb")),
        ("soymeal", ("TOURTEAU", "$/st")),
    ]:
        if key in prices:
            p       = prices[key]
            c1w     = price_color(p["chg_1w_pct"])
            c1m     = price_color(p["chg_1m_pct"])
            c3m     = price_color(p["chg_3m_pct"])
            trend   = "↗" if p["chg_1m_pct"] > 2 else ("↘" if p["chg_1m_pct"] < -2 else "→")
            trend_c = price_color(p["chg_1m_pct"])
            _perf_rows += (
                f'<tr style="border-bottom:1px solid #1C2333">'
                f'<td style="padding:7px 8px;color:#E6EDF3;font-weight:500">'
                f'{name} <span style="color:{trend_c}">{trend}</span></td>'
                f'<td style="padding:7px 8px;color:#E6EDF3;text-align:right;'
                f'font-family:\'IBM Plex Mono\',monospace">{p["price"]:.1f}</td>'
                f'<td style="padding:7px 8px;color:{c1w};text-align:right;'
                f'font-family:\'IBM Plex Mono\',monospace">{p["chg_1w_pct"]:+.1f}%</td>'
                f'<td style="padding:7px 8px;color:{c1m};text-align:right;'
                f'font-family:\'IBM Plex Mono\',monospace">{p["chg_1m_pct"]:+.1f}%</td>'
                f'<td style="padding:7px 8px;color:{c3m};text-align:right;'
                f'font-family:\'IBM Plex Mono\',monospace">{p["chg_3m_pct"]:+.1f}%</td>'
                f'</tr>'
            )

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:0.82em">
        <thead>
            <tr style="border-bottom:1px solid #30363D">
                <th style="padding:6px 8px;color:#8B949E;font-weight:500;text-align:left">Commodity</th>
                <th style="padding:6px 8px;color:#8B949E;font-weight:500;text-align:right">Prix</th>
                <th style="padding:6px 8px;color:#8B949E;font-weight:500;text-align:right">1S</th>
                <th style="padding:6px 8px;color:#8B949E;font-weight:500;text-align:right">1M</th>
                <th style="padding:6px 8px;color:#8B949E;font-weight:500;text-align:right">3M</th>
            </tr>
        </thead>
        <tbody>{_perf_rows}</tbody>
    </table>
    """, unsafe_allow_html=True)


# ── RIGHT : Trade Ideas ───────────────────────────────────────────────────────
with col_right:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #1C2333">
        🤖 TRADE IDEAS — LLM (GROQ/LLAMA)
    </div>
    """, unsafe_allow_html=True)

    ideas = load_trade_ideas()

    if ideas:
        summary = ideas.get("market_summary", "")
        if summary:
            st.markdown(f"""
            <div style="background:#0D1117;border:1px solid #1C2333;
                        border-left:3px solid #58A6FF;border-radius:6px;
                        padding:10px 12px;margin-bottom:12px;
                        font-size:0.8em;color:#C9D1D9;line-height:1.5">
                {summary[:200]}…
            </div>
            """, unsafe_allow_html=True)

        # Daily bias — construit en string, UN SEUL st.markdown
        bias       = ideas.get("daily_bias", {})
        bias_colors = {"bullish": "#3FB950", "bearish": "#F85149", "neutral": "#F0B429"}
        _bias_html  = ""
        for commodity, b in bias.items():
            bc    = bias_colors.get(b, "#8B949E")
            arrow = "▲" if b == "bullish" else ("▼" if b == "bearish" else "—")
            _bias_html += (
                f'<div style="flex:1;text-align:center;padding:6px;'
                f'background:{hex_to_rgba(bc,0.1)};'
                f'border:1px solid {hex_to_rgba(bc,0.3)};border-radius:6px">'
                f'<div style="font-size:0.65em;color:#8B949E">{commodity.upper()}</div>'
                f'<div style="color:{bc};font-weight:700;font-size:0.85em">{arrow} {b.upper()}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="display:flex;gap:6px;margin-bottom:12px">{_bias_html}</div>',
            unsafe_allow_html=True
        )

        risk = ideas.get("key_risk_today", "")
        if risk:
            st.markdown(f"""
            <div style="background:#1A0F0F;border:1px solid #3D1F1F;
                        border-radius:6px;padding:8px 12px;
                        margin-bottom:12px;font-size:0.78em">
                <span style="color:#F85149;font-weight:600">⚠ KEY RISK &nbsp;</span>
                <span style="color:#C9D1D9">{risk[:110]}</span>
            </div>
            """, unsafe_allow_html=True)

        type_colors = {
            "futures": "#58A6FF", "spread": "#F0B429",
            "physical": "#3FB950", "options": "#E040FB",
        }

        for idea in ideas.get("trade_ideas", [])[:3]:
            direction  = idea.get("direction", "")
            is_long    = "long" in direction.lower()
            dir_color  = "#3FB950" if is_long else "#F85149"
            dir_label  = "▲ LONG" if is_long else "▼ SHORT"
            conviction = idea.get("conviction", "medium")
            conv_colors = {"high": "#3FB950", "medium": "#F0B429", "low": "#8B949E"}
            conv_color  = conv_colors.get(conviction, "#8B949E")
            exec_data   = idea.get("execution", {})
            t_type      = idea.get("type", "futures")
            t_color     = type_colors.get(t_type, "#58A6FF")
            primary     = idea.get("rationale", {}).get("primary_catalyst", "")[:85]
            fund_driver = idea.get("rationale", {}).get("fundamental_driver", "")[:60]

            st.markdown(f"""
            <div style="background:#0D1117;border:1px solid #1C2333;
                        border-radius:8px;padding:12px;margin-bottom:10px;
                        border-left:3px solid {dir_color}">
                <div style="display:flex;justify-content:space-between;
                            align-items:flex-start;margin-bottom:6px">
                    <div style="font-size:0.85em;font-weight:700;color:#E6EDF3;
                                flex:1;margin-right:8px;line-height:1.3">
                        {idea.get('title','')[:38]}
                    </div>
                    <div style="font-size:0.7em;color:{t_color};font-weight:600;
                                background:{hex_to_rgba(t_color,0.15)};
                                padding:2px 7px;border-radius:10px;white-space:nowrap">
                        {t_type.upper()}
                    </div>
                </div>
                <div style="font-size:0.76em;color:#8B949E;margin-bottom:6px;line-height:1.4">
                    {primary}
                </div>
                <div style="font-size:0.72em;color:#8B949E;margin-bottom:8px;font-style:italic">
                    {fund_driver}
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">
                    <span style="font-size:0.72em;color:{dir_color};font-weight:700;
                                 background:{hex_to_rgba(dir_color,0.15)};
                                 padding:2px 8px;border-radius:10px">{dir_label}</span>
                    <span style="font-size:0.72em;color:{conv_color};
                                 background:{hex_to_rgba(conv_color,0.12)};
                                 padding:2px 8px;border-radius:10px">{conviction.upper()}</span>
                    <span style="font-size:0.72em;color:#8B949E;background:#1C2333;
                                 padding:2px 8px;border-radius:10px">
                        R/R {exec_data.get('risk_reward','?')}
                    </span>
                </div>
                <div style="border-top:1px solid #1C2333;padding-top:8px;
                            display:flex;justify-content:space-between;font-size:0.72em">
                    <span style="color:#8B949E">Entry
                        <b style="color:#E6EDF3">{exec_data.get('entry_level','?')[:16]}</b>
                    </span>
                    <span style="color:#8B949E">Stop
                        <b style="color:#F85149">{exec_data.get('stop_loss','?')[:14]}</b>
                    </span>
                    <span style="color:#8B949E">T1
                        <b style="color:#3FB950">{exec_data.get('target_1','?')[:12]}</b>
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🔄 Régénérer les idées", use_container_width=True):
            with st.spinner("Appel API Groq/Llama..."):
                try:
                    from module_5_llm.generators.trade_idea_generator import generate_trade_ideas
                    generate_trade_ideas(save=True)
                    st.success("✅ Nouvelles idées générées !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
    else:
        st.markdown("""
        <div style="background:#0D1117;border:1px dashed #30363D;border-radius:8px;
                    padding:30px;text-align:center;color:#8B949E">
            <div style="font-size:2em;margin-bottom:8px">🤖</div>
            Lance <code>llm_pipeline.py</code><br>pour générer les trade ideas
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# BOTTOM ROW
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="border-top:1px solid #1C2333;margin:24px 0 16px 0"></div>
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">📡 MARKET CONTEXT</div>
""", unsafe_allow_html=True)

bot_cols = st.columns(3)

# ── Calendrier Agricole ───────────────────────────────────────────────────────
with bot_cols[0]:
    st.markdown("""
    <div style="font-size:0.7em;color:#8B949E;font-weight:600;letter-spacing:0.8px;
                margin-bottom:8px">🗓️ CALENDRIER AGRICOLE</div>
    """, unsafe_allow_html=True)

    month_now = datetime.now().month
    seasonal_events = {
        1:  ("🇧🇷", "wheat",   "Récolte soja Brésil — 1ère coupe"),
        2:  ("🇧🇷", "soybean", "Pic récolte soja Brésil"),
        3:  ("🇦🇷", "soybean", "Récolte soja Argentine"),
        4:  ("🇺🇸", "corn",    "Semis maïs US — début"),
        5:  ("🇺🇸", "corn",    "Semis maïs US — pic tension"),
        6:  ("🇺🇸", "corn",    "Pollinisation maïs — fenêtre critique"),
        7:  ("🇺🇸", "soybean", "Pod fill soja — stress hydrique"),
        8:  ("🇺🇦", "wheat",   "Récolte blé Ukraine / Russie"),
        9:  ("🇺🇸", "corn",    "Récolte maïs US — début"),
        10: ("🇺🇸", "corn",    "Récolte maïs US — pic bearish"),
        11: ("🇺🇸", "wheat",   "Fin récolte — stocks au maximum"),
        12: ("🇧🇷", "soybean", "Semis soja Brésil"),
    }
    commodity_colors = {"wheat": "#F9A825", "corn": "#58A6FF", "soybean": "#3FB950"}

    _cal_html = ""
    for m in [month_now - 1, month_now, month_now + 1]:
        m_adj      = ((m - 1) % 12) + 1
        flag, commodity, event = seasonal_events.get(m_adj, ("", "wheat", "—"))
        is_current = (m == month_now)
        c_color    = commodity_colors.get(commodity, "#8B949E")
        mname      = datetime(2024, m_adj, 1).strftime("%b").upper()
        now_tag    = ' <span style="color:#58A6FF;font-weight:600">← MAINTENANT</span>' if is_current else ""
        _cal_html += (
            f'<div style="background:{"#0F1A1F" if is_current else "#0D1117"};'
            f'border:1px solid {"#58A6FF44" if is_current else "#1C2333"};'
            f'border-left:3px solid {c_color if is_current else "#1C2333"};'
            f'border-radius:6px;padding:8px 12px;margin-bottom:6px;'
            f'display:flex;align-items:center;gap:10px">'
            f'<div style="font-size:0.82em;color:#58A6FF;font-weight:700;min-width:32px">{mname}</div>'
            f'<div style="font-size:0.72em;color:{"#E6EDF3" if is_current else "#8B949E"};line-height:1.3">'
            f'{flag} {event}{now_tag}</div>'
            f'</div>'
        )
    st.markdown(_cal_html, unsafe_allow_html=True)


# ── Baltic ────────────────────────────────────────────────────────────────────
with bot_cols[1]:
    st.markdown("""
    <div style="font-size:0.7em;color:#8B949E;font-weight:600;letter-spacing:0.8px;
                margin-bottom:8px">🚢 BALTIC INDICES — FRET MARITIME</div>
    """, unsafe_allow_html=True)

    try:
        from config import DATA_RAW as DR
        _balt_html  = ""
        any_baltic  = False
        for code, label, color in [
            ("bdi",  "Baltic Dry Index", "#58A6FF"),
            ("bpi",  "Panamax (Grains)", "#F9A825"),
            ("bsi",  "Supramax",         "#3FB950"),
            ("bhsi", "Handysize",        "#FF9800"),
        ]:
            path = DR / f"baltic_{code}.csv"
            if path.exists():
                df_b  = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
                vals  = df_b["close"].dropna()
                last  = float(vals.iloc[-1])
                prev  = float(vals.iloc[-6])  if len(vals) > 5  else last
                prev1m= float(vals.iloc[-22]) if len(vals) > 21 else last
                chg   = ((last / prev)   - 1) * 100
                chg1m = ((last / prev1m) - 1) * 100
                c     = "#3FB950" if chg > 0 else "#F85149"
                any_baltic = True
                _balt_html += (
                    f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;'
                    f'padding:8px 12px;margin-bottom:6px;'
                    f'display:flex;justify-content:space-between;align-items:center">'
                    f'<div>'
                    f'<div style="font-size:0.68em;color:#8B949E">{label}</div>'
                    f'<div style="font-size:1em;font-weight:700;color:{color};'
                    f'font-family:\'IBM Plex Mono\',monospace">{last:,.0f}</div>'
                    f'</div>'
                    f'<div style="text-align:right">'
                    f'<div style="color:{c};font-size:0.82em;font-weight:600">{chg:+.1f}% 1S</div>'
                    f'<div style="color:#8B949E;font-size:0.72em">{chg1m:+.1f}% 1M</div>'
                    f'</div></div>'
                )
        if any_baltic:
            st.markdown(_balt_html, unsafe_allow_html=True)
        else:
            st.info("Lance `freight_pipeline.py` pour les données Baltic.")
    except Exception as e:
        st.warning(f"Baltic non disponible : {e}")


# ── Stress Scenarios ──────────────────────────────────────────────────────────
with bot_cols[2]:
    st.markdown("""
    <div style="font-size:0.7em;color:#8B949E;font-weight:600;letter-spacing:0.8px;
                margin-bottom:8px">🔥 TOP STRESS SCENARIOS</div>
    """, unsafe_allow_html=True)

    try:
        from config import DATA_PROCESSED as DP
        path = DP / "stress_test_results.csv"
        if path.exists():
            df_s     = pd.read_csv(path).sort_values("total_pnl")
            shown    = pd.concat([df_s.head(2), df_s.tail(2)])
            _str_html = ""
            for _, row in shown.iterrows():
                pnl     = row["total_pnl"]
                c       = "#F85149" if pnl < 0 else "#3FB950"
                icon    = "▼" if pnl < 0 else "▲"
                name    = row["scenario"].replace("_", " ").title()[:26]
                stype   = row.get("type", "")
                badge_c = "#F85149" if stype == "historical" else "#F0B429"
                _str_html += (
                    f'<div style="background:#0D1117;border:1px solid #1C2333;'
                    f'border-radius:6px;padding:8px 12px;margin-bottom:6px">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div>'
                    f'<div style="font-size:0.75em;color:#E6EDF3">{name}</div>'
                    f'<div style="font-size:0.65em;color:{badge_c};margin-top:1px">{stype.upper()}</div>'
                    f'</div>'
                    f'<div style="color:{c};font-size:0.9em;font-weight:700;'
                    f'white-space:nowrap;font-family:\'IBM Plex Mono\',monospace">'
                    f'{icon} ${abs(pnl):,.0f}</div>'
                    f'</div></div>'
                )
            st.markdown(_str_html, unsafe_allow_html=True)

            worst_pnl = df_s["total_pnl"].min()
            best_pnl  = df_s["total_pnl"].max()
            st.markdown(f"""
            <div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;
                        padding:8px 12px;font-size:0.72em;color:#8B949E;margin-top:4px">
                Worst: <span style="color:#F85149">${worst_pnl:+,.0f}</span>
                &nbsp;|&nbsp;
                Best: <span style="color:#3FB950">${best_pnl:+,.0f}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Lance `risk_pipeline.py` pour les stress tests.")
    except Exception as e:
        st.warning(f"Stress data : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="border-top:1px solid #1C2333;margin-top:28px;padding-top:14px;
            display:flex;justify-content:space-between;align-items:center;
            flex-wrap:wrap;gap:8px">
    <div style="font-size:0.72em;color:#8B949E">
        📡 Sources : CME/CBOT (yfinance) · CFTC COT Report ·
        Open-Meteo (ERA5) · Baltic Exchange (Stooq) · USDA PSD
    </div>
    <div style="font-size:0.72em;color:#8B949E">
        AgroTrade Intelligence v1.0 &nbsp;·&nbsp; Données J-1 &nbsp;·&nbsp;
        <span style="color:#3FB950">● {datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
    </div>
</div>
""", unsafe_allow_html=True)