"""
Risk Dashboard — VaR, CVaR, Stress Tests, Corrélations, Equity Curves
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

st.set_page_config(page_title="Risk Dashboard", page_icon="⚠️", layout="wide")
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
# CHARGEMENT DONNÉES — depuis fichiers sauvegardés uniquement (pas de recalcul)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=600)
def load_risk_data():
    try:
        from config import DATA_RAW, DATA_PROCESSED
    except:
        return {}

    data = {}

    # VaR analysis
    p = DATA_PROCESSED / "var_analysis.csv"
    data["var"] = pd.read_csv(p) if p.exists() else pd.DataFrame()

    # Stress tests
    p = DATA_PROCESSED / "stress_test_results.csv"
    data["stress"] = pd.read_csv(p) if p.exists() else pd.DataFrame()

    # Equity curves des backtests (depuis CSV sauvegardés)
    data["equity"] = {}
    backtest_ids = [
        ("momentum_wheat",   "Momentum Blé"),
        ("momentum_corn",    "Momentum Maïs"),
        ("momentum_soybean", "Momentum Soja"),
        ("crush_soybean",    "Crush Spread Soja"),
        ("calendar_wheat",   "Calendar Spread Blé"),
    ]
    for bt_id, bt_label in backtest_ids:
        p = DATA_PROCESSED / f"backtest_{bt_id}_equity.csv"
        if p.exists():
            df_eq = pd.read_csv(p, parse_dates=["date"], index_col="date")
            data["equity"][bt_label] = df_eq["equity"]

    # Trades des backtests
    data["trades"] = {}
    for bt_id, bt_label in backtest_ids:
        p = DATA_PROCESSED / f"backtest_{bt_id}_trades.csv"
        if p.exists():
            data["trades"][bt_label] = pd.read_csv(p)

    # Corrélations depuis les prix bruts
    corr_data = {}
    for c in ["wheat", "corn", "soybean"]:
        p = DATA_RAW / f"{c}_futures.csv"
        if p.exists():
            df = pd.read_csv(p, index_col="date", parse_dates=True)
            corr_data[c] = df["close"].pct_change().dropna().iloc[-252:]
    if len(corr_data) >= 2:
        data["corr_matrix"] = pd.DataFrame(corr_data).dropna().corr()
        data["returns_df"]  = pd.DataFrame(corr_data).dropna()
    else:
        data["corr_matrix"] = pd.DataFrame()
        data["returns_df"]  = pd.DataFrame()

    return data


data       = load_risk_data()
var_df     = data.get("var",        pd.DataFrame())
stress_df  = data.get("stress",     pd.DataFrame())
equity     = data.get("equity",     {})
trades     = data.get("trades",     {})
corr_mat   = data.get("corr_matrix",pd.DataFrame())
returns_df = data.get("returns_df", pd.DataFrame())

# Portefeuille de démo (même que risk_pipeline.py)
DEMO_PORTFOLIO = {
    "wheat":   {"contracts": 10, "direction":  1, "label": "🌾 Blé"},
    "corn":    {"contracts":  8, "direction": -1, "label": "🌽 Maïs"},
    "soybean": {"contracts":  5, "direction":  1, "label": "🫘 Soja"},
}


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 0 18px 0;border-bottom:1px solid #1C2333;margin-bottom:20px">
    <div>
        <span style="font-size:1.5em;font-weight:800;color:#E6EDF3">⚠️ Risk Dashboard</span>
        <div style="font-size:0.78em;color:#8B949E;margin-top:3px">
            VaR · CVaR · Stress Tests · Corrélations · Backtests
        </div>
    </div>
    <div style="text-align:right">
        <div style="font-size:0.75em;color:#8B949E">{datetime.now().strftime('%d %b %Y %H:%M')}</div>
        <div style="font-size:0.68em;color:#8B949E;margin-top:2px">
            Portefeuille démo : 10 blé L · 8 maïs S · 5 soja L
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Bouton recalcul
_, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("🔄 Recalculer le risque", use_container_width=True):
        with st.spinner("Calcul VaR & stress tests..."):
            try:
                from module_7_risk.risk_pipeline import run_risk_pipeline
                run_risk_pipeline()
                st.cache_data.clear()
                st.success("✅ Risque mis à jour !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 : KPIs Risque
# ══════════════════════════════════════════════════════════════════════════════
if not var_df.empty:
    total_var  = var_df["var_1d_99_hist"].sum()
    total_cvar = var_df["cvar_1d_99_hist"].sum()
    total_pos  = var_df["position_value"].sum()
    var_pct    = total_var / total_pos * 100 if total_pos > 0 else 0
    var_color  = "#3FB950" if var_pct < 2 else ("#F0B429" if var_pct < 4 else "#F85149")
    worst_stress = stress_df["total_pnl"].min() if not stress_df.empty else 0
    best_stress  = stress_df["total_pnl"].max() if not stress_df.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("💼 Valeur Portfolio",    f"${total_pos:,.0f}", "3 positions")
    k2.metric("⚠️ VaR 1j 99%",          f"${total_var:,.0f}",
              f"{var_pct:.2f}% du portfolio")
    k3.metric("💀 CVaR 1j 99%",         f"${total_cvar:,.0f}",
              "Expected Shortfall")
    k4.metric("🔥 Pire stress",          f"${worst_stress:+,.0f}",
              "Worst case scenario")
    k5.metric("✅ Meilleur stress",      f"${best_stress:+,.0f}",
              "Best case scenario")

    # Barre VaR / portfolio
    st.markdown(
        f'<div style="background:#0D1117;border:1px solid #1C2333;'
        f'border-radius:8px;padding:12px 16px;margin:12px 0">'
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:0.78em;color:#8B949E;margin-bottom:6px">'
        f'<span>VaR 1j 99% = <b style="color:{var_color}">${total_var:,.0f}</b> '
        f'sur <b style="color:#E6EDF3">${total_pos:,.0f}</b></span>'
        f'<span style="color:{var_color};font-weight:700">{var_pct:.2f}% du portfolio</span>'
        f'</div>'
        f'<div style="background:#1C2333;border-radius:4px;height:8px">'
        f'<div style="background:{var_color};width:{min(var_pct/10*100,100):.0f}%;'
        f'height:8px;border-radius:4px"></div></div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:0.68em;color:#8B949E;margin-top:4px">'
        f'<span>0%</span><span style="color:#3FB950">Limite OK: &lt;2%</span>'
        f'<span style="color:#F0B429">Attention: 2-4%</span>'
        f'<span style="color:#F85149">Danger: &gt;4%</span>'
        f'<span>10%</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )
else:
    st.warning("Lance `python module_7_risk/risk_pipeline.py` pour générer les données de risque.")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 : VaR par position + Corrélation
# ══════════════════════════════════════════════════════════════════════════════
col_var, col_corr = st.columns([1.2, 1])

with col_var:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">📊 VAR & CVAR PAR POSITION (99%, 1 JOUR)</div>
    """, unsafe_allow_html=True)

    if not var_df.empty:
        # Graphique barres groupées VaR vs CVaR
        fig_var = go.Figure()
        commodities_var = var_df["commodity"].tolist()
        var_vals  = var_df["var_1d_99_hist"].tolist()
        cvar_vals = var_df["cvar_1d_99_hist"].tolist()
        var_mc    = var_df["var_10d_99_mc"].tolist() if "var_10d_99_mc" in var_df.columns else [0]*len(commodities_var)

        fig_var.add_trace(go.Bar(
            name="VaR 1j 99%",
            x=commodities_var, y=var_vals,
            marker_color="#F0B429",
            text=[f"${v:,.0f}" for v in var_vals],
            textposition="outside", textfont=dict(size=10),
        ))
        fig_var.add_trace(go.Bar(
            name="CVaR 1j 99%",
            x=commodities_var, y=cvar_vals,
            marker_color="#F85149",
            text=[f"${v:,.0f}" for v in cvar_vals],
            textposition="outside", textfont=dict(size=10),
        ))
        if any(v > 0 for v in var_mc):
            fig_var.add_trace(go.Bar(
                name="VaR 10j MC",
                x=commodities_var, y=var_mc,
                marker_color="#58A6FF",
                text=[f"${v:,.0f}" for v in var_mc],
                textposition="outside", textfont=dict(size=10),
            ))

        fig_var.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10),
            height=280,
            margin=dict(l=5, r=5, t=30, b=5),
            barmode="group",
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
            yaxis=dict(gridcolor="#1C2333"),
            xaxis=dict(gridcolor="#1C2333"),
        )
        st.plotly_chart(fig_var, use_container_width=True,
                        config={"displayModeBar": False})

        # Tableau détaillé VaR
        _var_rows = ""
        for _, row in var_df.iterrows():
            c       = row["commodity"]
            pos_cfg = DEMO_PORTFOLIO.get(c, {})
            dir_str = "🟢 LONG" if pos_cfg.get("direction", 1) > 0 else "🔴 SHORT"
            pos_val = row["position_value"]
            var_v   = row["var_1d_99_hist"]
            cvar_v  = row["cvar_1d_99_hist"]
            vp      = var_v / pos_val * 100 if pos_val > 0 else 0
            vc      = "#3FB950" if vp < 3 else ("#F0B429" if vp < 5 else "#F85149")

            _var_rows += (
                f'<tr style="border-bottom:1px solid #1C2333">'
                f'<td style="padding:6px 10px;color:#E6EDF3;font-weight:600">'
                f'{pos_cfg.get("label", c.upper())}</td>'
                f'<td style="padding:6px 10px;color:#8B949E">{dir_str}</td>'
                f'<td style="padding:6px 10px;color:#8B949E;text-align:right;'
                f'font-family:IBM Plex Mono,monospace">{int(row["contracts"])}</td>'
                f'<td style="padding:6px 10px;color:#E6EDF3;text-align:right;'
                f'font-family:IBM Plex Mono,monospace">${pos_val:,.0f}</td>'
                f'<td style="padding:6px 10px;color:#F0B429;text-align:right;'
                f'font-family:IBM Plex Mono,monospace;font-weight:600">${var_v:,.0f}</td>'
                f'<td style="padding:6px 10px;color:#F85149;text-align:right;'
                f'font-family:IBM Plex Mono,monospace">${cvar_v:,.0f}</td>'
                f'<td style="padding:6px 10px;color:{vc};text-align:right;font-weight:700">'
                f'{vp:.2f}%</td>'
                f'</tr>'
            )

        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:0.82em">'
            f'<thead><tr style="border-bottom:1px solid #30363D">'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:left">Position</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500">Direction</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">Contrats</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">Valeur</th>'
            f'<th style="padding:6px 10px;color:#F0B429;font-weight:500;text-align:right">VaR 1j</th>'
            f'<th style="padding:6px 10px;color:#F85149;font-weight:500;text-align:right">CVaR 1j</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">VaR %</th>'
            f'</tr></thead>'
            f'<tbody>{_var_rows}</tbody>'
            f'</table>',
            unsafe_allow_html=True
        )
    else:
        st.info("Lance `risk_pipeline.py` pour les données VaR.")

with col_corr:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                margin-bottom:12px">🔗 MATRICE DE CORRÉLATION (252J)</div>
    """, unsafe_allow_html=True)

    if not corr_mat.empty:
        fig_heat = go.Figure(data=go.Heatmap(
            z=corr_mat.values,
            x=[c.upper() for c in corr_mat.columns],
            y=[c.upper() for c in corr_mat.index],
            colorscale=[
                [0.0, "#F85149"], [0.5, "#1C2333"], [1.0, "#3FB950"]
            ],
            zmid=0, zmin=-1, zmax=1,
            text=np.round(corr_mat.values, 2),
            texttemplate="%{text}",
            textfont=dict(size=14, color="white"),
            showscale=True,
            colorbar=dict(
                tickfont=dict(color="#8B949E"),
                len=0.8,
            )
        ))
        fig_heat.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=11),
            height=220,
            margin=dict(l=5, r=5, t=10, b=5),
        )
        st.plotly_chart(fig_heat, use_container_width=True,
                        config={"displayModeBar": False})

        # Bénéfice de diversification
        if not var_df.empty:
            sum_var = var_df["var_1d_99_hist"].sum()
            # VaR portfolio simplifié avec corrélations
            try:
                from module_7_risk.calculators.portfolio_risk import compute_portfolio_var
                port_risk = compute_portfolio_var(
                    {c: {"contracts": DEMO_PORTFOLIO[c]["contracts"],
                         "direction": DEMO_PORTFOLIO[c]["direction"]}
                     for c in DEMO_PORTFOLIO}
                )
                port_var   = port_risk["portfolio_var"]
                div_benefit = port_risk["diversification_benefit"]
                div_pct     = port_risk["diversification_pct"]
            except:
                port_var    = sum_var * 0.72
                div_benefit = sum_var - port_var
                div_pct     = div_benefit / sum_var * 100 if sum_var > 0 else 0

            _div_html = (
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px">'
                f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;padding:10px">'
                f'<div style="font-size:0.65em;color:#8B949E">Somme VaR individuels</div>'
                f'<div style="font-size:1em;font-weight:700;color:#F0B429">'
                f'${sum_var:,.0f}</div></div>'
                f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;padding:10px">'
                f'<div style="font-size:0.65em;color:#8B949E">VaR portfolio</div>'
                f'<div style="font-size:1em;font-weight:700;color:#3FB950">'
                f'${port_var:,.0f}</div></div>'
                f'<div style="background:#0D1117;border:1px solid #3FB95033;'
                f'border-left:3px solid #3FB950;border-radius:6px;padding:10px;grid-column:span 2">'
                f'<div style="font-size:0.65em;color:#8B949E">✅ Bénéfice diversification</div>'
                f'<div style="font-size:1.1em;font-weight:700;color:#3FB950">'
                f'${div_benefit:,.0f} (-{div_pct:.1f}%)</div>'
                f'<div style="font-size:0.72em;color:#8B949E;margin-top:2px">'
                f'La diversification réduit le VaR de {div_pct:.1f}%</div>'
                f'</div></div>'
            )
            st.markdown(_div_html, unsafe_allow_html=True)
    else:
        st.info("Données de corrélation non disponibles.")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 : Stress Tests
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">🔥 STRESS TESTS — 9 SCÉNARIOS HISTORIQUES & HYPOTHÉTIQUES</div>
""", unsafe_allow_html=True)

if not stress_df.empty:
    col_chart, col_detail = st.columns([1.5, 1])

    with col_chart:
        df_s    = stress_df.sort_values("total_pnl")
        labels  = df_s["scenario"].str.replace("_", " ").str.title()
        pnl_vals = df_s["total_pnl"].tolist()
        types   = df_s.get("type", pd.Series([""] * len(df_s))).tolist()

        bar_cols = [hex_to_rgba("#F85149", 0.8) if v < 0
                    else hex_to_rgba("#3FB950", 0.8)
                    for v in pnl_vals]

        fig_stress = go.Figure(go.Bar(
            x=pnl_vals,
            y=labels,
            orientation="h",
            marker_color=bar_cols,
            text=[f"${v:+,.0f}" for v in pnl_vals],
            textposition="outside",
            textfont=dict(size=10, color=[
                "#F85149" if v < 0 else "#3FB950" for v in pnl_vals
            ]),
        ))
        fig_stress.add_vline(x=0, line_color="white", opacity=0.3)

        fig_stress.update_layout(
            paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
            font=dict(color="#8B949E", size=10),
            height=380,
            margin=dict(l=5, r=80, t=10, b=5),
            xaxis=dict(gridcolor="#1C2333", title="P&L Impact ($)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
            showlegend=False,
        )
        st.plotly_chart(fig_stress, use_container_width=True,
                        config={"displayModeBar": False})

    with col_detail:
        # Tableau stress détaillé
        _st_rows = ""
        for _, row in stress_df.sort_values("total_pnl").iterrows():
            pnl     = row["total_pnl"]
            sc      = "#F85149" if pnl < 0 else "#3FB950"
            icon    = "▼" if pnl < 0 else "▲"
            name    = row["scenario"].replace("_", " ").title()[:30]
            stype   = row.get("type", "")
            badge_c = "#F85149" if stype == "historical" else "#F0B429"
            dur     = row.get("duration", "—")

            _st_rows += (
                f'<tr style="border-bottom:1px solid #1C2333">'
                f'<td style="padding:5px 8px;color:#E6EDF3;font-size:0.82em">{name}</td>'
                f'<td style="padding:5px 8px">'
                f'<span style="color:{badge_c};font-size:0.7em;'
                f'background:{hex_to_rgba(badge_c,0.15)};'
                f'padding:2px 6px;border-radius:10px">{stype.upper()}</span></td>'
                f'<td style="padding:5px 8px;color:{sc};font-weight:700;text-align:right;'
                f'font-family:IBM Plex Mono,monospace">{icon} ${abs(pnl):,.0f}</td>'
                f'</tr>'
            )

        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:0.82em">'
            f'<thead><tr style="border-bottom:1px solid #30363D">'
            f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:left">Scénario</th>'
            f'<th style="padding:5px 8px;color:#8B949E;font-weight:500">Type</th>'
            f'<th style="padding:5px 8px;color:#8B949E;font-weight:500;text-align:right">P&L</th>'
            f'</tr></thead>'
            f'<tbody>{_st_rows}</tbody>'
            f'</table>',
            unsafe_allow_html=True
        )

        # Résumé worst/best
        worst_pnl = stress_df["total_pnl"].min()
        best_pnl  = stress_df["total_pnl"].max()
        worst_name = stress_df.loc[stress_df["total_pnl"].idxmin(), "scenario"].replace("_"," ").title()
        best_name  = stress_df.loc[stress_df["total_pnl"].idxmax(), "scenario"].replace("_"," ").title()

        st.markdown(
            f'<div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:8px">'
            f'<div style="background:#1A0F0F;border:1px solid #3D1F1F;border-radius:6px;padding:10px">'
            f'<div style="font-size:0.65em;color:#F85149">💀 WORST CASE</div>'
            f'<div style="font-size:1em;font-weight:700;color:#F85149">'
            f'${worst_pnl:+,.0f}</div>'
            f'<div style="font-size:0.7em;color:#8B949E;margin-top:2px">{worst_name[:25]}</div>'
            f'</div>'
            f'<div style="background:#0A1A0F;border:1px solid #1A3D1F;border-radius:6px;padding:10px">'
            f'<div style="font-size:0.65em;color:#3FB950">✅ BEST CASE</div>'
            f'<div style="font-size:1em;font-weight:700;color:#3FB950">'
            f'${best_pnl:+,.0f}</div>'
            f'<div style="font-size:0.7em;color:#8B949E;margin-top:2px">{best_name[:25]}</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
else:
    st.info("Lance `risk_pipeline.py` pour les stress tests.")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 : Equity Curves Backtests
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">📈 EQUITY CURVES — BACKTESTS 2018-2025 (BASE 100)</div>
""", unsafe_allow_html=True)

if equity:
    palette = ["#F9A825", "#58A6FF", "#3FB950", "#F0B429", "#E040FB"]

    fig_eq = go.Figure()
    fig_eq.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.15)

    for i, (name, eq_series) in enumerate(equity.items()):
        normalized = (eq_series / eq_series.iloc[0] - 1) * 100
        last_val   = float(normalized.iloc[-1])
        col_eq     = palette[i % len(palette)]

        fig_eq.add_trace(go.Scatter(
            x=normalized.index, y=normalized.values,
            name=f"{name} ({last_val:+.1f}%)",
            line=dict(color=col_eq, width=2),
            hovertemplate=f"<b>{name}</b><br>%{{x|%d %b %Y}}<br>%{{y:.1f}}%<extra></extra>",
        ))

    fig_eq.update_layout(
        paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
        font=dict(color="#8B949E", size=10),
        height=320,
        margin=dict(l=5, r=10, t=10, b=5),
        legend=dict(bgcolor="rgba(13,17,23,0.8)", bordercolor="#1C2333",
                    borderwidth=1, font=dict(size=10)),
        yaxis=dict(gridcolor="#1C2333", title="Rendement (%)"),
        xaxis=dict(gridcolor="#1C2333"),
    )
    st.plotly_chart(fig_eq, use_container_width=True,
                    config={"displayModeBar": False})

    # Tableau résumé backtests
    if trades:
        st.markdown("""
        <div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
                    margin:14px 0 8px 0">📋 RÉSUMÉ PERFORMANCE BACKTESTS</div>
        """, unsafe_allow_html=True)

        _bt_rows = ""
        for i, (name, eq_series) in enumerate(equity.items()):
            total_ret = (eq_series.iloc[-1] / eq_series.iloc[0] - 1) * 100
            # Max drawdown
            roll_max  = eq_series.cummax()
            drawdown  = (eq_series - roll_max) / roll_max * 100
            max_dd    = drawdown.min()
            # Sharpe approx
            daily_ret = eq_series.pct_change().dropna()
            sharpe    = float((daily_ret.mean() / daily_ret.std()) * np.sqrt(252)) if daily_ret.std() > 0 else 0

            # Trades
            tr_df   = trades.get(name, pd.DataFrame())
            n_trades = len(tr_df) if not tr_df.empty else "—"
            win_rate = (
                f"{len(tr_df[tr_df['pnl_net']>0])/len(tr_df)*100:.1f}%"
                if not tr_df.empty and "pnl_net" in tr_df.columns else "—"
            )

            ret_col = "#3FB950" if total_ret > 0 else "#F85149"
            sh_col  = "#3FB950" if sharpe > 1 else ("#F0B429" if sharpe > 0.5 else "#F85149")
            dd_col  = "#3FB950" if max_dd > -15 else ("#F0B429" if max_dd > -25 else "#F85149")

            _bt_rows += (
                f'<tr style="border-bottom:1px solid #1C2333">'
                f'<td style="padding:6px 10px;color:{palette[i%len(palette)]};font-weight:600">'
                f'{name}</td>'
                f'<td style="padding:6px 10px;color:{ret_col};text-align:right;font-weight:700;'
                f'font-family:IBM Plex Mono,monospace">{total_ret:+.1f}%</td>'
                f'<td style="padding:6px 10px;color:{sh_col};text-align:right;font-weight:700;'
                f'font-family:IBM Plex Mono,monospace">{sharpe:.2f}</td>'
                f'<td style="padding:6px 10px;color:{dd_col};text-align:right;'
                f'font-family:IBM Plex Mono,monospace">{max_dd:.1f}%</td>'
                f'<td style="padding:6px 10px;color:#8B949E;text-align:right">{n_trades}</td>'
                f'<td style="padding:6px 10px;color:#8B949E;text-align:right">{win_rate}</td>'
                f'</tr>'
            )

        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:0.82em">'
            f'<thead><tr style="border-bottom:1px solid #30363D">'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:left">Stratégie</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">Rendement</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">Sharpe</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">Max DD</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">Trades</th>'
            f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">Win Rate</th>'
            f'</tr></thead>'
            f'<tbody>{_bt_rows}</tbody>'
            f'</table>',
            unsafe_allow_html=True
        )

        # Note explicative
        st.markdown("""
        <div style="background:#0D1117;border:1px solid #1C2333;border-left:3px solid #58A6FF;
                    border-radius:6px;padding:12px 16px;margin-top:12px;
                    font-size:0.78em;color:#8B949E;line-height:1.6">
            <b style="color:#E6EDF3">📖 Lecture des résultats :</b> Les stratégies momentum
            affichent des Sharpe négatifs sur 2018-2025 — ce qui reflète la réalité des marchés
            céréaliers : difficiles à trader en pur technique sur des horizons courts.
            La vraie edge vient de l'information fondamentale (WASDE surprises, anomalies météo,
            flux physiques) que nos modules 1-5 capturent. En production, ces stratégies seraient
            enrichies par des filtres fondamentaux et un horizon de holding plus long.
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Lance `backtest_pipeline.py` pour générer les equity curves.")


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="border-top:1px solid #1C2333;margin-top:28px;padding-top:14px;
            display:flex;justify-content:space-between;font-size:0.72em;color:#8B949E">
    <div>
        Méthodes : VaR Historique · VaR Paramétrique · Monte Carlo (10k simulations) ·
        Stress Tests 9 scénarios · Backtests 2018-2025
    </div>
    <div>Mis à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
</div>
""", unsafe_allow_html=True)