"""
News & Alerts Dashboard — Module 9
"""

import streamlit as st
import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.graph_objects as go

st.set_page_config(page_title="News & Alerts", page_icon="📰", layout="wide")
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


@st.cache_data(ttl=300)
def load_news_summary():
    try:
        from config import DATA_PROCESSED
        p = DATA_PROCESSED / "news_summary_latest.json"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


@st.cache_data(ttl=300)
def load_news_csv():
    try:
        from config import DATA_PROCESSED
        import glob
        files = sorted(glob.glob(str(DATA_PROCESSED / "signals_*.csv")), reverse=True)
        if files:
            return pd.read_csv(files[0])
    except Exception:
        pass
    return pd.DataFrame()


summary = load_news_summary()
news_df = load_news_csv()


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 0 18px 0;border-bottom:1px solid #1C2333;margin-bottom:20px">
    <div>
        <span style="font-size:1.5em;font-weight:800;color:#E6EDF3">📰 News & Alerts</span>
        <div style="font-size:0.78em;color:#8B949E;margin-top:3px">
            RSS Live · LLM Analysis · Early Warning · Macro Score
        </div>
    </div>
    <div style="font-size:0.75em;color:#8B949E">
        {summary.get("generated_at", "—") if summary else "—"}
    </div>
</div>
""", unsafe_allow_html=True)

# Bouton lancer le pipeline
col_r1, col_r2 = st.columns([4, 1])
with col_r2:
    if st.button("🔄 Actualiser les news", use_container_width=True):
        with st.spinner("Collecte RSS + analyse LLM en cours... (~2 min)"):
            try:
                from module_9_news.news_pipeline import run_news_pipeline
                run_news_pipeline()
                st.cache_data.clear()
                st.success("✅ News mises à jour !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

if not summary:
    st.info("Lance le pipeline pour collecter les news : `python module_9_news/news_pipeline.py`")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 : KPIs + Macro Score
# ══════════════════════════════════════════════════════════════════════════════
macro  = summary.get("macro_score", {})
alerts = summary.get("top_alerts", [])
sbc    = summary.get("sentiment_by_commodity", {})

n_critical = sum(1 for a in alerts if a.get("severity") == "critical")
n_watch    = sum(1 for a in alerts if a.get("severity") == "watch")
n_total    = summary.get("total_articles", 0)
macro_val  = macro.get("final_macro_score", 0)
macro_col  = "#3FB950" if macro_val > 0 else ("#F85149" if macro_val < 0 else "#8B949E")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📰 Articles analysés", n_total)
k2.metric("🚨 Alertes critiques", n_critical)
k3.metric("⚠️ Alertes watch",     n_watch)
k4.metric("🧭 Score macro",       f"{macro_val:+d}/5")
k5.metric("🌾 Blé",
          f"{sbc.get('wheat',{}).get('n_articles',0)} arts",
          f"Sentiment {sbc.get('wheat',{}).get('avg_sentiment',0):+.1f}")

# Barre macro score
st.markdown(
    f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:8px;'
    f'padding:12px 16px;margin:12px 0">'
    f'<div style="display:flex;justify-content:space-between;font-size:0.78em;margin-bottom:6px">'
    f'<span style="color:#8B949E">Score Macro-Grains global</span>'
    f'<span style="color:{macro_col};font-weight:700">{macro_val:+d} / 5</span>'
    f'</div>'
    f'<div style="display:flex;gap:12px;font-size:0.75em;flex-wrap:wrap">'
    f'<span style="color:#8B949E">🌤️ Météo: <b style="color:{pc(macro.get("weather",0))}">'
    f'{macro.get("weather",0):+d}</b></span>'
    f'<span style="color:#8B949E">💱 FX: <b style="color:{pc(macro.get("fx",0))}">'
    f'{macro.get("fx",0):+d}</b></span>'
    f'<span style="color:#8B949E">⛽ Énergie: <b style="color:{pc(macro.get("energy",0))}">'
    f'{macro.get("energy",0):+d}</b></span>'
    f'<span style="color:#8B949E">🚢 Shipping: <b style="color:{pc(macro.get("shipping",0))}">'
    f'{macro.get("shipping",0):+d}</b></span>'
    f'</div></div>',
    unsafe_allow_html=True
)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 : Alertes du jour
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">🚨 ALERTES DU JOUR — EARLY WARNING SYSTEM</div>
""", unsafe_allow_html=True)

if not alerts:
    st.info("Aucune alerte significative aujourd'hui.")
else:
    for alert in alerts[:6]:
        sev   = alert.get("severity", "info")
        score = alert.get("score", 0)
        title = alert.get("title", "")
        url   = alert.get("url", "")
        tags  = alert.get("tags", "")
        comm  = alert.get("commodity", "other")
        analysis = alert.get("analysis", "")

        sev_cfg = {
            "critical": ("#F85149", "🚨 CRITICAL"),
            "watch":    ("#F0B429", "⚠️  WATCH"),
            "info":     ("#58A6FF", "ℹ️  INFO"),
        }.get(sev, ("#8B949E", "—"))
        sev_col, sev_label = sev_cfg

        comm_icon = {"wheat":"🌾","corn":"🌽","soy":"🫘"}.get(comm,"📰")

        st.markdown(
            f'<div style="background:#0D1117;border:1px solid #1C2333;'
            f'border-left:4px solid {sev_col};border-radius:8px;'
            f'padding:14px;margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
            f'margin-bottom:8px">'
            f'<div style="flex:1">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
            f'<span style="background:{hex_to_rgba(sev_col,0.15)};color:{sev_col};'
            f'font-size:0.7em;font-weight:700;padding:2px 8px;border-radius:10px">'
            f'{sev_label}</span>'
            f'<span style="color:#8B949E;font-size:0.75em">{comm_icon} {comm.upper()}</span>'
            f'<span style="color:#8B949E;font-size:0.75em">Score: {score}</span>'
            f'</div>'
            f'<div style="font-size:0.88em;font-weight:600;color:#E6EDF3">'
            f'<a href="{url}" target="_blank" style="color:#E6EDF3;text-decoration:none">'
            f'{title}</a></div>'
            f'</div></div>'
            + (f'<div style="font-size:0.78em;color:#C9D1D9;margin-bottom:6px">'
               f'{analysis[:200]}{"..." if len(analysis)>200 else ""}</div>'
               if analysis else "")
            + (f'<div style="font-size:0.7em;color:#8B949E">'
               f'🏷️ {tags}</div>'
               if tags else "")
            + f'</div>',
            unsafe_allow_html=True
        )

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 : Sentiment par commodité
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">📊 SENTIMENT DES NEWS PAR COMMODITÉ</div>
""", unsafe_allow_html=True)

comm_cfg = {
    "wheat":   ("🌾", "Blé",  "#F9A825"),
    "corn":    ("🌽", "Maïs", "#58A6FF"),
    "soy":     ("🫘", "Soja", "#3FB950"),
}

sent_cols = st.columns(3)
for col, (c_key, (icon, label, color)) in zip(sent_cols, comm_cfg.items()):
    c_data = sbc.get(c_key, {})
    if not c_data:
        with col:
            st.markdown(
                f'<div style="background:#0D1117;border:1px solid #1C2333;'
                f'border-radius:8px;padding:14px;opacity:0.5">'
                f'<div style="color:#8B949E">{icon} {label} — Aucune donnée</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        continue

    avg  = float(c_data.get("avg_sentiment", 0))
    n    = int(c_data.get("n_articles", 0))
    bull = int(c_data.get("bullish", 0))
    bear = int(c_data.get("bearish", 0))
    neut = int(c_data.get("neutral", 0))
    sent_col = "#3FB950" if avg > 0.1 else ("#F85149" if avg < -0.1 else "#8B949E")
    sent_str = "BULLISH 🟢" if avg > 0.1 else ("BEARISH 🔴" if avg < -0.1 else "NEUTRE ⚪")
    bar_pct  = int((avg + 1) / 2 * 100)

    with col:
        st.markdown(
            f'<div style="background:#0D1117;border:1px solid #1C2333;'
            f'border-left:3px solid {color};border-radius:8px;padding:14px">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
            f'<div style="font-size:1em;font-weight:700;color:#E6EDF3">{icon} {label}</div>'
            f'<div style="font-size:0.75em;color:#8B949E">{n} articles</div>'
            f'</div>'
            f'<div style="font-size:1.4em;font-weight:800;color:{sent_col};margin-bottom:6px">'
            f'{avg:+.2f}</div>'
            f'<div style="font-size:0.75em;color:{sent_col};margin-bottom:8px">{sent_str}</div>'
            f'<div style="background:#1C2333;border-radius:3px;height:4px;margin-bottom:8px">'
            f'<div style="background:{sent_col};width:{bar_pct}%;height:4px;'
            f'border-radius:3px"></div></div>'
            f'<div style="display:flex;gap:12px;font-size:0.72em">'
            f'<span style="color:#3FB950">▲ {bull} bullish</span>'
            f'<span style="color:#F85149">▼ {bear} bearish</span>'
            f'<span style="color:#8B949E">— {neut} neutres</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 : Articles par commodité
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">📋 ARTICLES PAR COMMODITÉ</div>
""", unsafe_allow_html=True)

tab_wheat, tab_corn, tab_soy, tab_all = st.tabs(
    ["🌾 Blé", "🌽 Maïs", "🫘 Soja", "📰 Tous"]
)

def render_articles(articles: list[dict]):
    if not articles:
        st.info("Aucun article.")
        return

    for a in articles:
        sent     = a.get("sentiment", "neutral")
        s_col    = "#3FB950" if sent=="bullish" else ("#F85149" if sent=="bearish" else "#8B949E")
        s_icon   = "▲" if sent=="bullish" else ("▼" if sent=="bearish" else "—")
        title    = a.get("title", "Sans titre")
        url      = a.get("url", "")
        analysis = a.get("analysis", "")
        impact   = a.get("impact", "")
        outlook  = a.get("outlook", "")
        source   = a.get("source", a.get("source_name", ""))
        pub      = a.get("published", "")[:10] if a.get("published") else ""

        st.markdown(
            f'<div style="background:#0D1117;border:1px solid #1C2333;'
            f'border-radius:8px;padding:12px;margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:flex-start;margin-bottom:6px">'
            f'<a href="{url}" target="_blank" style="color:#E6EDF3;font-weight:600;'
            f'font-size:0.88em;text-decoration:none;flex:1">{title}</a>'
            f'<span style="color:{s_col};font-weight:700;font-size:0.9em;'
            f'margin-left:12px;white-space:nowrap">{s_icon} {sent.upper()}</span>'
            f'</div>'
            + (f'<div style="font-size:0.78em;color:#C9D1D9;margin-bottom:6px">'
               f'{analysis[:250]}{"..." if len(analysis)>250 else ""}</div>'
               if analysis else "")
            + (f'<div style="font-size:0.75em;color:#F0B429;margin-bottom:4px">'
               f'💰 {impact}</div>' if impact else "")
            + (f'<div style="font-size:0.75em;color:#58A6FF;margin-bottom:4px">'
               f'🔭 {outlook}</div>' if outlook else "")
            + f'<div style="font-size:0.68em;color:#8B949E">{source} · {pub}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

with tab_wheat:
    render_articles(sbc.get("wheat", {}).get("top_articles", []))
with tab_corn:
    render_articles(sbc.get("corn",  {}).get("top_articles", []))
with tab_soy:
    render_articles(sbc.get("soy",   {}).get("top_articles", []))
with tab_all:
    if not news_df.empty:
        # Colonnes disponibles seulement
        available_cols = news_df.columns.tolist()

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if "sentiment" in available_cols:
                filter_sent = st.multiselect(
                    "Sentiment",
                    ["bullish", "bearish", "neutral"],
                    default=["bullish", "bearish", "neutral"]
                )
            else:
                filter_sent = None
        with col_f2:
            if "commodity" in available_cols:
                filter_comm = st.multiselect(
                    "Commodité",
                    ["wheat", "corn", "soy", "other"],
                    default=["wheat", "corn", "soy", "other"]
                )
            else:
                filter_comm = None

        filtered = news_df.copy()
        if filter_sent and "sentiment" in available_cols:
            filtered = filtered[filtered["sentiment"].isin(filter_sent)]
        if filter_comm and "commodity" in available_cols:
            filtered = filtered[filtered["commodity"].isin(filter_comm)]

        # Affiche seulement les colonnes qui existent
        display_cols = [c for c in
            ["title", "commodity", "sentiment", "event_type",
             "alert_severity", "source_name", "published"]
            if c in filtered.columns
        ]
        rename_map = {
            "title": "Titre", "commodity": "Comm.",
            "sentiment": "Sentiment", "event_type": "Type",
            "alert_severity": "Alerte", "source_name": "Source",
            "published": "Date"
        }
        st.dataframe(
            filtered[display_cols].rename(columns=rename_map),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Pas de données disponibles.")