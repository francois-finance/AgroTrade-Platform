"""
Composants UI réutilisables pour Streamlit.
"""

import streamlit as st


def metric_card(label: str, value: str, delta: str = None,
                color: str = "white", icon: str = ""):
    """Card de métrique stylisée"""
    delta_html = ""
    if delta:
        delta_color = "#00C853" if "+" in str(delta) else "#FF1744"
        delta_html = f'<div style="color:{delta_color};font-size:0.85em">{delta}</div>'

    st.markdown(f"""
    <div style="
        background: #1E2130;
        border-radius: 12px;
        padding: 16px 20px;
        border-left: 4px solid {color};
        margin-bottom: 8px;
    ">
        <div style="color:#9E9E9E;font-size:0.8em;margin-bottom:4px">{icon} {label}</div>
        <div style="color:{color};font-size:1.4em;font-weight:700">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def signal_badge(direction: str) -> str:
    """Badge HTML coloré pour la direction"""
    colors = {
        "BULLISH": ("#00C853", "▲"),
        "BEARISH": ("#FF1744", "▼"),
        "NEUTRAL": ("#FFD600", "—"),
    }
    key = "BULLISH" if "BULL" in direction.upper() else (
          "BEARISH" if "BEAR" in direction.upper() else "NEUTRAL")
    color, icon = colors[key]
    return (f'<span style="background:{color}22;color:{color};'
            f'padding:3px 10px;border-radius:20px;font-weight:700">'
            f'{icon} {key}</span>')


def section_header(title: str, subtitle: str = ""):
    """En-tête de section"""
    st.markdown(f"""
    <div style="margin: 20px 0 10px 0">
        <h3 style="color:#FAFAFA;margin:0">{title}</h3>
        <p style="color:#9E9E9E;margin:4px 0 0 0;font-size:0.9em">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)