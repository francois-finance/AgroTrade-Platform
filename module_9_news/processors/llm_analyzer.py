"""
LLM Analyzer — Module 9
Analyse chaque article avec Groq/Llama et extrait les champs structurés.
Basé sur llm_summarizer.py existant, amélioré et intégré à AgroTrade.
"""

import json
import os
from pathlib import Path
from rich.console import Console

console = Console()

# Mots-clés pour filtrer le texte avant envoi au LLM
GRAIN_KEYWORDS = [
    # Wheat
    "wheat", "blé", "ble", "trigo", "пшеница", "пшениця", "小麦",
    # Corn
    "corn", "maïs", "mais", "maiz", "milho", "кукуруза", "玉米",
    # Soy
    "soy", "soja", "soybean", "soybeans", "大豆",
    # General
    "grain", "grains", "céréale", "cereal", "зерно",
    # Agri
    "harvest", "récolte", "cosecha", "colheita",
    "yield", "rendement", "crop",
    "drought", "sécheresse", "sequia", "seca",
    "export", "import", "stocks", "supply", "oferta",
    "freight", "fret", "shipping", "corridor",
    "WASDE", "USDA", "FAO", "futures", "CBOT",
    "tariff", "embargo", "sanction",
    "El Niño", "La Niña", "ENSO",
]

PROMPT_TEMPLATE = """Tu es un analyste senior sur un desk de trading de matières premières agricoles (grains).

Analyse le texte ci-dessous et extrait les informations clés pour un trader.

TEXTE :
{TEXT}

Réponds UNIQUEMENT en JSON strict avec cette structure :

{{
  "commodity": "wheat | corn | soy | other",
  "event_type": "weather | stocks | production | trade | politics | logistics | other",
  "sentiment": "bullish | bearish | neutral",
  "analysis": "Analyse de marché en français, 3-5 phrases orientées prix et trading",
  "impact": "Impact direct sur les prix, 1-2 phrases (ex: +2-4% haussier court terme)",
  "risks": ["risque 1", "risque 2", "risque 3"],
  "outlook": "Perspective 1-2 semaines pour les prix"
}}

Règles STRICTES :
- commodity: blé/wheat → "wheat", maïs/corn/maize → "corn", soja/soy → "soy", sinon → "other"
- sentiment = impact sur les PRIX : haussier → "bullish", baissier → "bearish", neutre → "neutral"
- Si le texte ne parle pas de grains/agri → commodity="other", sentiment="neutral"
- Réponds UNIQUEMENT avec le JSON, sans texte avant ni après
"""


def _filter_relevant_text(text: str, max_chars: int = 4000) -> str:
    """
    Garde les paragraphes contenant des mots-clés agri.
    Si rien trouvé, retourne le début du texte.
    """
    if not text:
        return ""

    paragraphs = [p.strip() for p in text.replace("\n", " ").split(". ") if p.strip()]
    selected = []

    for p in paragraphs:
        if any(kw.lower() in p.lower() for kw in GRAIN_KEYWORDS):
            selected.append(p)

    if selected:
        return ". ".join(selected)[:max_chars]

    return text[:max_chars]


def _normalize(raw: dict) -> dict:
    """Normalise et valide les champs du JSON LLM."""
    # Commodity
    c = (raw.get("commodity") or "other").strip().lower()
    if c in ["blé", "ble", "wheat", "trigo"]:
        commodity = "wheat"
    elif c in ["maïs", "mais", "corn", "maize", "milho"]:
        commodity = "corn"
    elif c in ["soja", "soy", "soybean", "soybeans"]:
        commodity = "soy"
    else:
        commodity = "other"

    # Event type
    et = (raw.get("event_type") or "other").strip().lower()
    event_map = {
        "weather": "weather", "météo": "weather",
        "stocks": "stocks", "inventaires": "stocks",
        "production": "production", "harvest": "production",
        "trade": "trade", "commerce": "trade",
        "politics": "politics", "policy": "politics",
        "logistics": "logistics", "transport": "logistics",
    }
    event_type = event_map.get(et, "other")

    # Sentiment
    s = (raw.get("sentiment") or "neutral").strip().lower()
    if "bull" in s or "hauss" in s:
        sentiment = "bullish"
    elif "bear" in s or "baiss" in s:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    # Risks
    risks = raw.get("risks", [])
    if not isinstance(risks, list):
        risks = []
    risks = [str(r).strip() for r in risks if r][:5]

    return {
        "commodity":  commodity,
        "event_type": event_type,
        "sentiment":  sentiment,
        "analysis":   (raw.get("analysis") or "").strip(),
        "impact":     (raw.get("impact") or "").strip(),
        "risks":      risks,
        "outlook":    (raw.get("outlook") or "").strip(),
    }


def analyze_article(article: dict) -> dict:
    """
    Analyse un article avec le LLM Groq.
    Retourne le dict article enrichi avec les champs LLM.
    """
    # Import Groq ici pour éviter crash si clé manquante
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    except Exception as e:
        console.print(f"[red]✗ Groq non disponible : {e}[/red]")
        return _empty_analysis(article)

    # Prépare le texte
    raw_text = f"{article.get('title', '')} {article.get('text', '')}"
    filtered  = _filter_relevant_text(raw_text)

    if not filtered.strip():
        return _empty_analysis(article)

    prompt = PROMPT_TEMPLATE.format(TEXT=filtered)

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert agricultural commodity analyst. "
                        "Always respond with valid JSON only."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=600,
        )
        output = completion.choices[0].message.content.strip()

        # Nettoie les backticks si présents
        if output.startswith("```"):
            output = output.split("```")[1]
            if output.startswith("json"):
                output = output[4:]

        raw_data = json.loads(output)

    except json.JSONDecodeError:
        # LLM a renvoyé du texte non-JSON — on extrait quand même
        raw_data = {
            "commodity":  "other",
            "event_type": "other",
            "sentiment":  "neutral",
            "analysis":   output if "output" in dir() else "",
            "impact":     "",
            "risks":      [],
            "outlook":    "",
        }
    except Exception as e:
        console.print(f"[yellow]⚠ LLM erreur ({article.get('title', '')[:40]}): {e}[/yellow]")
        return _empty_analysis(article)

    enriched = _normalize(raw_data)
    return {**article, **enriched}


def _empty_analysis(article: dict) -> dict:
    """Retourne l'article avec des champs LLM vides."""
    return {
        **article,
        "commodity":  "other",
        "event_type": "other",
        "sentiment":  "neutral",
        "analysis":   "",
        "impact":     "",
        "risks":      [],
        "outlook":    "",
    }


def analyze_batch(
    articles: list[dict],
    max_articles: int = 30,
    skip_other: bool = True,
) -> list[dict]:
    """
    Analyse un batch d'articles avec le LLM.

    Args:
        articles    : liste d'articles collectés
        max_articles: limite pour ne pas exploser le quota Groq
        skip_other  : si True, ne retraite pas les articles déjà classés "other"

    Returns:
        liste d'articles enrichis
    """
    to_analyze = articles[:max_articles]

    console.print(
        f"\n[bold cyan]🤖 Analyse LLM — {len(to_analyze)} articles[/bold cyan]\n"
    )

    results = []
    for i, article in enumerate(to_analyze):
        title = article.get("title", "")[:50]
        console.print(f"[dim]  ({i+1}/{len(to_analyze)}) {title}...[/dim]")
        enriched = analyze_article(article)
        results.append(enriched)

    # Résumé
    by_commodity = {}
    for a in results:
        c = a.get("commodity", "other")
        by_commodity[c] = by_commodity.get(c, 0) + 1

    console.print("\n[blue]📊 Résultats LLM :[/blue]")
    for c, n in sorted(by_commodity.items(), key=lambda x: -x[1]):
        icon = {"wheat": "🌾", "corn": "🌽", "soy": "🫘"}.get(c, "📰")
        console.print(f"  {icon} {c}: {n} articles")

    return results