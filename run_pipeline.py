"""
AgroTrade Platform — Master Pipeline
Lance tous les collectors + nettoyage automatique des anciens fichiers.
"""

from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys, time, glob, os
sys.path.insert(0, str(Path(__file__).parent))

from module_1_data_pipeline.collectors.cbot_collector    import fetch_all_commodities
from module_1_data_pipeline.collectors.usda_collector    import fetch_all_usda
from module_1_data_pipeline.collectors.weather_collector import fetch_all_weather
from module_1_data_pipeline.collectors.cot_collector     import fetch_all_cot
from module_1_data_pipeline.collectors.ndvi_collector    import fetch_all_ndvi

console = Console()


# ══════════════════════════════════════════════════════════════════════════════
# NETTOYAGE AUTOMATIQUE
# ══════════════════════════════════════════════════════════════════════════════

def cleanup_old_files():
    """
    Supprime les anciens fichiers générés pour garder le projet léger.
    Règle : garde les N fichiers les plus récents par pattern.
    """
    console.rule("[bold yellow]🧹 Nettoyage automatique[/bold yellow]")

    # pattern → nombre de fichiers à garder
    cleanup_rules = {
        "data/processed/signals_*.csv":           1,  # 1 seul fichier signaux
        "data/processed/trade_ideas_2*.json":     1,  # 1 seul trade ideas
        "data/news/news_*.json":                  3,  # 3 jours de news
        "data/processed/backtest_*_equity.csv":   1,
        "data/processed/backtest_*_trades.csv":   1,
        "data/processed/cot_signals_*.csv":       1,
        "data/processed/weather_signals_*.csv":   1,
    }

    total_deleted  = 0
    total_freed_kb = 0

    for pattern, keep_n in cleanup_rules.items():
        files = sorted(glob.glob(pattern), reverse=True)  # plus récent en premier
        to_delete = files[keep_n:]
        for f in to_delete:
            try:
                size_kb = os.path.getsize(f) / 1024
                os.remove(f)
                total_deleted  += 1
                total_freed_kb += size_kb
                console.print(f"  [dim]🗑️  {f} ({size_kb:.0f} KB)[/dim]")
            except Exception as e:
                console.print(f"  [yellow]⚠ Impossible de supprimer {f}: {e}[/yellow]")

    if total_deleted == 0:
        console.print("  [green]✓ Aucun fichier à nettoyer — projet déjà propre[/green]")
    else:
        console.print(
            f"\n  [green]✅ {total_deleted} fichiers supprimés "
            f"({total_freed_kb:.0f} KB libérés)[/green]"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def run_full_pipeline():
    console.print(
        "\n[bold magenta]🌾 AgroTrade Platform — Data Pipeline[/bold magenta]\n"
    )
    start  = time.time()
    status = {}

    # 1. Prix futures CBOT
    console.rule("[bold cyan]1/5 — Prix Futures CBOT[/bold cyan]")
    try:
        results = fetch_all_commodities(save=True)
        status["CBOT Futures"] = ("✅", len(results), "commodités")
    except Exception as e:
        status["CBOT Futures"] = ("❌", 0, str(e)[:60])

    # 2. USDA / WASDE
    console.rule("[bold cyan]2/5 — USDA PSD Data[/bold cyan]")
    try:
        results = fetch_all_usda(save=True)
        status["USDA PSD"] = ("✅", len(results), "commodités")
    except Exception as e:
        status["USDA PSD"] = ("❌", 0, str(e)[:60])

    # 3. Météo zones agricoles
    console.rule("[bold cyan]3/5 — Weather Zones[/bold cyan]")
    try:
        results = fetch_all_weather(save=True)
        status["Weather"] = ("✅", len(results), "zones")
    except Exception as e:
        status["Weather"] = ("❌", 0, str(e)[:60])

    # 4. COT Report CFTC
    console.rule("[bold cyan]4/5 — COT Report CFTC[/bold cyan]")
    try:
        df = fetch_all_cot(years=[2022, 2023, 2024], save=True)
        status["COT CFTC"] = ("✅", len(df), "entrées")
    except Exception as e:
        status["COT CFTC"] = ("❌", 0, str(e)[:60])

    # 5. NDVI Végétation Satellite
    console.rule("[bold cyan]5/5 — NDVI Végétation Satellite[/bold cyan]")
    try:
        df_ndvi = fetch_all_ndvi(save=True)
        n_zones = len(df_ndvi["zone"].unique()) if not df_ndvi.empty else 0
        status["NDVI Vegetation"] = ("✅", n_zones, "zones")
    except Exception as e:
        status["NDVI Vegetation"] = ("❌", 0, str(e)[:60])

    # ── Nettoyage automatique ─────────────────────────────────────────────────
    cleanup_old_files()

    # ── Rapport final ─────────────────────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    console.print(f"\n[bold]Pipeline terminé en {elapsed}s[/bold]\n")

    table = Table(title="📊 Data Pipeline — Rapport d'État")
    table.add_column("Source",  style="cyan")
    table.add_column("Status",  style="green")
    table.add_column("Volume",  style="yellow")
    table.add_column("Unité",   style="white")

    for source, (st, vol, unit) in status.items():
        table.add_row(source, st, str(vol), unit)

    console.print(table)


if __name__ == "__main__":
    run_full_pipeline()