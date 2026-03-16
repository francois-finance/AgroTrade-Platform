"""
AgroTrade Platform — Module 1 : Data Pipeline Master
Lance tous les collectors en séquence et génère un rapport d'état.
"""

from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys, time

sys.path.insert(0, str(Path(__file__).parent))

from module_1_data_pipeline.collectors.cbot_collector   import fetch_all_commodities
from module_1_data_pipeline.collectors.usda_collector   import fetch_all_usda
from module_1_data_pipeline.collectors.weather_collector import fetch_all_weather
from module_1_data_pipeline.collectors.cot_collector    import fetch_all_cot

console = Console()

def run_full_pipeline():
    console.print("\n[bold magenta]🌾 AgroTrade Platform — Data Pipeline démarrage...[/bold magenta]\n")
    start = time.time()
    status = {}

    # 1. Prix futures CBOT
    console.rule("[bold cyan]1/4 — Prix Futures CBOT[/bold cyan]")
    try:
        results = fetch_all_commodities(save=True)
        status["CBOT Futures"] = ("✅", len(results), "commodités")
    except Exception as e:
        status["CBOT Futures"] = ("❌", 0, str(e))

    # 2. USDA / WASDE
    console.rule("[bold cyan]2/4 — USDA PSD Data[/bold cyan]")
    try:
        results = fetch_all_usda(save=True)
        status["USDA PSD"] = ("✅", len(results), "commodités")
    except Exception as e:
        status["USDA PSD"] = ("❌", 0, str(e))

    # 3. Météo zones agricoles
    console.rule("[bold cyan]3/4 — Weather Zones[/bold cyan]")
    try:
        results = fetch_all_weather(save=True)
        status["Weather"] = ("✅", len(results), "zones")
    except Exception as e:
        status["Weather"] = ("❌", 0, str(e))

    # 4. COT Report CFTC
    console.rule("[bold cyan]4/4 — COT Report CFTC[/bold cyan]")
    try:
        df = fetch_all_cot(years=[2022, 2023, 2024], save=True)
        status["COT CFTC"] = ("✅", len(df), "entrées")
    except Exception as e:
        status["COT CFTC"] = ("❌", 0, str(e))

    # Rapport final
    elapsed = round(time.time() - start, 1)
    console.print(f"\n[bold]Pipeline terminé en {elapsed}s[/bold]\n")

    table = Table(title="📊 Data Pipeline — Rapport d'État")
    table.add_column("Source",   style="cyan")
    table.add_column("Status",   style="green")
    table.add_column("Volume",   style="yellow")
    table.add_column("Unité",    style="white")

    for source, (st, vol, unit) in status.items():
        table.add_row(source, st, str(vol), unit)

    console.print(table)

# Dans run_pipeline.py, après les 4 collectors existants
from module_1_data_pipeline.collectors.ndvi_collector import fetch_all_ndvi

# Dans run_full_pipeline() :
console.rule("[bold cyan]5/5 — NDVI Végétation Satellite[/bold cyan]")
try:
    df_ndvi = fetch_all_ndvi(save=True)
    status["NDVI Vegetation"] = ("✅", len(df_ndvi["zone"].unique()) if not df_ndvi.empty else 0, "zones")
except Exception as e:
    status["NDVI Vegetation"] = ("❌", 0, str(e))
    

if __name__ == "__main__":
    run_full_pipeline()