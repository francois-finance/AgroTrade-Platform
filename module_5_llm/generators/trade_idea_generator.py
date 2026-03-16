"""
Generator : Appel à l'API Claude pour générer les trade ideas
"""
import json
import re
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import ANTHROPIC_API_KEY, GROQ_API_KEY, LLM_MODEL, LLM_PROVIDER, DATA_PROCESSED

from module_5_llm.aggregator.context_builder import build_full_context, context_to_text
from module_5_llm.prompts.trade_idea_prompt  import SYSTEM_PROMPT, TRADE_IDEA_PROMPT, DAILY_REPORT_PROMPT

console = Console()



def call_claude(system: str, user: str, max_tokens: int = 3000) -> str:
    """
    Appel LLM unifié — supporte Groq (gratuit) et Anthropic.
    Groq utilise une API compatible OpenAI, très simple à intégrer.
    """
    provider = LLM_PROVIDER

    if provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY manquante dans .env — "
                             "Inscription gratuite sur console.groq.com")
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.3,   # Bas pour des réponses plus déterministes / JSON propre
        )
        return response.choices[0].message.content

    elif provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY manquante dans .env")
        import anthropic as anth
        client = anth.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        return message.content[0].text

    else:
        raise ValueError(f"Provider inconnu : {provider}. Utilise 'groq' ou 'anthropic'.")


def parse_json_response(raw: str) -> dict:
    """Parse la réponse JSON du LLM avec nettoyage"""
    # Nettoie les éventuels backticks markdown
    clean = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ JSON parse error: {e}[/red]")
        console.print(f"[dim]Raw response: {raw[:500]}...[/dim]")
        raise


def generate_trade_ideas(save: bool = True) -> dict:
    """
    Génère 3 trade ideas via Claude en utilisant tout le contexte M1-M4.
    """
    console.print("\n[bold cyan]🤖 Génération des trade ideas via Claude...[/bold cyan]")

    # Construit le contexte
    context = build_full_context()
    context_text = context_to_text(context)

    # Prépare le prompt
    prompt = TRADE_IDEA_PROMPT.format(
        market_context=context_text,
        timestamp=context["timestamp"]
    )

    console.print("[dim]Appel API Claude...[/dim]")
    raw_response = call_claude(SYSTEM_PROMPT, prompt, max_tokens=4000)

    result = parse_json_response(raw_response)

    if save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        path = DATA_PROCESSED / f"trade_ideas_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

        # Sauvegarde aussi comme "latest"
        latest_path = DATA_PROCESSED / "trade_ideas_latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result


def generate_daily_report(save: bool = True) -> dict:
    """Génère le rapport de marché quotidien"""
    console.print("\n[bold cyan]📰 Génération du rapport quotidien...[/bold cyan]")

    context = build_full_context()
    context_text = context_to_text(context)

    prompt = DAILY_REPORT_PROMPT.format(
        market_context=context_text,
        timestamp=context["timestamp"]
    )

    raw_response = call_claude(SYSTEM_PROMPT, prompt, max_tokens=2000)
    result = parse_json_response(raw_response)

    if save:
        timestamp = datetime.now().strftime("%Y%m%d")
        path = DATA_PROCESSED / f"daily_report_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        latest_path = DATA_PROCESSED / "daily_report_latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        console.print(f"[blue]💾 Rapport sauvegardé[/blue]")

    return result


def print_trade_ideas(result: dict):
    """Affiche les trade ideas de façon professionnelle"""

    # Résumé marché
    console.print(Panel(
        f"[bold]{result.get('market_summary', '')}[/bold]",
        title="📊 Market Summary",
        border_style="cyan"
    ))

    # Biais journalier
    bias = result.get("daily_bias", {})
    bias_table = Table(title="🧭 Daily Bias", show_header=True)
    bias_table.add_column("Commodité", style="cyan",  width=12)
    bias_table.add_column("Biais",     style="bold",  width=12)

    bias_colors = {"bullish": "green", "bearish": "red", "neutral": "yellow"}
    for commodity, b in bias.items():
        color = bias_colors.get(b, "white")
        icon  = "▲" if b == "bullish" else ("▼" if b == "bearish" else "—")
        bias_table.add_row(commodity.upper(), f"[{color}]{icon} {b.upper()}[/{color}]")
    console.print(bias_table)

    # Key risk
    if result.get("key_risk_today"):
        console.print(Panel(
            f"[bold red]{result['key_risk_today']}[/bold red]",
            title="⚠️  Key Risk Today",
            border_style="red"
        ))

    # Trade Ideas
    for idea in result.get("trade_ideas", []):
        direction_color = "green" if "long" in idea.get("direction","") else "red"
        conviction_color = {"high": "green", "medium": "yellow", "low": "dim"}.get(
            idea.get("conviction","medium"), "white"
        )

        title = (f"[bold]#{idea['id']} — {idea['title']}[/bold]\n"
                 f"[{direction_color}]{idea['direction'].upper()}[/{direction_color}] "
                 f"{idea['commodity'].upper()} | "
                 f"[{conviction_color}]Conviction: {idea.get('conviction','?').upper()}[/{conviction_color}] | "
                 f"Timeframe: {idea.get('timeframe','?')}")

        rationale = idea.get("rationale", {})
        execution = idea.get("execution", {})
        monitoring = idea.get("monitoring", {})

        body = []
        body.append("[bold yellow]📌 RATIONALE[/bold yellow]")
        body.append(f"  Primary  : {rationale.get('primary_catalyst','')}")
        body.append(f"  Secondary: {rationale.get('secondary_catalyst','')}")
        body.append(f"  Technical: {rationale.get('technical_setup','')}")
        body.append(f"  Fundamental: {rationale.get('fundamental_driver','')}")
        if rationale.get("freight_angle"):
            body.append(f"  Freight  : {rationale.get('freight_angle','')}")

        body.append("\n[bold yellow]⚡ EXECUTION[/bold yellow]")
        body.append(f"  Entry    : {execution.get('entry_level','')} → {execution.get('entry_trigger','')}")
        body.append(f"  Stop     : {execution.get('stop_loss','')}")
        body.append(f"  Target 1 : {execution.get('target_1','')}")
        if execution.get("target_2"):
            body.append(f"  Target 2 : {execution.get('target_2','')}")
        body.append(f"  R/R      : {execution.get('risk_reward','')}")
        body.append(f"  Size     : {execution.get('position_size','')}")

        body.append("\n[bold yellow]⚠️  RISKS[/bold yellow]")
        for risk in idea.get("risk_factors", []):
            body.append(f"  • {risk}")

        body.append("\n[bold yellow]👁️  MONITORING[/bold yellow]")
        body.append(f"  Dates      : {monitoring.get('key_dates','')}")
        body.append(f"  Levels     : {monitoring.get('key_levels','')}")
        body.append(f"  Invalide si: {monitoring.get('invalidation','')}")

        console.print(Panel(
            "\n".join(body),
            title=title,
            border_style=direction_color,
            padding=(1, 2)
        ))


def print_daily_report(report: dict):
    """Affiche le rapport quotidien"""
    console.print(Panel(
        f"[bold white]{report.get('headline','')}[/bold white]\n\n"
        f"{report.get('executive_summary','')}",
        title=f"📰 Daily Report — {report.get('date','')}",
        border_style="magenta"
    ))

    # Vues par commodité
    views = report.get("commodity_views", {})
    table = Table(title="📊 Commodity Views")
    table.add_column("Commodité",   style="cyan",   width=12)
    table.add_column("Vue",         style="bold",   width=10)
    table.add_column("Driver",      style="white",  width=40)
    table.add_column("Range semaine",style="yellow",width=20)
    table.add_column("Niveau clé",  style="dim",    width=15)

    for c, v in views.items():
        view  = v.get("view","neutral")
        color = "green" if view == "bullish" else ("red" if view == "bearish" else "yellow")
        table.add_row(
            c.upper(),
            f"[{color}]{view.upper()}[/{color}]",
            v.get("key_driver",""),
            v.get("price_range_week",""),
            v.get("watch_level",""),
        )
    console.print(table)

    # Marché physique
    phys = report.get("physical_market", {})
    if phys:
        console.print(Panel(
            f"Blé   : {phys.get('best_origin_wheat','')}\n"
            f"Maïs  : {phys.get('best_origin_corn','')}\n"
            f"Soja  : {phys.get('best_origin_soy','')}\n"
            f"Freight: {phys.get('freight_outlook','')}",
            title="🚢 Physical Market",
            border_style="blue"
        ))

    # Quote
    if report.get("quote_of_day"):
        console.print(Panel(
            f"[italic]\"{report['quote_of_day']}\"[/italic]",
            title="💬 Quote of the Day",
            border_style="dim"
        ))