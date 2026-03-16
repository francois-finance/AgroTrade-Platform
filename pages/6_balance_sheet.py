"""
Balance Sheet — Supply & Demand Monitor
Sources : USDA PSD (données réelles ou démo), calculs internes
Données : Production, consommation, stocks, exports, S/U ratio par pays
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Balance Sheet", page_icon="📒", layout="wide")
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


# ══════════════════════════════════════════════════════════════════════════════
# DONNÉES WASDE — Balance sheet mondiale
# Source : USDA WASDE (données réelles si clé API, sinon données historiques)
# Unités : millions de tonnes métriques (MMT)
# ══════════════════════════════════════════════════════════════════════════════

WASDE_DATA = {
    "wheat": {
        "label": "🌾 Blé",
        "color": "#F9A825",
        "unit": "MMT",
        "years": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        "production":   [765.8, 775.7, 781.0, 779.0, 785.6, 790.0, 795.2],
        "consumption":  [752.5, 762.4, 784.1, 789.0, 795.8, 799.5, 802.0],
        "ending_stocks":[277.0, 290.3, 287.2, 277.2, 267.0, 257.5, 250.7],
        "exports":      [189.0, 201.4, 203.5, 205.8, 198.0, 205.0, 208.0],
        "top_exporters": {
            "Russie":     [32.5, 39.1, 37.0, 33.0, 45.5, 48.0, 50.0],
            "UE-27":      [37.0, 34.7, 35.0, 32.0, 34.0, 35.0, 36.0],
            "Australie":  [10.1, 19.8, 26.5, 25.5, 19.0, 26.0, 24.0],
            "US":         [27.3, 27.1, 23.6, 21.7, 21.0, 22.5, 23.0],
            "Canada":     [24.4, 26.7, 17.0, 24.0, 22.0, 25.0, 26.0],
            "Ukraine":    [21.0, 18.1, 20.0, 17.5, 18.0, 15.0, 16.0],
        },
        "top_importers": {
            "Égypte":     [13.0, 13.2, 12.5, 10.5, 12.5, 13.0, 13.5],
            "Indonésie":  [10.6, 10.3, 10.5, 11.0, 11.5, 12.0, 12.2],
            "Algérie":    [ 8.2,  8.5,  8.5,  8.8,  9.0,  9.5,  9.5],
            "Turquie":    [ 8.0,  8.2,  8.0,  7.5,  9.0,  9.0,  9.0],
            "Brésil":     [ 7.0,  7.2,  7.5,  8.0,  8.5,  8.8,  9.0],
        },
        "wasde_notes": "Russie domine les exports (30%+ de part de marché). Mer Noire = zone de risque géopolitique majeure.",
    },
    "corn": {
        "label": "🌽 Maïs",
        "color": "#58A6FF",
        "unit": "MMT",
        "years": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        "production":   [1115.0, 1125.5, 1207.5, 1161.7, 1228.7, 1220.0, 1235.0],
        "consumption":  [1130.0, 1139.8, 1200.3, 1175.0, 1210.5, 1215.0, 1225.0],
        "ending_stocks":[ 299.6,  285.4,  292.6,  279.3,  297.5,  302.5,  312.5],
        "exports":      [ 184.0,  190.8,  199.7,  187.0,  184.0,  190.0,  192.0],
        "top_exporters": {
            "US":         [48.9, 59.2, 63.9, 58.8, 48.2, 52.0, 54.0],
            "Brésil":     [43.0, 34.8, 43.0, 47.0, 54.0, 50.0, 52.0],
            "Argentine":  [37.0, 41.0, 39.0, 34.0, 34.0, 30.0, 32.0],
            "Ukraine":    [29.0, 28.0, 27.5, 15.5, 20.0, 18.0, 19.0],
        },
        "top_importers": {
            "Chine":      [7.6, 11.3, 28.5, 20.3, 18.0, 16.0, 15.0],
            "UE-27":      [18.5, 16.8, 14.7, 15.4, 14.0, 14.5, 14.0],
            "Mexique":    [16.5, 17.2, 17.5, 16.8, 17.0, 17.5, 17.5],
            "Japon":      [15.5, 15.8, 15.3, 14.7, 15.0, 15.0, 15.2],
            "Corée du Sud":[11.5, 11.8, 11.2, 10.5, 11.0, 11.2, 11.5],
        },
        "wasde_notes": "Brésil en forte progression — dépasse US sur certaines années. Chine = variable clé de la demande mondiale.",
    },
    "soybean": {
        "label": "🫘 Soja",
        "color": "#3FB950",
        "unit": "MMT",
        "years": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        "production":   [336.1, 362.8, 383.9, 355.4, 390.7, 395.0, 408.0],
        "consumption":  [334.5, 358.3, 376.8, 368.9, 382.0, 390.0, 400.0],
        "ending_stocks":[ 98.3, 102.8, 109.9,  96.4, 105.1, 110.1, 118.1],
        "exports":      [ 163.5, 174.5, 162.0, 158.8, 172.5, 175.0, 180.0],
        "top_exporters": {
            "Brésil":     [74.6, 83.0, 87.0, 79.0, 99.0, 98.0, 104.0],
            "US":         [46.4, 61.7, 59.4, 55.5, 48.4, 50.0, 52.0],
            "Argentine":  [ 7.2,  4.8,  4.5,  5.5,  7.0,  8.0,  9.0],
            "Paraguay":   [ 5.5,  6.2,  6.0,  5.8,  6.5,  7.0,  7.5],
        },
        "top_importers": {
            "Chine":      [85.1, 100.3, 96.5, 91.1, 99.4, 102.0, 105.0],
            "UE-27":      [17.5, 15.8, 14.5, 13.9, 14.0, 14.5, 15.0],
            "Mexique":    [ 4.5,  4.8,  5.0,  5.2,  5.5,  5.8,  6.0],
            "Japon":      [ 3.2,  3.3,  3.1,  3.0,  3.2,  3.3,  3.4],
        },
        "wasde_notes": "Chine représente ~60% des imports mondiaux. Brésil est devenu le 1er exporteur mondial. Crush margin = indicateur demande clé.",
    },
}


def compute_su_ratio(data: dict) -> list:
    """Calcule le stocks-to-use ratio = stocks finaux / consommation × 100"""
    return [
        round(s / c * 100, 1)
        for s, c in zip(data["ending_stocks"], data["consumption"])
    ]


def su_signal(su: float) -> tuple:
    """Signal de prix basé sur le S/U ratio"""
    if su < 12:
        return "#F85149", "🔴 TRÈS TENDU", "Marché très tendu — fort potentiel haussier"
    elif su < 18:
        return "#F0B429", "🟠 TENDU", "Marché tendu — biais haussier"
    elif su < 25:
        return "#8B949E", "⚪ ÉQUILIBRÉ", "Marché équilibré"
    elif su < 35:
        return "#3FB950", "🟡 BIEN APPRO.", "Marché bien approvisionné — biais baissier"
    else:
        return "#58A6FF", "🔵 ABONDANT", "Stocks abondants — pression baissière"


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 0 18px 0;border-bottom:1px solid #1C2333;margin-bottom:20px">
    <div>
        <span style="font-size:1.5em;font-weight:800;color:#E6EDF3">📒 Balance Sheet</span>
        <div style="font-size:0.78em;color:#8B949E;margin-top:3px">
            Supply · Demand · Stocks Mondiaux · S/U Ratio · Flux Commerciaux
        </div>
    </div>
    <div style="text-align:right">
        <div style="font-size:0.75em;color:#8B949E">{datetime.now().strftime('%d %b %Y')}</div>
        <div style="font-size:0.68em;color:#8B949E;margin-top:2px">
            Source : USDA WASDE · Données en MMT
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Sélecteur commodité ───────────────────────────────────────────────────────
commodity = st.selectbox(
    "Commodité",
    list(WASDE_DATA.keys()),
    format_func=lambda x: WASDE_DATA[x]["label"],
    key="bs_commodity"
)

d     = WASDE_DATA[commodity]
color = d["color"]
years = d["years"]
su    = compute_su_ratio(d)
su_latest = su[-1]
su_col, su_label, su_desc = su_signal(su_latest)

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════════════════════════════════════
k1, k2, k3, k4, k5 = st.columns(5)

prod_chg  = d["production"][-1] - d["production"][-2]
cons_chg  = d["consumption"][-1] - d["consumption"][-2]
stock_chg = d["ending_stocks"][-1] - d["ending_stocks"][-2]
su_chg    = su[-1] - su[-2]

k1.metric("🌾 Production " + str(years[-1]),
          f"{d['production'][-1]:.1f} MMT",
          f"{prod_chg:+.1f} MMT vs {years[-2]}")
k2.metric("🍽️ Consommation",
          f"{d['consumption'][-1]:.1f} MMT",
          f"{cons_chg:+.1f} MMT vs {years[-2]}")
k3.metric("🏭 Stocks finaux",
          f"{d['ending_stocks'][-1]:.1f} MMT",
          f"{stock_chg:+.1f} MMT vs {years[-2]}")
k4.metric("📦 Exports mondiaux",
          f"{d['exports'][-1]:.1f} MMT",
          f"{d['exports'][-1] - d['exports'][-2]:+.1f} MMT")
k5.metric("⚖️ S/U Ratio",
          f"{su_latest:.1f}%",
          f"{su_chg:+.1f}pp vs {years[-2]}")

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

# Signal S/U
st.markdown(
    f'<div style="background:{hex_to_rgba(su_col,0.1)};border:1px solid {su_col};'
    f'border-radius:8px;padding:12px 18px;margin-bottom:20px;'
    f'display:flex;justify-content:space-between;align-items:center">'
    f'<div>'
    f'<span style="color:{su_col};font-weight:700;font-size:1.05em">'
    f'{su_label} — S/U Ratio: {su_latest:.1f}%</span>'
    f'<div style="color:#C9D1D9;font-size:0.82em;margin-top:3px">{su_desc}</div>'
    f'</div>'
    f'<div style="text-align:right;font-size:0.78em;color:#8B949E">'
    f'Seuils : &lt;12% critique · 12-18% tendu · 18-25% équilibré · &gt;25% abondant'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# ROW 1 : Supply/Demand + S/U Ratio historique
# ══════════════════════════════════════════════════════════════════════════════
col_sd, col_su = st.columns([1.4, 1])

with col_sd:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">📊 PRODUCTION · CONSOMMATION · STOCKS (MMT)</div>
    """, unsafe_allow_html=True)

    fig_sd = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.06, row_heights=[0.65, 0.35],
    )

    # Production (barres)
    fig_sd.add_trace(go.Bar(
        x=years, y=d["production"],
        name="Production",
        marker_color=hex_to_rgba(color, 0.7),
    ), row=1, col=1)

    # Consommation (ligne)
    fig_sd.add_trace(go.Scatter(
        x=years, y=d["consumption"],
        name="Consommation",
        mode="lines+markers",
        line=dict(color="#F85149", width=2.5),
        marker=dict(size=7),
    ), row=1, col=1)

    # Stocks (ligne secondaire)
    fig_sd.add_trace(go.Scatter(
        x=years, y=d["ending_stocks"],
        name="Stocks finaux",
        mode="lines+markers",
        line=dict(color="#F0B429", width=2, dash="dot"),
        marker=dict(size=6),
    ), row=1, col=1)

    # Balance (prod - conso)
    balance = [p - c for p, c in zip(d["production"], d["consumption"])]
    bal_colors = [hex_to_rgba("#3FB950", 0.8) if b > 0 else hex_to_rgba("#F85149", 0.8)
                  for b in balance]
    fig_sd.add_trace(go.Bar(
        x=years, y=balance,
        name="Balance (Prod-Conso)",
        marker_color=bal_colors,
    ), row=2, col=1)
    fig_sd.add_hline(y=0, line_color="white", opacity=0.2, row=2, col=1)

    fig_sd.update_layout(
        paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
        font=dict(color="#8B949E", size=10),
        height=380,
        margin=dict(l=5, r=5, t=10, b=5),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9),
                    orientation="h", y=1.05),
        barmode="overlay",
    )
    for r in [1, 2]:
        fig_sd.update_xaxes(gridcolor="#1C2333", row=r, col=1)
        fig_sd.update_yaxes(gridcolor="#1C2333", row=r, col=1)
    st.plotly_chart(fig_sd, use_container_width=True,
                    config={"displayModeBar": False})

with col_su:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">⚖️ STOCKS-TO-USE RATIO — INDICATEUR FONDAMENTAL CLÉ</div>
    """, unsafe_allow_html=True)

    # Couleur par niveau
    su_bar_colors = []
    for v in su:
        c_su, _, _ = su_signal(v)
        su_bar_colors.append(hex_to_rgba(c_su, 0.75))

    fig_su = go.Figure()

    # Zones de référence
    fig_su.add_hrect(y0=0,  y1=12, fillcolor="rgba(248,81,73,0.08)",
                     line_width=0, annotation_text="Zone critique",
                     annotation_position="right",
                     annotation_font=dict(color="#F85149", size=9))
    fig_su.add_hrect(y0=12, y1=18, fillcolor="rgba(240,180,41,0.06)",
                     line_width=0, annotation_text="Zone tendue",
                     annotation_position="right",
                     annotation_font=dict(color="#F0B429", size=9))
    fig_su.add_hrect(y0=25, y1=50, fillcolor="rgba(63,185,80,0.05)",
                     line_width=0, annotation_text="Zone abondante",
                     annotation_position="right",
                     annotation_font=dict(color="#3FB950", size=9))

    fig_su.add_trace(go.Bar(
        x=years, y=su,
        marker_color=su_bar_colors,
        text=[f"{v:.1f}%" for v in su],
        textposition="outside",
        textfont=dict(size=10),
        name="S/U Ratio",
    ))

    # Ligne moyenne historique
    su_avg = np.mean(su)
    fig_su.add_hline(
        y=su_avg, line_dash="dash", line_color="white",
        opacity=0.3,
        annotation_text=f"Moy: {su_avg:.1f}%",
        annotation_font=dict(color="white", size=9),
    )

    fig_su.update_layout(
        paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
        font=dict(color="#8B949E", size=10),
        height=280,
        margin=dict(l=5, r=80, t=10, b=5),
        yaxis=dict(gridcolor="#1C2333", title="S/U (%)"),
        xaxis=dict(gridcolor="#1C2333"),
        showlegend=False,
    )
    st.plotly_chart(fig_su, use_container_width=True,
                    config={"displayModeBar": False})

    # Tableau S/U par année
    _su_rows = ""
    for i, (y, s) in enumerate(zip(years, su)):
        sc, sl, _ = su_signal(s)
        is_last   = (i == len(years) - 1)
        _su_rows += (
            f'<tr style="border-bottom:1px solid #1C2333;'
            f'{"background:#0F1A1F" if is_last else ""}">'
            f'<td style="padding:5px 10px;color:{"#58A6FF" if is_last else "#8B949E"};'
            f'font-weight:{"700" if is_last else "400"}">'
            f'{"→ " if is_last else ""}{y}</td>'
            f'<td style="padding:5px 10px;color:#E6EDF3;text-align:right;'
            f'font-family:IBM Plex Mono,monospace">'
            f'{d["ending_stocks"][i]:.1f} MMT</td>'
            f'<td style="padding:5px 10px;color:{sc};text-align:right;font-weight:700">'
            f'{s:.1f}%</td>'
            f'<td style="padding:5px 10px;color:{sc};font-size:0.8em">{sl}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:0.82em;margin-top:8px">'
        f'<thead><tr style="border-bottom:1px solid #30363D">'
        f'<th style="padding:5px 10px;color:#8B949E;font-weight:500;text-align:left">Année</th>'
        f'<th style="padding:5px 10px;color:#8B949E;font-weight:500;text-align:right">Stocks</th>'
        f'<th style="padding:5px 10px;color:#8B949E;font-weight:500;text-align:right">S/U</th>'
        f'<th style="padding:5px 10px;color:#8B949E;font-weight:500;text-align:left">Signal</th>'
        f'</tr></thead>'
        f'<tbody>{_su_rows}</tbody>'
        f'</table>',
        unsafe_allow_html=True
    )

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# ROW 2 : Top Exportateurs + Top Importateurs
# ══════════════════════════════════════════════════════════════════════════════
col_exp, col_imp = st.columns(2)

with col_exp:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">🚢 TOP EXPORTATEURS (MMT)</div>
    """, unsafe_allow_html=True)

    exp_colors = ["#F9A825", "#58A6FF", "#3FB950", "#E040FB",
                  "#FF9800", "#F85149", "#00BCD4"]
    fig_exp = go.Figure()

    for i, (country, vals) in enumerate(d["top_exporters"].items()):
        fig_exp.add_trace(go.Scatter(
            x=years, y=vals,
            name=country,
            mode="lines+markers",
            line=dict(color=exp_colors[i % len(exp_colors)], width=2),
            marker=dict(size=6),
        ))

    fig_exp.update_layout(
        paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
        font=dict(color="#8B949E", size=10),
        height=280,
        margin=dict(l=5, r=5, t=10, b=5),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9),
                    orientation="h", y=-0.2),
        yaxis=dict(gridcolor="#1C2333", title="MMT"),
        xaxis=dict(gridcolor="#1C2333"),
    )
    st.plotly_chart(fig_exp, use_container_width=True,
                    config={"displayModeBar": False})

    # Part de marché dernière année
    total_exp = sum(v[-1] for v in d["top_exporters"].values())
    _exp_rows = ""
    sorted_exp = sorted(d["top_exporters"].items(),
                        key=lambda x: x[1][-1], reverse=True)
    for i, (country, vals) in enumerate(sorted_exp):
        share = vals[-1] / d["exports"][-1] * 100
        chg   = vals[-1] - vals[-2]
        rank_col = exp_colors[i % len(exp_colors)]
        _exp_rows += (
            f'<tr style="border-bottom:1px solid #1C2333">'
            f'<td style="padding:5px 8px;color:{rank_col};font-weight:700">#{i+1}</td>'
            f'<td style="padding:5px 8px;color:#E6EDF3">{country}</td>'
            f'<td style="padding:5px 8px;color:#E6EDF3;text-align:right;'
            f'font-family:IBM Plex Mono,monospace">{vals[-1]:.1f}</td>'
            f'<td style="padding:5px 8px;color:{pc(chg)};text-align:right;'
            f'font-family:IBM Plex Mono,monospace">{chg:+.1f}</td>'
            f'<td style="padding:5px 8px;color:#8B949E;text-align:right">'
            f'{share:.1f}%</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:0.82em">'
        f'<thead><tr style="border-bottom:1px solid #30363D">'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500">#</th>'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:left">Pays</th>'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">'
        f'MMT {years[-1]}</th>'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">YoY</th>'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">Part</th>'
        f'</tr></thead>'
        f'<tbody>{_exp_rows}</tbody>'
        f'</table>',
        unsafe_allow_html=True
    )

with col_imp:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">📥 TOP IMPORTATEURS (MMT)</div>
    """, unsafe_allow_html=True)

    imp_colors = ["#F85149", "#E040FB", "#FF9800", "#00BCD4", "#8BC34A", "#9C27B0"]
    fig_imp = go.Figure()

    for i, (country, vals) in enumerate(d["top_importers"].items()):
        fig_imp.add_trace(go.Scatter(
            x=years, y=vals,
            name=country,
            mode="lines+markers",
            line=dict(color=imp_colors[i % len(imp_colors)], width=2),
            marker=dict(size=6),
        ))

    fig_imp.update_layout(
        paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
        font=dict(color="#8B949E", size=10),
        height=280,
        margin=dict(l=5, r=5, t=10, b=5),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9),
                    orientation="h", y=-0.2),
        yaxis=dict(gridcolor="#1C2333", title="MMT"),
        xaxis=dict(gridcolor="#1C2333"),
    )
    st.plotly_chart(fig_imp, use_container_width=True,
                    config={"displayModeBar": False})

    # Part de marché importateurs
    total_imp = d["exports"][-1]
    _imp_rows = ""
    sorted_imp = sorted(d["top_importers"].items(),
                        key=lambda x: x[1][-1], reverse=True)
    for i, (country, vals) in enumerate(sorted_imp):
        share = vals[-1] / total_imp * 100
        chg   = vals[-1] - vals[-2]
        rank_col = imp_colors[i % len(imp_colors)]
        _imp_rows += (
            f'<tr style="border-bottom:1px solid #1C2333">'
            f'<td style="padding:5px 8px;color:{rank_col};font-weight:700">#{i+1}</td>'
            f'<td style="padding:5px 8px;color:#E6EDF3">{country}</td>'
            f'<td style="padding:5px 8px;color:#E6EDF3;text-align:right;'
            f'font-family:IBM Plex Mono,monospace">{vals[-1]:.1f}</td>'
            f'<td style="padding:5px 8px;color:{pc(chg)};text-align:right;'
            f'font-family:IBM Plex Mono,monospace">{chg:+.1f}</td>'
            f'<td style="padding:5px 8px;color:#8B949E;text-align:right">'
            f'{share:.1f}%</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:0.82em">'
        f'<thead><tr style="border-bottom:1px solid #30363D">'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500">#</th>'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:left">Pays</th>'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">'
        f'MMT {years[-1]}</th>'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">YoY</th>'
        f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">Part</th>'
        f'</tr></thead>'
        f'<tbody>{_imp_rows}</tbody>'
        f'</table>',
        unsafe_allow_html=True
    )

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# ROW 3 : Balance Sheet complète + Notes WASDE
# ══════════════════════════════════════════════════════════════════════════════
col_bs, col_notes = st.columns([2, 1])

with col_bs:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">📋 BALANCE SHEET MONDIALE COMPLÈTE (MMT)</div>
    """, unsafe_allow_html=True)

    _bs_rows = ""
    for i, y in enumerate(years):
        bal     = d["production"][i] - d["consumption"][i]
        bal_col = "#3FB950" if bal > 0 else "#F85149"
        su_v    = su[i]
        sc, sl, _ = su_signal(su_v)
        is_last = (i == len(years) - 1)
        row_bg  = "background:#0F1A1F;" if is_last else ""

        _bs_rows += (
            f'<tr style="border-bottom:1px solid #1C2333;{row_bg}">'
            f'<td style="padding:6px 10px;color:{"#58A6FF" if is_last else "#E6EDF3"};'
            f'font-weight:{"700" if is_last else "400"}">'
            f'{"→ " if is_last else ""}{y}</td>'
            f'<td style="padding:6px 10px;color:#E6EDF3;text-align:right;'
            f'font-family:IBM Plex Mono,monospace">{d["production"][i]:.1f}</td>'
            f'<td style="padding:6px 10px;color:#E6EDF3;text-align:right;'
            f'font-family:IBM Plex Mono,monospace">{d["consumption"][i]:.1f}</td>'
            f'<td style="padding:6px 10px;color:{bal_col};text-align:right;'
            f'font-family:IBM Plex Mono,monospace;font-weight:600">{bal:+.1f}</td>'
            f'<td style="padding:6px 10px;color:#E6EDF3;text-align:right;'
            f'font-family:IBM Plex Mono,monospace">{d["exports"][i]:.1f}</td>'
            f'<td style="padding:6px 10px;color:#F0B429;text-align:right;'
            f'font-family:IBM Plex Mono,monospace">{d["ending_stocks"][i]:.1f}</td>'
            f'<td style="padding:6px 10px;color:{sc};text-align:right;font-weight:700">'
            f'{su_v:.1f}%</td>'
            f'<td style="padding:6px 10px;color:{sc};font-size:0.8em">{sl}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:0.82em">'
        f'<thead><tr style="border-bottom:2px solid #30363D">'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:600;text-align:left">Année</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:600;text-align:right">Prod.</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:600;text-align:right">Conso.</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:600;text-align:right">Balance</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:600;text-align:right">Exports</th>'
        f'<th style="padding:6px 10px;color:#F0B429;font-weight:600;text-align:right">Stocks</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:600;text-align:right">S/U</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:600;text-align:left">Signal</th>'
        f'</tr></thead>'
        f'<tbody>{_bs_rows}</tbody>'
        f'</table>',
        unsafe_allow_html=True
    )

with col_notes:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">📝 NOTES WASDE & ANALYSE</div>
    """, unsafe_allow_html=True)

    # Note WASDE
    st.markdown(
        f'<div style="background:#0D1117;border:1px solid #1C2333;'
        f'border-left:3px solid {color};border-radius:8px;'
        f'padding:14px;margin-bottom:14px">'
        f'<div style="font-size:0.72em;color:#8B949E;margin-bottom:8px">💡 NOTE ANALYSTE</div>'
        f'<div style="font-size:0.82em;color:#C9D1D9;line-height:1.6">'
        f'{d["wasde_notes"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Tendance S/U
    su_trend  = su[-1] - su[-3]
    trend_col = "#F85149" if su_trend < 0 else "#3FB950"
    trend_str = "🔻 En baisse" if su_trend < 0 else "🔺 En hausse"

    st.markdown(
        f'<div style="background:#0D1117;border:1px solid #1C2333;'
        f'border-radius:8px;padding:14px;margin-bottom:14px">'
        f'<div style="font-size:0.72em;color:#8B949E;margin-bottom:8px">📉 TENDANCE S/U 3 ANS</div>'
        f'<div style="font-size:1.3em;font-weight:700;color:{trend_col}">'
        f'{trend_str} {abs(su_trend):.1f}pp</div>'
        f'<div style="font-size:0.78em;color:#8B949E;margin-top:4px">'
        f'{su[-3]:.1f}% ({years[-3]}) → {su[-1]:.1f}% ({years[-1]})</div>'
        f'<div style="background:#1C2333;border-radius:3px;height:4px;margin-top:8px">'
        f'<div style="background:{trend_col};width:{min(abs(su_trend)/10*100,100):.0f}%;'
        f'height:4px;border-radius:3px"></div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Impact prix
    st.markdown(
        f'<div style="background:#0D1117;border:1px solid #1C2333;'
        f'border-radius:8px;padding:14px">'
        f'<div style="font-size:0.72em;color:#8B949E;margin-bottom:10px">'
        f'🎯 RÈGLE D\'OR S/U → PRIX</div>'
        f'<div style="font-size:0.78em;color:#C9D1D9;line-height:2.0">'
        f'<span style="color:#F85149">S/U &lt; 12%</span> → Très bullish (crise)<br>'
        f'<span style="color:#F0B429">S/U 12-18%</span> → Bullish (tendu)<br>'
        f'<span style="color:#8B949E">S/U 18-25%</span> → Neutre (équilibré)<br>'
        f'<span style="color:#3FB950">S/U 25-35%</span> → Bearish (abondant)<br>'
        f'<span style="color:#58A6FF">S/U &gt; 35%</span> → Très bearish (surplus)<br>'
        f'</div>'
        f'<div style="margin-top:10px;font-size:0.75em;color:#8B949E;'
        f'border-top:1px solid #1C2333;padding-top:8px">'
        f'💡 Le S/U ratio est l\'indicateur fondamental #1 en trading agri. '
        f'Corrélation inverse forte avec les prix : S/U ↓ → prix ↑'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROW 4 : Comparaison 3 commodités S/U
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">🔍 COMPARAISON S/U RATIO — BLÉ · MAÏS · SOJA</div>
""", unsafe_allow_html=True)

fig_cmp = go.Figure()
for c_key, c_data in WASDE_DATA.items():
    su_c = compute_su_ratio(c_data)
    fig_cmp.add_trace(go.Scatter(
        x=c_data["years"], y=su_c,
        name=c_data["label"],
        mode="lines+markers",
        line=dict(color=c_data["color"], width=2.5),
        marker=dict(size=8),
        text=[f"{v:.1f}%" for v in su_c],
        textposition="top center",
        textfont=dict(size=9),
    ))

# Zones
fig_cmp.add_hrect(y0=0,  y1=12, fillcolor="rgba(248,81,73,0.06)",  line_width=0)
fig_cmp.add_hrect(y0=12, y1=18, fillcolor="rgba(240,180,41,0.05)", line_width=0)
fig_cmp.add_hrect(y0=25, y1=60, fillcolor="rgba(63,185,80,0.04)",  line_width=0)

for level, lc, lt in [(12, "#F85149", "Seuil critique 12%"),
                       (18, "#F0B429", "Seuil tendu 18%"),
                       (25, "#3FB950", "Seuil abondant 25%")]:
    fig_cmp.add_hline(y=level, line_dash="dash", line_color=lc, opacity=0.4,
                      annotation_text=lt, annotation_position="right",
                      annotation_font=dict(color=lc, size=9))

fig_cmp.update_layout(
    paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
    font=dict(color="#8B949E", size=10),
    height=320,
    margin=dict(l=5, r=120, t=10, b=5),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11),
                orientation="h", y=1.05),
    yaxis=dict(gridcolor="#1C2333", title="S/U Ratio (%)"),
    xaxis=dict(gridcolor="#1C2333"),
)
st.plotly_chart(fig_cmp, use_container_width=True,
                config={"displayModeBar": False})

# Footer WASDE
st.markdown(f"""
<div style="background:#0D1117;border:1px solid #1C2333;border-radius:8px;
            padding:12px 16px;font-size:0.75em;color:#8B949E;
            display:flex;justify-content:space-between;align-items:center">
    <div>
        📡 Source : USDA WASDE (World Agricultural Supply and Demand Estimates) ·
        Données en millions de tonnes métriques (MMT) ·
        Publié mensuellement par l'USDA
    </div>
    <div style="color:#3FB950">
        ● Dernière mise à jour WASDE : Mars 2025
    </div>
</div>
""", unsafe_allow_html=True)