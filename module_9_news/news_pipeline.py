"""
News Pipeline — Module 9
Orchestrateur principal : collecte RSS → analyse LLM → alertes → sauvegarde
"""
from dotenv import load_dotenv
load_dotenv()
import json
import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from rich.console import Console
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
console = Console()

# Chemins
BASE_DIR     = Path(__file__).parent.parent
DATA_NEWS    = BASE_DIR / "data" / "news"
DATA_PROC    = BASE_DIR / "data" / "processed"
SOURCES_PATH = Path(__file__).parent / "sources_rss.yaml"


# ══════════════════════════════════════════════════════════════════════════════
# ALERT ENGINE — repris de ton alerts.py
# ══════════════════════════════════════════════════════════════════════════════

RISK_KEYWORDS = {
    # Météo / récolte
    "drought": 3, "sécheresse": 3, "sequia": 3, "seca": 3,
    "frost": 3, "gel": 3, "helada": 3, "geada": 3,
    "hail": 2, "grêle": 2, "granizo": 2,
    "heatwave": 2, "canicule": 2, "ola de calor": 2,
    "flood": 2, "flooding": 2, "inondation": 2,
    "el nino": 2, "la nina": 2, "enso": 1,
    # Logistique
    "port closed": 4, "port closure": 4, "porto fechado": 4,
    "strike": 3, "grève": 3, "huelga": 3, "greve": 3,
    "blockade": 4, "blocus": 4, "grain corridor": 3,
    # Politique / commerce
    "export ban": 4, "export restriction": 3, "export taxes": 3,
    "quota": 2, "embargo": 4, "sanction": 3, "sanctions": 3,
    # Conflit
    "attack": 3, "bombardment": 3, "missile": 3,
    "war": 2, "guerre": 2, "conflict": 2,
    # Production
    "crop failure": 4, "harvest loss": 3,
    "poor yields": 3, "yield loss": 3,
}


def compute_alert(article: dict) -> dict:
    """Calcule le score d'alerte d'un article."""
    full = f"{article.get('title','')} {article.get('analysis','')} {article.get('text','')}".lower()

    score = 0
    tags  = []

    for kw, weight in RISK_KEYWORDS.items():
        if kw in full:
            score += weight
            tags.append(kw)

    # Bonus event type
    if article.get("event_type") in ("weather", "logistics", "trade", "politics"):
        score += 1

    # Bonus sentiment fort
    if article.get("sentiment") in ("bullish", "bearish"):
        score += 1

    # Bonus groupe géopolitique / shipping
    if article.get("source_group") in ("geopolitics", "shipping"):
        score += 1

    # Severity
    if score >= 7:
        severity = "critical"
    elif score >= 4:
        severity = "watch"
    elif score >= 2:
        severity = "info"
    else:
        severity = "none"

    return {
        **article,
        "alert_score":    score,
        "alert_severity": severity,
        "alert_tags":     ", ".join(sorted(set(tags))),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MACRO SCORER — repris de ton scoring_macro.py
# ══════════════════════════════════════════════════════════════════════════════

def compute_macro_score(macro_rows: list[dict]) -> dict:
    """Calcule le score macro-grains par thème."""

    def sent_score(s):
        s = (s or "").lower()
        return 1 if "bull" in s else (-1 if "bear" in s else 0)

    def classify_theme(row):
        et  = (row.get("event_type") or "").lower()
        url = (row.get("url") or "").lower()
        if et == "weather" or any(x in url for x in ["noaa","droughtmonitor","ecmwf","climate"]):
            return "weather"
        if any(x in url for x in ["currencies","dollar-index","usd-brl","usd-ars"]):
            return "fx"
        if any(x in url for x in ["brent","eia.gov","energy"]):
            return "energy"
        if et == "logistics" or any(x in url for x in ["splash247","blackseagrain","baltic"]):
            return "shipping"
        return "other"

    scores = {"weather": 0, "fx": 0, "energy": 0, "shipping": 0, "other": 0}
    for r in macro_rows:
        theme = classify_theme(r)
        scores[theme] += sent_score(r.get("sentiment"))

    final = sum(scores.values())
    final = max(-5, min(5, final))

    return {"final_macro_score": final, **scores}


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE
# ══════════════════════════════════════════════════════════════════════════════

def save_news(articles: list[dict]) -> dict:
    """
    Sauvegarde les articles en 3 formats :
    - JSON complet (toutes les données)
    - CSV signaux (pour compatibilité avec le reste d'AgroTrade)
    - JSON résumé (pour la page Streamlit)
    """
    DATA_NEWS.mkdir(parents=True, exist_ok=True)
    DATA_PROC.mkdir(parents=True, exist_ok=True)

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    # 1. JSON complet
    json_path = DATA_NEWS / f"news_{today}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2, default=str)

    # 2. CSV signaux (compatible avec l'ancien pipeline)
    csv_path = DATA_PROC / f"signals_{today}.csv"
    if articles:
        fields = [
            "source_name", "source_group", "url", "title", "published",
            "commodity", "event_type", "sentiment", "sentiment_score",
            "analysis", "impact", "outlook",
            "alert_score", "alert_severity", "alert_tags",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for a in articles:
                # Ajoute sentiment_score numérique
                sent = a.get("sentiment", "neutral")
                a["sentiment_score"] = 1 if sent == "bullish" else (-1 if sent == "bearish" else 0)
                writer.writerow(a)

    # 3. JSON résumé pour Streamlit
    summary = _build_summary(articles)
    summary_path = DATA_PROC / "news_summary_latest.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    console.print(f"[blue]💾 JSON : {json_path}[/blue]")
    console.print(f"[blue]💾 CSV  : {csv_path}[/blue]")
    console.print(f"[blue]💾 Summary : {summary_path}[/blue]")

    return {
        "json_path":    str(json_path),
        "csv_path":     str(csv_path),
        "summary_path": str(summary_path),
    }


def _build_summary(articles: list[dict]) -> dict:
    """Construit le JSON résumé pour la page Streamlit."""
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Groupe par commodité
    by_commodity = {"wheat": [], "corn": [], "soy": [], "other": []}
    for a in articles:
        c = a.get("commodity", "other")
        if c not in by_commodity:
            c = "other"
        by_commodity[c].append(a)

    # Alertes
    alerts = [
        a for a in articles
        if a.get("alert_severity") in ("watch", "critical")
    ]
    alerts.sort(key=lambda x: x.get("alert_score", 0), reverse=True)

    # Macro score
    macro_rows = [a for a in articles if a.get("commodity") == "other"]
    macro_score = compute_macro_score(macro_rows)

    # Sentiment par commodité
    sentiment_summary = {}
    for c, rows in by_commodity.items():
        if not rows:
            continue
        scores = [
            1 if r.get("sentiment") == "bullish" else
            (-1 if r.get("sentiment") == "bearish" else 0)
            for r in rows
        ]
        avg = sum(scores) / len(scores) if scores else 0
        sentiment_summary[c] = {
            "n_articles": len(rows),
            "avg_sentiment": round(avg, 2),
            "bullish": sum(1 for s in scores if s > 0),
            "bearish": sum(1 for s in scores if s < 0),
            "neutral": sum(1 for s in scores if s == 0),
            "top_articles": [
                {
                    "title":     a.get("title", ""),
                    "url":       a.get("url", ""),
                    "sentiment": a.get("sentiment", "neutral"),
                    "analysis":  a.get("analysis", ""),
                    "impact":    a.get("impact", ""),
                    "outlook":   a.get("outlook", ""),
                    "source":    a.get("source_name", ""),
                    "published": a.get("published", ""),
                }
                for a in rows[:5]
            ],
        }

    return {
        "generated_at":     today,
        "total_articles":   len(articles),
        "macro_score":      macro_score,
        "sentiment_by_commodity": sentiment_summary,
        "top_alerts":       [
            {
                "title":    a.get("title", ""),
                "url":      a.get("url", ""),
                "severity": a.get("alert_severity", ""),
                "score":    a.get("alert_score", 0),
                "tags":     a.get("alert_tags", ""),
                "commodity":a.get("commodity", ""),
                "analysis": a.get("analysis", ""),
            }
            for a in alerts[:10]
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def run_news_pipeline(
    groups: list[str] | None = None,
    max_articles_llm: int = 25,
) -> dict:
    """
    Lance le pipeline complet :
    1. Collecte RSS
    2. Analyse LLM
    3. Calcul alertes
    4. Sauvegarde

    Args:
        groups           : groupes de sources à inclure (None = tous)
        max_articles_llm : max articles envoyés au LLM (quota Groq)

    Returns:
        dict avec chemins des fichiers sauvegardés + résumé
    """
    console.print("\n[bold cyan]🌾 AgroTrade — News Pipeline[/bold cyan]\n")
    console.print(f"[dim]Démarrage : {datetime.now().strftime('%Y-%m-%d %H:%M')}[/dim]\n")

    # ── Étape 1 : Collecte RSS ────────────────────────────────────────────────
    console.print("[bold]Étape 1/4 — Collecte RSS[/bold]")
    from module_9_news.collectors.news_collector import collect_all_news
    articles = collect_all_news(
        sources_path=SOURCES_PATH,
        groups=groups,
    )

    if not articles:
        console.print("[red]✗ Aucun article collecté.[/red]")
        return {}

    # ── Étape 2 : Analyse LLM ────────────────────────────────────────────────
    console.print(f"\n[bold]Étape 2/4 — Analyse LLM ({min(len(articles), max_articles_llm)} articles)[/bold]")
    from module_9_news.processors.llm_analyzer import analyze_batch
    analyzed = analyze_batch(articles, max_articles=max_articles_llm)

    # ── Étape 3 : Alertes ────────────────────────────────────────────────────
    console.print("\n[bold]Étape 3/4 — Calcul des alertes[/bold]")
    alerted = [compute_alert(a) for a in analyzed]

    n_critical = sum(1 for a in alerted if a.get("alert_severity") == "critical")
    n_watch    = sum(1 for a in alerted if a.get("alert_severity") == "watch")
    console.print(f"  🚨 Critical : {n_critical} | ⚠️  Watch : {n_watch}")

    # ── Étape 4 : Sauvegarde ─────────────────────────────────────────────────
    console.print("\n[bold]Étape 4/4 — Sauvegarde[/bold]")
    paths = save_news(alerted)

    console.print("\n[bold green]✅ Pipeline terminé ![/bold green]")
    return paths


if __name__ == "__main__":
    run_news_pipeline()