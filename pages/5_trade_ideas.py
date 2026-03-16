import streamlit as st
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import DATA_PROCESSED

st.set_page_config(page_title="Trade Ideas", page_icon="🤖", layout="wide")
st.markdown("<style>[data-testid='stAppViewContainer']{background:#0E1117}[data-testid='stSidebar']{background:#1E2130}</style>", unsafe_allow_html=True)
st.title("🤖 Trade Ideas — LLM Intelligence")

# Bouton de régénération
col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Régénérer les idées", type="primary"):
        with st.spinner("Appel API Groq/Llama..."):
            try:
                from module_5_llm.generators.trade_idea_generator import generate_trade_ideas
                ideas = generate_trade_ideas(save=True)
                st.success("✅ Nouvelles idées générées !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

path = DATA_PROCESSED / "trade_ideas_latest.json"
if not path.exists():
    st.info("Lance `llm_pipeline.py` pour générer les trade ideas.")
    st.stop()

with open(path) as f:
    data = json.load(f)

# Market Summary
st.markdown(f"""
<div style="background:#1E2130;border-radius:12px;padding:20px;margin-bottom:20px;
            border-left:4px solid #448AFF">
    <h4 style="margin:0 0 8px 0">📊 Market Summary</h4>
    <p style="color:#BDBDBD;margin:0">{data.get('market_summary','')}</p>
    <p style="color:#9E9E9E;font-size:0.8em;margin:8px 0 0 0">
        Généré le : {data.get('generated_at','')}
    </p>
</div>
""", unsafe_allow_html=True)

# Daily Bias
bias = data.get("daily_bias", {})
bias_cols = st.columns(3)
bias_config = {"bullish": "#00C853", "bearish": "#FF1744", "neutral": "#FFD600"}
for i, (c, b) in enumerate(bias.items()):
    with bias_cols[i]:
        color = bias_config.get(b, "white")
        icon  = "▲" if b == "bullish" else ("▼" if b == "bearish" else "—")
        st.markdown(f"""
        <div style="background:#1E2130;border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:0.85em;color:#9E9E9E">{c.upper()}</div>
            <div style="font-size:1.3em;font-weight:700;color:{color}">{icon} {b.upper()}</div>
        </div>
        """, unsafe_allow_html=True)

# Trade Ideas
st.markdown("---")
for idea in data.get("trade_ideas", []):
    direction = idea.get("direction", "")
    color = "#00C853" if "long" in direction else "#FF1744"
    conviction = idea.get("conviction", "medium")
    conv_color = {"high": "#00C853", "medium": "#FFD600", "low": "#9E9E9E"}.get(conviction)
    execution  = idea.get("execution", {})
    rationale  = idea.get("rationale", {})
    monitoring = idea.get("monitoring", {})

    with st.expander(
        f"#{idea['id']} — {idea['title']} | {direction.upper()} | "
        f"Conviction: {conviction.upper()}",
        expanded=(idea["id"] == 1)
    ):
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown("**📌 Rationale**")
            st.markdown(f"🎯 {rationale.get('primary_catalyst','')}")
            st.markdown(f"📊 {rationale.get('secondary_catalyst','')}")
            st.markdown(f"📉 {rationale.get('technical_setup','')}")
            st.markdown(f"🌾 {rationale.get('fundamental_driver','')}")
            if rationale.get("freight_angle"):
                st.markdown(f"🚢 {rationale.get('freight_angle')}")

        with r2:
            st.markdown("**⚡ Execution**")
            st.markdown(f"""
            | Paramètre | Valeur |
            |-----------|--------|
            | Entry     | {execution.get('entry_level','')} |
            | Trigger   | {execution.get('entry_trigger','')} |
            | Stop      | {execution.get('stop_loss','')} |
            | Target 1  | {execution.get('target_1','')} |
            | Target 2  | {execution.get('target_2','')} |
            | R/R       | **{execution.get('risk_reward','')}** |
            | Size      | {execution.get('position_size','')} |
            """)

        with r3:
            st.markdown("**⚠️ Risks & Monitoring**")
            for risk in idea.get("risk_factors", []):
                st.markdown(f"• {risk}")
            st.markdown("---")
            st.markdown(f"📅 {monitoring.get('key_dates','')}")
            st.markdown(f"📍 {monitoring.get('key_levels','')}")
            st.markdown(f"❌ Invalide si: {monitoring.get('invalidation','')}")

# Key Risk
if data.get("key_risk_today"):
    st.warning(f"⚠️ **Key Risk Today** : {data['key_risk_today']}")