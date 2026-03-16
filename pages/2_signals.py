import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Signals Dashboard", page_icon="⚡", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');
    * { font-family: 'IBM Plex Sans', sans-serif !important; }
    [data-testid="stAppViewContainer"] { background: #070B14; }
    [data-testid="stSidebar"] { background: #0D1117; border-right: 1px solid #1C2333; }
    h1,h2,h3,h4 { color: #E6EDF3 !important; }
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


def hex_to_rgba(h, a):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"

def pc(v): return "#3FB950" if v > 0 else ("#F85149" if v < 0 else "#8B949E")


# ── Chargement données ────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all():
    try:
        from config import DATA_RAW, DATA_PROCESSED
    except Exception as e:
        return {}

    data = {}

    # Signaux summary
    p = DATA_PROCESSED / "signals_summary.csv"
    data["signals"] = pd.read_csv(p) if p.exists() else pd.DataFrame()

    # COT enrichi
    p = DATA_PROCESSED / "cot_signals.csv"
    if p.exists():
        data["cot"] = pd.read_csv(p, parse_dates=["date"])
    else:
        try:
            from module_3_signals.indicators.sentiment_indicators import _synthetic_cot_signals
            data["cot"] = _synthetic_cot_signals()
        except:
            data["cot"] = pd.DataFrame()

    # BDI signals
    p = DATA_PROCESSED / "bdi_signals.csv"
    if p.exists():
        data["bdi"] = pd.read_csv(p, parse_dates=["date"])
    else:
        try:
            p_raw = DATA_RAW / "baltic_bdi.csv"
            if p_raw.exists():
                df_bdi = pd.read_csv(p_raw, parse_dates=["date"]).sort_values("date")
                df_bdi["bdi_ma50"]   = df_bdi["close"].rolling(50).mean()
                df_bdi["bdi_roc1m"]  = df_bdi["close"].pct_change(20) * 100
                df_bdi["bdi_roc3m"]  = df_bdi["close"].pct_change(60) * 100
                df_bdi["bdi_pctile"] = df_bdi["close"].rank(pct=True) * 100
                df_bdi["bdi_regime"] = "normal"
                df_bdi["bdi_signal"] = 0
                data["bdi"] = df_bdi
            else:
                data["bdi"] = pd.DataFrame()
        except:
            data["bdi"] = pd.DataFrame()

    # Météo
    p = DATA_PROCESSED / "weather_signals.csv"
    if p.exists():
        data["weather"] = pd.read_csv(p, parse_dates=["date"])
    else:
        try:
            dfs = []
            for zone in ["us_midwest_corn_belt", "us_plains_wheat", "brazil_mato_grosso",
                         "argentina_pampas", "ukraine_black_earth", "australia_wheatbelt"]:
                p_raw = DATA_RAW / f"weather_{zone}.csv"
                if p_raw.exists():
                    df_w = pd.read_csv(p_raw, parse_dates=["date"])
                    df_w["zone"] = zone
                    if "precip_anomaly_30d" not in df_w.columns:
                        df_w["month"] = df_w["date"].dt.month
                        monthly_avg = df_w.groupby("month")["precipitation_sum"].mean()
                        df_w["precip_avg"] = df_w["month"].map(monthly_avg)
                        df_w["precip_anomaly_pct"] = (
                            (df_w["precipitation_sum"] - df_w["precip_avg"])
                            / (df_w["precip_avg"] + 0.1)
                        ) * 100
                        df_w["precip_anomaly_30d"] = df_w["precip_anomaly_pct"].rolling(30).mean()
                        df_w["weather_signal"] = 0
                        df_w.loc[df_w["precip_anomaly_30d"] < -30, "weather_signal"] =  1
                        df_w.loc[df_w["precip_anomaly_30d"] >  30, "weather_signal"] = -1
                    dfs.append(df_w)
            data["weather"] = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        except:
            data["weather"] = pd.DataFrame()

    # NDVI
    p = DATA_RAW / "ndvi_vegetation.csv"
    data["ndvi"] = pd.read_csv(p, parse_dates=["date"]) if p.exists() else pd.DataFrame()

    # Technical
    data["technical"] = {}
    for c in ["wheat", "corn", "soybean"]:
        p = DATA_PROCESSED / f"{c}_technical.csv"
        if p.exists():
            data["technical"][c] = pd.read_csv(p, index_col="date", parse_dates=True)

    return data


# ── APPEL load_all() + assignation des variables ──────────────────────────────
data       = load_all()
signals_df = data.get("signals", pd.DataFrame())
cot_df     = data.get("cot",     pd.DataFrame())
bdi_df     = data.get("bdi",     pd.DataFrame())
weather_df = data.get("weather", pd.DataFrame())
ndvi_df    = data.get("ndvi",    pd.DataFrame())
tech       = data.get("technical", {})


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 0 18px 0;border-bottom:1px solid #1C2333;margin-bottom:20px">
    <div>
        <span style="font-size:1.5em;font-weight:800;color:#E6EDF3">⚡ Market Signals</span>
        <div style="font-size:0.78em;color:#8B949E;margin-top:3px">
            Momentum · COT · Météo · BDI · NDVI Satellite
        </div>
    </div>
    <div style="font-size:0.75em;color:#8B949E">{datetime.now().strftime('%d %b %Y %H:%M')}</div>
</div>
""", unsafe_allow_html=True)

col_r1, col_r2 = st.columns([4, 1])
with col_r2:
    if st.button("🔄 Recalculer", use_container_width=True):
        with st.spinner("Calcul en cours..."):
            try:
                from module_3_signals.signals.signal_engine import run_signal_engine
                run_signal_engine(save=True)
                st.cache_data.clear()
                st.success("✅ Signaux mis à jour !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 : Scores composites
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">⚡ SCORES COMPOSITES — CONVICTION PAR COMMODITÉ</div>
""", unsafe_allow_html=True)

comm_cfg = {
    "wheat":   ("🌾", "BLÉ CBOT",  "#F9A825"),
    "corn":    ("🌽", "MAÏS CBOT", "#58A6FF"),
    "soybean": ("🫘", "SOJA CBOT", "#3FB950"),
}

if not signals_df.empty:
    score_cols = st.columns(3)
    for col, (_, row) in zip(score_cols, signals_df.iterrows()):
        c       = row.get("commodity", "")
        icon, label, accent = comm_cfg.get(c, ("", "", "#58A6FF"))
        score   = float(row.get("composite", 0))
        conv    = int(row.get("conviction", 0))
        direc   = str(row.get("direction", "NEUTRAL"))
        bar_col = "#3FB950" if score > 0.1 else ("#F85149" if score < -0.1 else "#F0B429")
        bar_pct = int((score + 1) / 2 * 100)

        cot_pctile = float(row.get("cot_pctile", 50))
        cot_col    = "#F85149" if cot_pctile > 75 else ("#3FB950" if cot_pctile < 25 else "#8B949E")
        ndvi_raw   = row.get("ndvi_value", None)
        ndvi_str   = f"NDVI: {float(ndvi_raw):.2f}" if ndvi_raw and str(ndvi_raw) != "nan" else "NDVI: —"

        sig_keys   = ["momentum", "rsi", "bb", "cot", "weather", "bdi", "ndvi"]
        sig_labels = ["MOM", "RSI", "BB", "COT", "WTH", "BDI", "NDVI"]

        _grid = ""
        for k, lbl in zip(sig_keys, sig_labels):
            v     = int(row.get(k, 0))
            sym   = "▲" if v > 0 else ("▼" if v < 0 else "—")
            col_s = "#3FB950" if v > 0 else ("#F85149" if v < 0 else "#8B949E")
            hx    = col_s.lstrip("#")
            rv, gv, bv = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
            _grid += (
                f'<div style="text-align:center;padding:4px 2px;'
                f'background:rgba({rv},{gv},{bv},0.1);'
                f'border-radius:5px;border:1px solid rgba({rv},{gv},{bv},0.25)">'
                f'<div style="font-size:0.6em;color:#8B949E">{lbl}</div>'
                f'<div style="color:{col_s};font-weight:700;font-size:0.85em">{sym}</div>'
                f'</div>'
            )

        with col:
            st.markdown(
                f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:10px;'
                f'padding:18px;border-left:3px solid {accent}">'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:flex-start;margin-bottom:12px">'
                f'<div>'
                f'<div style="font-size:1.1em;font-weight:700;color:#E6EDF3">{icon} {label}</div>'
                f'<div style="font-size:0.72em;color:#8B949E;margin-top:2px">'
                f'COT: <span style="color:{cot_col}">{cot_pctile:.0f}%ile</span>'
                f' &nbsp;·&nbsp; {ndvi_str}</div>'
                f'</div>'
                f'<div style="text-align:right">'
                f'<div style="font-size:1.6em;font-weight:800;color:{bar_col}">{score:+.3f}</div>'
                f'<div style="font-size:0.75em;color:{bar_col};font-weight:600">'
                f'{direc.split()[0]}</div>'
                f'</div></div>'
                f'<div style="background:#1C2333;border-radius:4px;height:6px;margin-bottom:4px">'
                f'<div style="background:{bar_col};width:{bar_pct}%;height:6px;'
                f'border-radius:4px"></div></div>'
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:0.65em;color:#8B949E;margin-bottom:12px">'
                f'<span>-1.0 Bearish</span>'
                f'<span style="color:{bar_col}">Conviction {conv}%</span>'
                f'<span>+1.0 Bullish</span></div>'
                f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px">'
                f'{_grid}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )
else:
    st.warning("Lance `signals_pipeline.py` pour générer les signaux.")
    st.stop()

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 : COT Analysis
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px;border-top:1px solid #1C2333;padding-top:20px">
    📋 COT REPORT — POSITIONING SPÉCULATIF
</div>
""", unsafe_allow_html=True)

col_cot1, col_cot2 = st.columns([2, 1])

with col_cot1:
    if not cot_df.empty:
        commodity_sel = st.selectbox(
            "Commodité COT",
            ["wheat", "corn", "soybean"],
            format_func=lambda x: {"wheat": "🌾 Blé", "corn": "🌽 Maïs", "soybean": "🫘 Soja"}[x],
            key="cot_sel"
        )
        sub_cot = cot_df[cot_df["commodity"] == commodity_sel].sort_values("date").tail(104)

        if not sub_cot.empty:
            fig_cot = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                vertical_spacing=0.06, row_heights=[0.65, 0.35],
                subplot_titles=["Net Speculative Length", "Percentile 3 ans"]
            )
            fig_cot.add_trace(go.Scatter(
                x=sub_cot["date"], y=sub_cot["net_spec"],
                name="Net Spec", line=dict(color="#58A6FF", width=2),
                fill="tozeroy", fillcolor="rgba(88,166,255,0.1)",
            ), row=1, col=1)
            fig_cot.add_trace(go.Scatter(
                x=sub_cot["date"], y=sub_cot["net_comm"],
                name="Net Comm", line=dict(color="#F9A825", width=1.5, dash="dot"),
            ), row=1, col=1)
            fig_cot.add_hline(y=0, line_color="white", opacity=0.2, row=1, col=1)
            fig_cot.add_hrect(y0=80, y1=100, fillcolor="rgba(248,81,73,0.1)",
                              line_width=0, row=2, col=1)
            fig_cot.add_hrect(y0=0, y1=20, fillcolor="rgba(63,185,80,0.1)",
                              line_width=0, row=2, col=1)
            fig_cot.add_trace(go.Scatter(
                x=sub_cot["date"], y=sub_cot["nsl_pctile"],
                name="Percentile", line=dict(color="#E040FB", width=2),
            ), row=2, col=1)
            fig_cot.add_hline(y=80, line_dash="dash", line_color="#F85149",
                              opacity=0.5, row=2, col=1)
            fig_cot.add_hline(y=20, line_dash="dash", line_color="#3FB950",
                              opacity=0.5, row=2, col=1)
            fig_cot.update_layout(
                paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
                font=dict(color="#8B949E", size=10),
                height=380, margin=dict(l=5, r=5, t=30, b=5),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
            )
            for r in [1, 2]:
                fig_cot.update_xaxes(gridcolor="#1C2333", row=r, col=1)
                fig_cot.update_yaxes(gridcolor="#1C2333", row=r, col=1)
            st.plotly_chart(fig_cot, use_container_width=True,
                            config={"displayModeBar": False})
    else:
        st.info("Données COT non disponibles — lance `run_pipeline.py`.")

with col_cot2:
    st.markdown("""
    <div style="font-size:0.72em;color:#8B949E;font-weight:600;margin-bottom:12px">
        📖 LECTURE COT
    </div>
    """, unsafe_allow_html=True)

    if not signals_df.empty:
        _cot_gauges = ""
        for _, row in signals_df.iterrows():
            c = row.get("commodity", "")
            icon, label, _ = comm_cfg.get(c, ("", "", "#58A6FF"))
            pctile  = float(row.get("cot_pctile", 50))
            col_p   = "#F85149" if pctile > 75 else ("#3FB950" if pctile < 25 else "#F0B429")
            status  = ("EXTRÊME LONG 🔴" if pctile > 80 else
                       "EXTRÊME SHORT 🟢" if pctile < 20 else "NEUTRE ⚪")
            _cot_gauges += (
                f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:8px;'
                f'padding:12px;margin-bottom:8px">'
                f'<div style="font-size:0.8em;font-weight:700;color:#E6EDF3;margin-bottom:6px">'
                f'{icon} {label}</div>'
                f'<div style="background:#1C2333;border-radius:4px;height:8px;margin-bottom:6px">'
                f'<div style="background:{col_p};width:{pctile:.0f}%;height:8px;'
                f'border-radius:4px"></div></div>'
                f'<div style="display:flex;justify-content:space-between;font-size:0.72em">'
                f'<span style="color:#3FB950">0%</span>'
                f'<span style="color:{col_p};font-weight:600">{pctile:.0f}%ile</span>'
                f'<span style="color:#F85149">100%</span></div>'
                f'<div style="font-size:0.72em;color:{col_p};margin-top:4px;font-weight:600">'
                f'{status}</div>'
                f'</div>'
            )
        st.markdown(_cot_gauges, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#0D1117;border:1px solid #1C2333;border-radius:8px;
                padding:12px;font-size:0.75em;color:#8B949E;line-height:1.7">
        <b style="color:#E6EDF3">Comment lire le COT :</b><br>
        📊 <b>Net Spec</b> = Longs - Shorts spéculatifs<br>
        📊 <b>Net Comm</b> = Position des hedgers physiques<br><br>
        🔴 <b>Percentile >80%</b> = Spécs extrêmement longs<br>
        → Signal bearish contrarian<br><br>
        🟢 <b>Percentile &lt;20%</b> = Spécs extrêmement courts<br>
        → Signal bullish contrarian<br><br>
        💡 La divergence spécs/commercials<br>est le signal le plus fort
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 : NDVI Satellite
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px;border-top:1px solid #1C2333;padding-top:20px">
    🛰️ NDVI — SANTÉ DE LA VÉGÉTATION AGRICOLE (PROXY SATELLITE)
</div>
""", unsafe_allow_html=True)

zone_labels = {
    "us_corn_belt":        ("🇺🇸", "Iowa — Corn Belt",      ["corn", "soybean"]),
    "us_wheat_plains":     ("🇺🇸", "Kansas — Winter Wheat", ["wheat"]),
    "brazil_cerrado":      ("🇧🇷", "Mato Grosso — Soja",    ["soybean"]),
    "ukraine_steppe":      ("🇺🇦", "Ukraine — Tchernozem",  ["wheat", "corn"]),
    "argentina_pampas":    ("🇦🇷", "Pampas — Soja/Blé",    ["soybean", "wheat"]),
    "australia_wheatbelt": ("🇦🇺", "W. Australia — Blé",   ["wheat"]),
}

if not ndvi_df.empty:
    latest_ndvi     = ndvi_df.sort_values("date").groupby("zone").last().reset_index()
    ndvi_zones_list = latest_ndvi["zone"].tolist()
    n_cols          = min(3, len(ndvi_zones_list))
    ndvi_cols       = st.columns(n_cols)

    for idx, (_, zrow) in enumerate(latest_ndvi.iterrows()):
        zone      = zrow["zone"]
        flag, desc, crops = zone_labels.get(zone, ("🌍", zone, []))
        ndvi_val  = float(zrow.get("ndvi_proxy", 0.5))
        signal    = int(zrow.get("price_signal", 0))
        stress    = zrow.get("stress_category", "normal")
        critical  = bool(zrow.get("is_critical_window", False))

        ndvi_color = (
            "#F85149" if ndvi_val < 0.25 else
            "#F0B429" if ndvi_val < 0.40 else
            "#3FB950" if ndvi_val > 0.65 else
            "#8B949E"
        )
        stress_label = {
            "severe_stress":   "🚨 STRESS SÉVÈRE",
            "moderate_stress": "⚠️  Stress modéré",
            "normal":          "✅ Normal",
            "excellent":       "🌿 Excellent",
        }.get(stress, "—")

        sig_col   = "#3FB950" if signal > 0 else ("#F85149" if signal < 0 else "#8B949E")
        sig_str   = "↑ Bullish" if signal > 0 else ("↓ Bearish" if signal < 0 else "→ Neutre")
        crit_tag  = " ⚡" if critical else ""
        crops_str = " · ".join(c.upper() for c in crops)
        bar_pct   = int(ndvi_val * 100)

        with ndvi_cols[idx % n_cols]:
            st.markdown(
                f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:8px;'
                f'padding:12px;margin-bottom:8px;border-left:3px solid {ndvi_color}">'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:flex-start;margin-bottom:8px">'
                f'<div>'
                f'<div style="font-size:0.8em;font-weight:700;color:#E6EDF3">'
                f'{flag} {desc}<span style="color:#F0B429">{crit_tag}</span></div>'
                f'<div style="font-size:0.65em;color:#8B949E;margin-top:1px">{crops_str}</div>'
                f'</div>'
                f'<div style="text-align:right">'
                f'<div style="font-size:1.15em;font-weight:700;color:{ndvi_color}">{ndvi_val:.2f}</div>'
                f'<div style="font-size:0.65em;color:{sig_col};font-weight:600">{sig_str}</div>'
                f'</div></div>'
                f'<div style="background:#1C2333;border-radius:3px;height:4px;margin-bottom:6px">'
                f'<div style="background:{ndvi_color};width:{bar_pct}%;height:4px;'
                f'border-radius:3px"></div></div>'
                f'<div style="font-size:0.68em;color:{ndvi_color}">{stress_label}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
    zone_sel_ndvi = st.selectbox(
        "Zone NDVI — historique",
        options=ndvi_zones_list,
        format_func=lambda z: f"{zone_labels.get(z, ('', '', []))[0]} {zone_labels.get(z, ('', z, []))[1]}"
    )
    zone_hist = ndvi_df[ndvi_df["zone"] == zone_sel_ndvi].sort_values("date")
    if not zone_hist.empty:
        fig_ndvi = go.Figure()
        fig_ndvi.add_trace(go.Scatter(
            x=zone_hist["date"], y=zone_hist["ndvi_proxy"],
            name="NDVI proxy", line=dict(color="#3FB950", width=2),
            fill="tozeroy", fillcolor="rgba(63,185,80,0.08)",
        ))
        for y, col, txt in [(0.35, "#F0B429", "Stress modéré"),
                             (0.20, "#F85149", "Stress sévère"),
                             (0.65, "#3FB950", "Excellent")]:
            fig_ndvi.add_hline(y=y, line_dash="dash", line_color=col,
                               opacity=0.6, annotation_text=txt)
        fig_ndvi.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10),
            height=220, margin=dict(l=5, r=10, t=10, b=5),
            yaxis=dict(range=[0, 1], gridcolor="#1C2333"),
            xaxis=dict(gridcolor="#1C2333"),
            showlegend=False,
        )
        st.plotly_chart(fig_ndvi, use_container_width=True,
                        config={"displayModeBar": False})
else:
    st.info("Lance `python module_1_data_pipeline/collectors/ndvi_collector.py` pour les données NDVI.")

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 : BDI + Météo
# ══════════════════════════════════════════════════════════════════════════════
col_bdi, col_wthr = st.columns(2)

with col_bdi:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px;border-top:1px solid #1C2333;padding-top:18px">
        🚢 BALTIC DRY INDEX — SIGNAL FRET
    </div>
    """, unsafe_allow_html=True)

    if not bdi_df.empty:
        bdi_recent = bdi_df.sort_values("date").tail(180)
        fig_bdi    = go.Figure()
        fig_bdi.add_trace(go.Scatter(
            x=bdi_recent["date"], y=bdi_recent["close"],
            name="BDI", line=dict(color="#58A6FF", width=2),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.08)",
        ))
        if "bdi_ma50" in bdi_recent.columns:
            fig_bdi.add_trace(go.Scatter(
                x=bdi_recent["date"], y=bdi_recent["bdi_ma50"],
                name="MA50", line=dict(color="#F0B429", width=1.5, dash="dot"),
            ))
        last_bdi = float(bdi_df["close"].dropna().iloc[-1])
        fig_bdi.add_annotation(
            x=bdi_recent["date"].iloc[-1], y=last_bdi,
            text=f"  {last_bdi:,.0f}",
            showarrow=False, font=dict(color="#58A6FF", size=11), xanchor="left"
        )
        fig_bdi.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10),
            height=250, margin=dict(l=5, r=40, t=10, b=5),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
            xaxis=dict(gridcolor="#1C2333"),
            yaxis=dict(gridcolor="#1C2333"),
        )
        st.plotly_chart(fig_bdi, use_container_width=True,
                        config={"displayModeBar": False})

        if "bdi_regime" in bdi_df.columns:
            regime = str(bdi_df["bdi_regime"].dropna().iloc[-1])
            roc1m  = float(bdi_df["bdi_roc1m"].dropna().iloc[-1])
            rc     = {"very_low": "#F85149", "low": "#F0B429",
                      "normal": "#8B949E", "high": "#3FB950",
                      "very_high": "#3FB950"}.get(regime, "#8B949E")
            st.markdown(
                f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;'
                f'padding:8px 12px;font-size:0.78em;display:flex;'
                f'justify-content:space-between;align-items:center">'
                f'<span style="color:#8B949E">Régime fret :</span>'
                f'<span style="color:{rc};font-weight:600">{regime.replace("_"," ").upper()}</span>'
                f'<span style="color:{pc(roc1m)};font-weight:600">{roc1m:+.1f}% 1M</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("Données BDI non disponibles — lance `freight_pipeline.py`.")

with col_wthr:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px;border-top:1px solid #1C2333;padding-top:18px">
        🌤️ MÉTÉO — ANOMALIES PRÉCIPITATIONS
    </div>
    """, unsafe_allow_html=True)

    if not weather_df.empty:
        zone_sel_w = st.selectbox(
            "Zone météo",
            options=weather_df["zone"].unique(),
            format_func=lambda z: z.replace("_", " ").title(),
            key="wthr_zone"
        )
        wzone = weather_df[weather_df["zone"] == zone_sel_w].sort_values("date").tail(180)

        fig_wthr = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                 vertical_spacing=0.06, row_heights=[0.6, 0.4])
        fig_wthr.add_trace(go.Bar(
            x=wzone["date"], y=wzone["precipitation_sum"],
            name="Précip. (mm)", marker_color="#58A6FF", opacity=0.7,
        ), row=1, col=1)
        if "precip_avg" in wzone.columns:
            fig_wthr.add_trace(go.Scatter(
                x=wzone["date"], y=wzone["precip_avg"],
                name="Moyenne hist.", line=dict(color="#F0B429", width=1.5, dash="dot"),
            ), row=1, col=1)
        if "precip_anomaly_30d" in wzone.columns:
            anom_vals = wzone["precip_anomaly_30d"].fillna(0)
            colors_anom = ["#F85149" if v < 0 else "#3FB950" for v in anom_vals]
            fig_wthr.add_trace(go.Bar(
                x=wzone["date"], y=anom_vals,
                name="Anomalie 30j (%)", marker_color=colors_anom, opacity=0.8,
            ), row=2, col=1)
            fig_wthr.add_hline(y=0, line_color="white", opacity=0.3, row=2, col=1)
        fig_wthr.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10),
            height=280, margin=dict(l=5, r=5, t=10, b=5),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
            barmode="overlay",
        )
        for r in [1, 2]:
            fig_wthr.update_xaxes(gridcolor="#1C2333", row=r, col=1)
            fig_wthr.update_yaxes(gridcolor="#1C2333", row=r, col=1)
        st.plotly_chart(fig_wthr, use_container_width=True,
                        config={"displayModeBar": False})

        if "weather_signal" in wzone.columns:
            last_sig  = int(wzone["weather_signal"].iloc[-1])
            last_anom = float(wzone["precip_anomaly_30d"].iloc[-1]) \
                        if "precip_anomaly_30d" in wzone.columns else 0
            if last_sig != 0:
                alert_c = "#F85149" if last_sig > 0 else "#3FB950"
                alert_t = (f"🌵 SÉCHERESSE — Anomalie {last_anom:+.1f}% → Signal BULLISH prix"
                           if last_sig > 0 else
                           f"🌧️ EXCÈS EAU — Anomalie {last_anom:+.1f}% → Signal BEARISH prix")
                st.markdown(
                    f'<div style="background:{hex_to_rgba(alert_c,0.1)};'
                    f'border:1px solid {alert_c};border-radius:6px;padding:8px 12px;'
                    f'font-size:0.78em;color:{alert_c};font-weight:600;margin-top:8px">'
                    f'{alert_t}</div>',
                    unsafe_allow_html=True
                )
    else:
        st.info("Données météo non disponibles — lance `run_pipeline.py`.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 : Saisonnalité
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px;border-top:1px solid #1C2333;padding-top:20px">
    🗓️ SAISONNALITÉ HISTORIQUE — PERFORMANCE PAR MOIS
</div>
""", unsafe_allow_html=True)

commodity_seas = st.selectbox(
    "Commodité — saisonnalité",
    ["wheat", "corn", "soybean"],
    format_func=lambda x: {"wheat": "🌾 Blé", "corn": "🌽 Maïs", "soybean": "🫘 Soja"}[x],
    key="seas_sel"
)

try:
    from config import DATA_RAW as DR_seas
    path_seas = DR_seas / f"{commodity_seas}_futures.csv"
    if path_seas.exists():
        df_seas = pd.read_csv(path_seas, index_col="date", parse_dates=True)
        df_seas["month"]  = df_seas.index.month
        df_seas["ret_1m"] = df_seas["close"].pct_change(21) * 100

        monthly = df_seas.groupby("month")["ret_1m"].agg(["mean", "std", "count"]).reset_index()
        monthly.columns = ["month", "avg_return", "std_return", "count"]
        monthly["month"] = monthly["month"].astype(int)
        month_names = ["Jan","Fév","Mar","Avr","Mai","Jun",
                       "Jul","Aoû","Sep","Oct","Nov","Déc"]
        monthly["month_name"] = monthly["month"].apply(lambda x: month_names[int(x) - 1])
        current_month = int(datetime.now().month)

        # rgba() obligatoire — Plotly rejette hex+alpha comme "#3FB95099"
        bar_colors = []
        for i in range(len(monthly)):
            m       = int(monthly["month"].iloc[i])
            is_pos  = float(monthly["avg_return"].iloc[i]) > 0
            r, g, b = (63, 185, 80) if is_pos else (248, 81, 73)
            alpha   = 1.0 if m == current_month else 0.45
            bar_colors.append(f"rgba({r},{g},{b},{alpha})")

        fig_seas = go.Figure()
        fig_seas.add_trace(go.Bar(
            x=monthly["month_name"],
            y=monthly["avg_return"],
            marker_color=bar_colors,
            text=[f"{v:+.1f}%" for v in monthly["avg_return"]],
            textposition="outside",
            textfont=dict(size=10),
            name="Rendement moyen 1M",
        ))
        fig_seas.add_vline(
            x=month_names[current_month - 1],
            line_dash="dash", line_color="#58A6FF",
            annotation_text="Aujourd'hui",
            annotation_font=dict(color="#58A6FF", size=10),
        )
        fig_seas.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10),
            height=280, margin=dict(l=5, r=5, t=30, b=5),
            yaxis=dict(gridcolor="#1C2333", zeroline=True, zerolinecolor="#30363D"),
            xaxis=dict(gridcolor="#1C2333"),
            showlegend=False,
            title=dict(
                text=f"Rendement moyen par mois — {commodity_seas.upper()} (2015-2025)",
                font=dict(size=12, color="#8B949E")
            )
        )
        st.plotly_chart(fig_seas, use_container_width=True,
                        config={"displayModeBar": False})

        best_m  = monthly.loc[monthly["avg_return"].idxmax()]
        worst_m = monthly.loc[monthly["avg_return"].idxmin()]
        curr_m  = monthly[monthly["month"] == current_month].iloc[0]

        st.markdown(
            f'<div style="display:flex;gap:10px;flex-wrap:wrap">'

            f'<div style="flex:1;background:#0D1117;border:1px solid #1C2333;'
            f'border-radius:6px;padding:10px;min-width:140px">'
            f'<div style="font-size:0.65em;color:#8B949E">🟢 MEILLEUR MOIS</div>'
            f'<div style="font-size:1em;font-weight:700;color:#3FB950">'
            f'{best_m["month_name"]}</div>'
            f'<div style="font-size:0.75em;color:#3FB950">'
            f'{best_m["avg_return"]:+.1f}% en moyenne</div>'
            f'</div>'

            f'<div style="flex:1;background:#0D1117;border:1px solid #1C2333;'
            f'border-radius:6px;padding:10px;min-width:140px">'
            f'<div style="font-size:0.65em;color:#8B949E">🔴 PIRE MOIS</div>'
            f'<div style="font-size:1em;font-weight:700;color:#F85149">'
            f'{worst_m["month_name"]}</div>'
            f'<div style="font-size:0.75em;color:#F85149">'
            f'{worst_m["avg_return"]:+.1f}% en moyenne</div>'
            f'</div>'

            f'<div style="flex:1;background:#0D1117;border:1px solid #58A6FF33;'
            f'border-left:3px solid #58A6FF;border-radius:6px;padding:10px;min-width:140px">'
            f'<div style="font-size:0.65em;color:#58A6FF">📅 CE MOIS-CI</div>'
            f'<div style="font-size:1em;font-weight:700;color:#E6EDF3">'
            f'{curr_m["month_name"]}</div>'
            f'<div style="font-size:0.75em;color:{pc(curr_m["avg_return"])}">'
            f'{curr_m["avg_return"]:+.1f}% historique</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

except Exception as e:
    st.warning(f"Saisonnalité non disponible : {e}")