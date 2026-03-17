"""
News Collector — Module 9
Source : RSS feeds uniquement (fiable, rapide, pas de blocage)
"""

import feedparser
import requests
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path
from rich.console import Console

console = Console()

# Chemin vers le fichier sources
SOURCES_PATH = Path(__file__).parent.parent / "sources_rss.yaml"

# On accepte les articles des 7 derniers jours max
MAX_AGE_DAYS = 7


def load_sources(path: Path = SOURCES_PATH) -> list[dict]:
    """Charge et aplatit toutes les sources RSS du YAML."""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    all_sources = []
    for group_name, group_list in cfg["sources"].items():
        if not group_list:
            continue
        for source in group_list:
            item = dict(source)
            item["group"] = group_name
            all_sources.append(item)

    return all_sources


def parse_date(entry) -> datetime | None:
    """Parse la date d'une entrée RSS en datetime UTC."""
    # feedparser met la date parsée dans published_parsed
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            import time
            ts = time.mktime(entry.published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    # Fallback : updated_parsed
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            import time
            ts = time.mktime(entry.updated_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    return None


def is_recent(pub_date: datetime | None, max_days: int = MAX_AGE_DAYS) -> bool:
    """Vérifie que l'article est récent."""
    if pub_date is None:
        return True  # si pas de date, on garde
    limit = datetime.now(tz=timezone.utc) - timedelta(days=max_days)
    return pub_date >= limit


def fetch_rss_feed(source: dict) -> list[dict]:
    """
    Récupère les articles d'un flux RSS.
    Retourne une liste de dicts normalisés.
    """
    url   = source["url"]
    name  = source["name"]
    group = source.get("group", "grains")
    tags  = source.get("tags", [])
    weight = source.get("weight", 0.7)
    lang  = source.get("language", "en")

    try:
        # feedparser gère le timeout via requests
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; AgroTrade/1.0; "
                "+https://github.com/francois-finance/AgroTrade-Platform)"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

    except Exception as e:
        console.print(f"[yellow]⚠ {name}: {e}[/yellow]")
        return []

    articles = []
    for entry in feed.entries:
        pub_date = parse_date(entry)

        if not is_recent(pub_date):
            continue

        # Texte : on prend summary ou content
        text = ""
        if hasattr(entry, "summary"):
            text = entry.summary or ""
        if not text and hasattr(entry, "content"):
            text = entry.content[0].get("value", "") if entry.content else ""

        # Nettoie le HTML basique du texte RSS
        from html.parser import HTMLParser

        class _Stripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.result = []
            def handle_data(self, d):
                self.result.append(d)
            def get_data(self):
                return " ".join(self.result)

        stripper = _Stripper()
        stripper.feed(text)
        clean_text = stripper.get_data().strip()

        articles.append({
            "source_name":  name,
            "source_group": group,
            "source_tags":  tags,
            "source_weight": weight,
            "language":     lang,
            "url":          getattr(entry, "link", url),
            "title":        getattr(entry, "title", "").strip(),
            "text":         clean_text,
            "published":    pub_date.isoformat() if pub_date else None,
            "fetched_at":   datetime.now(tz=timezone.utc).isoformat(),
        })

    console.print(
        f"[green]✓ {name}[/green] — {len(articles)} articles récents"
    )
    return articles


def collect_all_news(
    sources_path: Path = SOURCES_PATH,
    groups: list[str] | None = None,
    max_per_source: int = 10,
) -> list[dict]:
    """
    Collecte les news de toutes les sources RSS.

    Args:
        sources_path : chemin vers le YAML
        groups       : liste de groupes à inclure (None = tous)
                       ex: ["grains", "macro", "shipping", "geopolitics"]
        max_per_source : nombre max d'articles par source

    Returns:
        liste de dicts articles normalisés
    """
    sources = load_sources(sources_path)

    # Filtre par groupe si demandé
    if groups:
        sources = [s for s in sources if s.get("group") in groups]

    console.print(
        f"\n[bold cyan]📡 Collecte RSS — {len(sources)} sources[/bold cyan]\n"
    )

    all_articles = []
    for source in sources:
        articles = fetch_rss_feed(source)
        # Limite par source
        all_articles.extend(articles[:max_per_source])

    # Déduplique par URL
    seen_urls = set()
    unique = []
    for a in all_articles:
        if a["url"] not in seen_urls:
            seen_urls.add(a["url"])
            unique.append(a)

    console.print(
        f"\n[blue]📊 Total : {len(unique)} articles uniques collectés[/blue]"
    )
    return unique


if __name__ == "__main__":
    articles = collect_all_news()
    for a in articles[:3]:
        print(f"\n[{a['source_group']}] {a['title'][:80]}")
        print(f"  → {a['url']}")