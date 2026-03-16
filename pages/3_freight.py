"""
Freight & Trade Logistics — avec carte des flux commerciaux mondiaux
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.graph_objects as go

st.set_page_config(page_title="Freight & Logistique", page_icon="🚢", layout="wide")
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


# ══════════════════════════════════════════════════════════════════════════════
# DONNÉES GÉOGRAPHIQUES — Flux commerciaux mondiaux
# ══════════════════════════════════════════════════════════════════════════════

# Ports majeurs avec coordonnées
PORTS = {
    # Origines exportatrices
    "us_gulf":             {"lat": 29.95,  "lon": -90.07, "name": "US Gulf (New Orleans)", "type": "origin"},
    "us_pnw":              {"lat": 46.20,  "lon": -123.8, "name": "US PNW (Portland)",     "type": "origin"},
    "brazil_santos":       {"lat": -23.95, "lon": -46.33, "name": "Santos (Brésil)",       "type": "origin"},
    "brazil_paranagua":    {"lat": -25.52, "lon": -48.52, "name": "Paranaguá (Brésil)",    "type": "origin"},
    "argentina_up":        {"lat": -32.95, "lon": -60.63, "name": "Up River (Argentine)",  "type": "origin"},
    "black_sea_odesa":     {"lat":  46.48, "lon":  30.73, "name": "Odesa (Ukraine)",       "type": "origin"},
    "black_sea_novor":     {"lat":  44.72, "lon":  37.77, "name": "Novorossiysk (Russie)", "type": "origin"},
    "australia_kwinana":   {"lat": -32.23, "lon": 115.78, "name": "Kwinana (Australie)",   "type": "origin"},

    # Destinations importatrices
    "egypt_damietta":      {"lat":  31.42, "lon":  31.81, "name": "Damietta (Égypte)",     "type": "destination"},
    "japan_osaka":         {"lat":  34.65, "lon": 135.43, "name": "Osaka (Japon)",         "type": "destination"},
    "china_shanghai":      {"lat":  31.23, "lon": 121.47, "name": "Shanghai (Chine)",      "type": "destination"},
    "netherlands_ara":     {"lat":  51.90, "lon":   4.48, "name": "Rotterdam (ARA)",       "type": "destination"},
    "turkey_derince":      {"lat":  40.75, "lon":  29.82, "name": "Derince (Turquie)",     "type": "destination"},
    "indonesia_jakarta":   {"lat":  -6.10, "lon": 106.83, "name": "Jakarta (Indonésie)",   "type": "destination"},
    "south_korea_busan":   {"lat":  35.10, "lon": 129.04, "name": "Busan (Corée du Sud)",  "type": "destination"},
    "spain_barcelona":     {"lat":  41.38, "lon":   2.17, "name": "Barcelone (Espagne)",   "type": "destination"},
}

# Flux commerciaux clés avec volume et commodité
TRADE_FLOWS = {
    "wheat": [
        {"from": "black_sea_odesa",   "to": "egypt_damietta",   "volume": 12.5, "label": "Blé Mer Noire → Égypte"},
        {"from": "black_sea_novor",   "to": "turkey_derince",   "volume":  8.0, "label": "Blé Russie → Turquie"},
        {"from": "us_gulf",           "to": "egypt_damietta",   "volume":  5.5, "label": "Blé US Gulf → Égypte"},
        {"from": "us_gulf",           "to": "netherlands_ara",  "volume":  4.5, "label": "Blé US → ARA"},
        {"from": "australia_kwinana", "to": "indonesia_jakarta","volume":  6.0, "label": "Blé Australie → Indonésie"},
        {"from": "black_sea_novor",   "to": "netherlands_ara",  "volume":  7.0, "label": "Blé Russie → Europe"},
        {"from": "us_gulf",           "to": "japan_osaka",      "volume":  2.5, "label": "Blé US → Japon"},
    ],
    "corn": [
        {"from": "us_gulf",           "to": "japan_osaka",      "volume": 10.5, "label": "Maïs US → Japon"},
        {"from": "brazil_santos",     "to": "china_shanghai",   "volume": 15.0, "label": "Maïs Brésil → Chine"},
        {"from": "us_gulf",           "to": "south_korea_busan","volume":  7.0, "label": "Maïs US → Corée"},
        {"from": "argentina_up",      "to": "netherlands_ara",  "volume":  8.5, "label": "Maïs Argentine → Europe"},
        {"from": "brazil_paranagua",  "to": "netherlands_ara",  "volume":  6.0, "label": "Maïs Brésil → ARA"},
        {"from": "us_gulf",           "to": "netherlands_ara",  "volume":  5.5, "label": "Maïs US → ARA"},
    ],
    "soybean": [
        {"from": "brazil_paranagua",  "to": "china_shanghai",   "volume": 45.0, "label": "Soja Brésil → Chine"},
        {"from": "us_gulf",           "to": "china_shanghai",   "volume": 22.0, "label": "Soja US → Chine"},
        {"from": "argentina_up",      "to": "china_shanghai",   "volume":  6.0, "label": "Soja Argentine → Chine"},
        {"from": "brazil_santos",     "to": "netherlands_ara",  "volume":  8.0, "label": "Soja Brésil → ARA"},
        {"from": "us_gulf",           "to": "netherlands_ara",  "volume":  4.5, "label": "Soja US → Europe"},
        {"from": "brazil_paranagua",  "to": "spain_barcelona",  "volume":  3.5, "label": "Soja Brésil → Espagne"},
    ],
}

COMMODITY_COLORS = {
    "wheat":   "#F9A825",
    "corn":    "#58A6FF",
    "soybean": "#3FB950",
}


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 0 18px 0;border-bottom:1px solid #1C2333;margin-bottom:20px">
    <div>
        <span style="font-size:1.5em;font-weight:800;color:#E6EDF3">🚢 Freight & Trade Logistics</span>
        <div style="font-size:0.78em;color:#8B949E;margin-top:3px">
            Flux Commerciaux · Baltic Indices · FOB→CIF · Arbitrage Inter-Origines
        </div>
    </div>
    <div style="font-size:0.75em;color:#8B949E">{datetime.now().strftime('%d %b %Y %H:%M')}</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 : Baltic Indices
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:12px">📊 BALTIC INDICES — COÛT DU FRET MARITIME</div>
""", unsafe_allow_html=True)

try:
    from config import DATA_RAW, DATA_PROCESSED, TRADE_ROUTES
    config_ok = True
except Exception as e:
    st.error(f"❌ Config introuvable : {e}")
    config_ok = False

bdi_current = 1800  # fallback

if config_ok:
    baltic_cfg = [
        ("bdi",  "Baltic Dry Index",   "#448AFF"),
        ("bpi",  "Panamax (Grains)",   "#F9A825"),
        ("bsi",  "Supramax",           "#3FB950"),
        ("bhsi", "Handysize",          "#FF9800"),
    ]
    cols_balt = st.columns(4)
    for col, (code, label, color) in zip(cols_balt, baltic_cfg):
        with col:
            path = DATA_RAW / f"baltic_{code}.csv"
            if path.exists():
                try:
                    df_b  = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
                    vals  = df_b["close"].dropna()
                    last  = float(vals.iloc[-1])
                    prev  = float(vals.iloc[-6])  if len(vals) > 5  else last
                    prev1m= float(vals.iloc[-22]) if len(vals) > 21 else last
                    chg   = ((last / prev)   - 1) * 100
                    chg1m = ((last / prev1m) - 1) * 100
                    c     = "#3FB950" if chg > 0 else "#F85149"
                    if code == "bdi":
                        bdi_current = int(last)
                    st.markdown(
                        f'<div style="background:#0D1117;border:1px solid #1C2333;'
                        f'border-top:3px solid {color};border-radius:8px;padding:14px">'
                        f'<div style="font-size:0.7em;color:#8B949E;margin-bottom:4px">{label}</div>'
                        f'<div style="font-size:1.5em;font-weight:700;color:{color};'
                        f'font-family:IBM Plex Mono,monospace">{last:,.0f}</div>'
                        f'<div style="display:flex;gap:12px;margin-top:6px;font-size:0.78em">'
                        f'<span style="color:{c};font-weight:600">{chg:+.1f}% 1S</span>'
                        f'<span style="color:#8B949E">{chg1m:+.1f}% 1M</span>'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.warning(f"{code}: {e}")
            else:
                st.markdown(
                    f'<div style="background:#0D1117;border:1px solid #1C2333;'
                    f'border-top:3px solid {color};border-radius:8px;padding:14px;opacity:0.5">'
                    f'<div style="font-size:0.7em;color:#8B949E">{label}</div>'
                    f'<div style="color:#8B949E;font-size:0.85em;margin-top:8px">'
                    f'Lance freight_pipeline.py</div></div>',
                    unsafe_allow_html=True
                )

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 : CARTE DES FLUX COMMERCIAUX
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">🗺️ CARTE DES FLUX COMMERCIAUX MONDIAUX</div>
""", unsafe_allow_html=True)

ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
with ctrl1:
    selected_commodity = st.selectbox(
        "Commodité",
        ["wheat", "corn", "soybean", "all"],
        format_func=lambda x: {
            "wheat": "🌾 Blé", "corn": "🌽 Maïs",
            "soybean": "🫘 Soja", "all": "🌍 Toutes"
        }[x],
        key="map_commodity"
    )
with ctrl2:
    show_labels = st.checkbox("Afficher les volumes", value=True)
with ctrl3:
    map_style = st.selectbox("Style", ["Dark", "Satellite"], key="map_style")

# Construction de la figure
fig_map = go.Figure()

# ── Fond de carte ─────────────────────────────────────────────────────────────
geo_style = "carto-darkmatter" if map_style == "Dark" else "stamen-terrain"

# ── Tracé des flux (lignes courbes) ──────────────────────────────────────────
commodities_to_show = (
    ["wheat", "corn", "soybean"] if selected_commodity == "all"
    else [selected_commodity]
)

max_volume = max(
    flow["volume"]
    for c in commodities_to_show
    for flow in TRADE_FLOWS.get(c, [])
)

for commodity in commodities_to_show:
    color = COMMODITY_COLORS[commodity]
    flows = TRADE_FLOWS.get(commodity, [])

    for flow in flows:
        orig = PORTS.get(flow["from"])
        dest = PORTS.get(flow["to"])
        if not orig or not dest:
            continue

        # Épaisseur proportionnelle au volume
        vol_norm = flow["volume"] / max_volume
        line_width = 1.5 + vol_norm * 5

        # Générer une courbe géodésique (plusieurs points intermédiaires)
        n_points = 20
        lats = []
        lons = []
        for t in np.linspace(0, 1, n_points):
            # Interpolation sphérique simplifiée
            lat = orig["lat"] + t * (dest["lat"] - orig["lat"])
            lon = orig["lon"] + t * (dest["lon"] - orig["lon"])
            # Courbure légère
            mid_t = 4 * t * (1 - t)
            lat += mid_t * 3 * np.sin(np.pi * t)
            lats.append(lat)
            lons.append(lon)

        # Ligne du flux
        fig_map.add_trace(go.Scattergeo(
            lat=lats,
            lon=lons,
            mode="lines",
            line=dict(
                width=line_width,
                color=color,
            ),
            opacity=0.6 if selected_commodity == "all" else 0.8,
            name=flow["label"],
            hovertemplate=(
                f"<b>{flow['label']}</b><br>"
                f"Volume: {flow['volume']:.1f} MMT/an<br>"
                f"<extra></extra>"
            ),
            showlegend=False,
        ))

        # Flèche à la destination
        fig_map.add_trace(go.Scattergeo(
            lat=[lats[-3], dest["lat"]],
            lon=[lons[-3], dest["lon"]],
            mode="lines",
            line=dict(width=line_width + 1, color=color),
            opacity=0.9,
            showlegend=False,
            hoverinfo="skip",
        ))

        # Label volume au milieu
        if show_labels and flow["volume"] >= 6.0:
            mid_idx = n_points // 2
            fig_map.add_trace(go.Scattergeo(
                lat=[lats[mid_idx]],
                lon=[lons[mid_idx]],
                mode="text",
                text=[f"{flow['volume']:.0f}M"],
                textfont=dict(size=9, color=color),
                showlegend=False,
                hoverinfo="skip",
            ))

# ── Ports — origines ─────────────────────────────────────────────────────────
origin_ports = {k: v for k, v in PORTS.items() if v["type"] == "origin"}
fig_map.add_trace(go.Scattergeo(
    lat=[p["lat"] for p in origin_ports.values()],
    lon=[p["lon"] for p in origin_ports.values()],
    mode="markers+text",
    marker=dict(
        size=10,
        color="#F9A825",
        symbol="circle",
        line=dict(color="#070B14", width=2),
    ),
    text=[p["name"] for p in origin_ports.values()],
    textposition="top right",
    textfont=dict(size=8, color="#F9A825"),
    name="🟡 Origine (export)",
    hovertemplate="<b>%{text}</b><extra></extra>",
))

# ── Ports — destinations ──────────────────────────────────────────────────────
dest_ports = {k: v for k, v in PORTS.items() if v["type"] == "destination"}
fig_map.add_trace(go.Scattergeo(
    lat=[p["lat"] for p in dest_ports.values()],
    lon=[p["lon"] for p in dest_ports.values()],
    mode="markers+text",
    marker=dict(
        size=10,
        color="#58A6FF",
        symbol="diamond",
        line=dict(color="#070B14", width=2),
    ),
    text=[p["name"] for p in dest_ports.values()],
    textposition="top left",
    textfont=dict(size=8, color="#58A6FF"),
    name="🔷 Destination (import)",
    hovertemplate="<b>%{text}</b><extra></extra>",
))

# ── Layout carte ──────────────────────────────────────────────────────────────
fig_map.update_layout(
    paper_bgcolor="#070B14",
    geo=dict(
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#1C2333",
        coastlinewidth=0.8,
        showland=True,
        landcolor="#0D1117",
        showocean=True,
        oceancolor="#070B14",
        showlakes=False,
        showrivers=False,
        showcountries=True,
        countrycolor="#1C2333",
        countrywidth=0.5,
        bgcolor="#070B14",
        projection_type="natural earth",
        lataxis=dict(range=[-55, 70]),
        lonaxis=dict(range=[-150, 160]),
    ),
    legend=dict(
        bgcolor="rgba(13,17,23,0.85)",
        bordercolor="#1C2333",
        borderwidth=1,
        font=dict(color="#8B949E", size=10),
        x=0.01, y=0.99,
        xanchor="left", yanchor="top",
    ),
    height=480,
    margin=dict(l=0, r=0, t=0, b=0),
)

st.plotly_chart(fig_map, use_container_width=True,
                config={"displayModeBar": True,
                        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        "displaylogo": False})

# Légende commodités
_legend_html = '<div style="display:flex;gap:16px;margin-bottom:4px;flex-wrap:wrap">'
if selected_commodity == "all":
    for c, col in COMMODITY_COLORS.items():
        _legend_html += (
            f'<div style="display:flex;align-items:center;gap:6px">'
            f'<div style="width:24px;height:3px;background:{col};border-radius:2px"></div>'
            f'<span style="font-size:0.78em;color:#8B949E">'
            f'{"🌾 Blé" if c=="wheat" else "🌽 Maïs" if c=="corn" else "🫘 Soja"}</span>'
            f'</div>'
        )
else:
    col = COMMODITY_COLORS[selected_commodity]
    total_vol = sum(f["volume"] for f in TRADE_FLOWS.get(selected_commodity, []))
    _legend_html += (
        f'<div style="font-size:0.78em;color:#8B949E">'
        f'Épaisseur des lignes ∝ volume · '
        f'Volume total affiché : <b style="color:{col}">{total_vol:.0f} MMT/an</b></div>'
    )
_legend_html += '</div>'
st.markdown(_legend_html, unsafe_allow_html=True)

# ── Top routes par volume ─────────────────────────────────────────────────────
st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

all_flows = []
for c in commodities_to_show:
    for flow in TRADE_FLOWS.get(c, []):
        all_flows.append({
            "Commodité": {"wheat":"🌾 Blé","corn":"🌽 Maïs","soybean":"🫘 Soja"}[c],
            "Route":     flow["label"],
            "Volume":    flow["volume"],
            "Couleur":   COMMODITY_COLORS[c],
        })

all_flows.sort(key=lambda x: x["Volume"], reverse=True)

_flow_rows = ""
for i, flow in enumerate(all_flows[:8]):
    bar_pct = int(flow["Volume"] / max_volume * 100)
    _flow_rows += (
        f'<tr style="border-bottom:1px solid #1C2333">'
        f'<td style="padding:6px 10px;color:#8B949E;font-size:0.85em">#{i+1}</td>'
        f'<td style="padding:6px 10px;color:#E6EDF3;font-size:0.85em">{flow["Route"]}</td>'
        f'<td style="padding:6px 10px;width:120px">'
        f'<div style="background:#1C2333;border-radius:3px;height:5px">'
        f'<div style="background:{flow["Couleur"]};width:{bar_pct}%;height:5px;'
        f'border-radius:3px"></div></div></td>'
        f'<td style="padding:6px 10px;color:{flow["Couleur"]};font-weight:700;'
        f'text-align:right;font-family:IBM Plex Mono,monospace">'
        f'{flow["Volume"]:.1f} MMT</td>'
        f'</tr>'
    )

col_top, col_ins = st.columns([2, 1])
with col_top:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;
                letter-spacing:1px;margin-bottom:8px">🏆 TOP ROUTES PAR VOLUME</div>
    """, unsafe_allow_html=True)
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:0.82em">'
        f'<thead><tr style="border-bottom:1px solid #30363D">'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:500">#</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:left">Route</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:500">Volume</th>'
        f'<th style="padding:6px 10px;color:#8B949E;font-weight:500;text-align:right">MMT/an</th>'
        f'</tr></thead>'
        f'<tbody>{_flow_rows}</tbody>'
        f'</table>',
        unsafe_allow_html=True
    )

with col_ins:
    st.markdown("""
    <div style="font-size:0.68em;color:#8B949E;font-weight:600;
                letter-spacing:1px;margin-bottom:8px">💡 INSIGHTS CLÉS</div>
    """, unsafe_allow_html=True)
    insights = [
        ("🫘", "#3FB950", "Brésil → Chine",
         "Route #1 mondiale soja (45 MMT). Chine = 60% des imports mondiaux."),
        ("🌾", "#F9A825", "Mer Noire → Monde",
         "Russie + Ukraine = 30% exports blé. Zone de risque géopolitique majeure."),
        ("🌽", "#58A6FF", "Brésil vs US",
         "Brésil dépasse parfois les US. Saison miroir = compétition tout l'année."),
        ("🚢", "#FF9800", "BDI Impact",
         f"BDI actuel ~{bdi_current:,}. +500pts ≈ +$3-8/t sur routes longues."),
    ]
    _ins_html = ""
    for icon, col_i, title, desc in insights:
        _ins_html += (
            f'<div style="background:#0D1117;border:1px solid #1C2333;'
            f'border-left:3px solid {col_i};border-radius:6px;'
            f'padding:10px 12px;margin-bottom:8px">'
            f'<div style="font-size:0.82em;font-weight:700;color:#E6EDF3;margin-bottom:3px">'
            f'{icon} {title}</div>'
            f'<div style="font-size:0.75em;color:#8B949E;line-height:1.4">{desc}</div>'
            f'</div>'
        )
    st.markdown(_ins_html, unsafe_allow_html=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 : Calculateur FOB → CIF Interactif
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">🧮 CALCULATEUR FOB → CIF INTERACTIF</div>
""", unsafe_allow_html=True)

try:
    from module_2_freight.calculators.freight_calculator import estimate_freight_cost
    from module_2_freight.calculators.arbitrage_calculator import compare_origins_for_destination
    freight_available = True
except Exception as e:
    st.warning(f"⚠️ Module freight : {e}")
    freight_available = False

if freight_available and config_ok:
    col_params, col_result = st.columns([1, 1])

    with col_params:
        route_options = list(TRADE_ROUTES.keys())
        route = st.selectbox(
            "Route commerciale",
            route_options,
            format_func=lambda x: (
                f"{TRADE_ROUTES[x]['from'].replace('_',' ').title()} → "
                f"{TRADE_ROUTES[x]['to'].replace('_',' ').title()} "
                f"({TRADE_ROUTES[x]['commodity']})"
            )
        )
        fob_price = st.number_input(
            "Prix FOB ($/tonne)", min_value=50.0, max_value=1000.0,
            value=220.0, step=5.0
        )
        bdi_val = st.number_input(
            "BDI actuel", min_value=200, max_value=10000,
            value=bdi_current, step=50
        )
        quantity = st.number_input(
            "Quantité (tonnes)", min_value=5000, max_value=200000,
            value=50000, step=5000
        )

    with col_result:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🧮 Calculer le CIF", type="primary", use_container_width=True):
            try:
                result = estimate_freight_cost(
                    route_key=route,
                    fob_price_per_ton=fob_price,
                    quantity_tons=quantity,
                    bdi_current=bdi_val,
                )
                frt = result["freight_per_ton"]
                cif = result["cif_per_ton"]
                frt_pct = frt / fob_price * 100

                st.markdown(
                    f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:12px;'
                    f'padding:20px">'
                    f'<div style="font-size:0.7em;color:#8B949E;margin-bottom:14px;font-weight:600">'
                    f'DÉCOMPOSITION DU PRIX</div>'
                    f'<div style="display:flex;flex-direction:column;gap:6px;font-size:0.85em">'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<span style="color:#8B949E">📦 Prix FOB</span>'
                    f'<span style="color:#E6EDF3;font-family:IBM Plex Mono,monospace">'
                    f'${fob_price:.2f}/t</span></div>'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<span style="color:#8B949E">🚢 Fret ({result["voyage_days"]:.0f}j · '
                    f'{result["distance_nm"]:,}nm)</span>'
                    f'<span style="color:#F0B429;font-family:IBM Plex Mono,monospace">'
                    f'+${frt:.2f}/t ({frt_pct:.1f}%)</span></div>'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<span style="color:#8B949E">🛡️ Assurance</span>'
                    f'<span style="color:#8B949E;font-family:IBM Plex Mono,monospace">'
                    f'+${result["insurance_per_ton"]:.2f}/t</span></div>'
                    f'<div style="border-top:1px solid #1C2333;margin-top:6px;padding-top:10px;'
                    f'display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="color:#3FB950;font-weight:700;font-size:1.05em">PRIX CIF</span>'
                    f'<span style="color:#3FB950;font-weight:800;font-size:1.4em;'
                    f'font-family:IBM Plex Mono,monospace">${cif:.2f}/t</span></div>'
                    f'</div>'
                    f'<div style="border-top:1px solid #1C2333;margin-top:12px;padding-top:10px;'
                    f'font-size:0.8em;color:#8B949E">'
                    f'Valeur cargo : <b style="color:#58A6FF">'
                    f'${cif * quantity:,.0f}</b> · '
                    f'TCE : <b>${result["tce_per_day_usd"]:,}/jour</b>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"Erreur calcul : {e}")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 : Arbitrage Inter-Origines
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">🌍 ARBITRAGE INTER-ORIGINES</div>
""", unsafe_allow_html=True)

if freight_available and config_ok:

    # Détecte automatiquement les routes disponibles par commodité + destination
    def get_available_routes(commodity_filter=None):
        routes = {}
        for route_key, route_info in TRADE_ROUTES.items():
            if commodity_filter and route_info["commodity"] != commodity_filter:
                continue
            dest_key = route_info["to"]
            if dest_key not in routes:
                routes[dest_key] = []
            routes[dest_key].append({
                "route_key": route_key,
                "from":      route_info["from"],
                "commodity": route_info["commodity"],
            })
        return routes

    col_arb1, col_arb2 = st.columns(2)

    with col_arb1:
        commodity_arb = st.selectbox(
            "Commodité",
            ["wheat", "corn", "soybean"],
            format_func=lambda x: {"wheat":"🌾 Blé","corn":"🌽 Maïs","soybean":"🫘 Soja"}[x],
            key="arb_commodity"
        )

        # Destinations disponibles pour cette commodité
        available = get_available_routes(commodity_arb)
        dest_labels = {
            "egypt_damietta":    "🇪🇬 Égypte (Damietta)",
            "japan_osaka":       "🇯🇵 Japon (Osaka)",
            "china_shanghai":    "🇨🇳 Chine (Shanghai)",
            "netherlands_ara":   "🇳🇱 Rotterdam (ARA)",
            "turkey_derince":    "🇹🇷 Turquie (Derince)",
            "indonesia_jakarta": "🇮🇩 Indonésie (Jakarta)",
            "south_korea_busan": "🇰🇷 Corée du Sud (Busan)",
            "spain_barcelona":   "🇪🇸 Barcelone (Espagne)",
        }
        dest_options = {k: dest_labels.get(k, k) for k in available}

        if not dest_options:
            st.warning("Aucune route disponible pour cette commodité.")
            st.stop()

        dest_arb = st.selectbox(
            "Destination",
            list(dest_options.keys()),
            format_func=lambda x: dest_options[x],
            key="arb_dest"
        )
        bdi_arb = st.number_input(
            "BDI actuel", value=bdi_current, step=50, key="bdi_arb2"
        )

        # Origines disponibles pour cette route
        origins_for_route = available.get(dest_arb, [])
        origin_keys = list({r["from"] for r in origins_for_route})

    with col_arb2:
        st.markdown("**Prix FOB par origine ($/tonne)**")

        # Prix FOB de référence par commodité
        fob_ref = {
            "wheat":   {"us_gulf":220,"black_sea_odesa":195,"black_sea_novor":192,
                        "australia_kwinana":210,"argentina_up":200},
            "corn":    {"us_gulf":185,"brazil_santos":175,"brazil_paranagua":175,
                        "argentina_up":170,"black_sea_odesa":172},
            "soybean": {"us_gulf":395,"brazil_paranagua":380,"brazil_santos":380,
                        "argentina_up":365},
        }

        fob_inputs = {}
        for origin in origin_keys:
            default = fob_ref.get(commodity_arb, {}).get(origin, 200.0)
            # Label lisible
            origin_label = origin.replace("_", " ").title()
            fob_inputs[origin] = st.number_input(
                origin_label,
                value=float(default),
                step=5.0,
                key=f"arb_fob_{origin}_{commodity_arb}_{dest_arb}"
            )

    if st.button("🌍 Lancer l'arbitrage", type="primary", use_container_width=True):
        try:
            df_arb = compare_origins_for_destination(
                destination_key=dest_arb,
                commodity=commodity_arb,
                fob_prices=fob_inputs,
                bdi_current=bdi_arb,
            )

            if df_arb is not None and not df_arb.empty:
                # Graphique barres empilées
                fig_arb = go.Figure()
                fig_arb.add_trace(go.Bar(
                    x=df_arb["origin"].str[:25],
                    y=df_arb["fob_usd_t"],
                    name="FOB",
                    marker_color=hex_to_rgba("#8B949E", 0.6),
                ))
                fig_arb.add_trace(go.Bar(
                    x=df_arb["origin"].str[:25],
                    y=df_arb["freight_usd_t"],
                    name="Fret",
                    marker_color=hex_to_rgba("#F0B429", 0.8),
                ))
                if "insurance_usd_t" in df_arb.columns:
                    fig_arb.add_trace(go.Bar(
                        x=df_arb["origin"].str[:25],
                        y=df_arb["insurance_usd_t"],
                        name="Assurance",
                        marker_color=hex_to_rgba("#58A6FF", 0.6),
                    ))

                fig_arb.update_layout(
                    paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
                    font=dict(color="#8B949E", size=10),
                    height=280, margin=dict(l=5,r=5,t=10,b=5),
                    barmode="stack",
                    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
                    yaxis=dict(gridcolor="#1C2333", title="$/tonne"),
                    xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig_arb, use_container_width=True,
                                config={"displayModeBar": False})

                # Tableau
                cols_show = ["rank","origin","fob_usd_t","freight_usd_t",
                             "cif_usd_t","spread_vs_cheapest","voyage_days"]
                cols_show = [c for c in cols_show if c in df_arb.columns]
                st.dataframe(
                    df_arb[cols_show].rename(columns={
                        "rank":"Rang","origin":"Origine",
                        "fob_usd_t":"FOB $/t","freight_usd_t":"Fret $/t",
                        "cif_usd_t":"CIF $/t",
                        "spread_vs_cheapest":"Spread vs Best",
                        "voyage_days":"Jours"
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

                best   = df_arb.iloc[0]
                worst  = df_arb.iloc[-1]
                spread = worst["cif_usd_t"] - best["cif_usd_t"]
                st.success(
                    f"✅ **Meilleure origine** : **{best['origin']}** "
                    f"à **${best['cif_usd_t']:.1f}/t CIF** "
                    f"— Avantage **${spread:.1f}/t** vs {worst['origin']}"
                )
            else:
                st.warning(
                    f"Aucune route trouvée pour {commodity_arb} → {dest_arb}. "
                    f"Vérifie que les origines correspondent aux routes dans TRADE_ROUTES."
                )

        except Exception as e:
            st.error(f"Erreur arbitrage : {e}")
            import traceback
            st.code(traceback.format_exc())
else:
    st.info("Module freight non disponible.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 : Sensibilité BDI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:0.68em;color:#8B949E;font-weight:600;letter-spacing:1px;
            margin-bottom:14px">📉 SENSIBILITÉ DU PRIX CIF AU BDI</div>
""", unsafe_allow_html=True)

if freight_available and config_ok:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        route_sens = st.selectbox(
            "Route", list(TRADE_ROUTES.keys()), key="route_sens",
            format_func=lambda x: (
                f"{TRADE_ROUTES[x]['from'].replace('_',' ').title()} → "
                f"{TRADE_ROUTES[x]['to'].replace('_',' ').title()}"
            )
        )
    with col_s2:
        fob_sens = st.number_input("FOB référence ($/t)", value=220.0, step=5.0)

    bdi_range  = list(range(500, 4001, 250))
    cif_values, frt_values = [], []
    for b in bdi_range:
        try:
            r = estimate_freight_cost(route_key=route_sens,
                                      fob_price_per_ton=fob_sens, bdi_current=b)
            cif_values.append(r["cif_per_ton"])
            frt_values.append(r["freight_per_ton"])
        except:
            cif_values.append(None)
            frt_values.append(None)

    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(
        x=bdi_range, y=cif_values, name="CIF total",
        line=dict(color="#3FB950", width=2.5),
        fill="tozeroy", fillcolor="rgba(63,185,80,0.06)",
    ))
    fig_sens.add_trace(go.Scatter(
        x=bdi_range, y=frt_values, name="Fret seul",
        line=dict(color="#F0B429", width=2, dash="dot"),
    ))
    fig_sens.add_vline(
        x=bdi_current, line_dash="dash", line_color="#58A6FF",
        annotation_text=f"BDI actuel {bdi_current:,}",
        annotation_font=dict(color="#58A6FF", size=10),
        annotation_position="top right",
    )
    fig_sens.update_layout(
        paper_bgcolor="#070B14", plot_bgcolor="#0D1117",
        font=dict(color="#8B949E", size=10),
        height=300,
        margin=dict(l=5, r=10, t=10, b=5),
        xaxis=dict(gridcolor="#1C2333", title="BDI"),
        yaxis=dict(gridcolor="#1C2333", title="$/tonne"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    )
    st.plotly_chart(fig_sens, use_container_width=True,
                    config={"displayModeBar": False})

    # Calcul d'impact
    if cif_values and len([v for v in cif_values if v]) >= 2:
        valid = [(b, c) for b, c in zip(bdi_range, cif_values) if c]
        cif_500  = valid[0][1]  if valid else 0
        cif_4000 = valid[-1][1] if valid else 0
        impact   = cif_4000 - cif_500
        st.markdown(
            f'<div style="background:#0D1117;border:1px solid #1C2333;border-radius:6px;'
            f'padding:10px 14px;font-size:0.8em;color:#8B949E">'
            f'💡 Sur cette route, quand le BDI passe de 500 à 4000 points, '
            f'le prix CIF augmente de '
            f'<b style="color:#F0B429">${impact:.1f}/tonne</b> — '
            f'soit <b style="color:#F0B429">{impact/fob_sens*100:.1f}%</b> du prix FOB. '
            f'Un cargo de 50 000t représente <b style="color:#F85149">'
            f'${impact*50000:,.0f}</b> d\'écart.</div>',
            unsafe_allow_html=True
        )