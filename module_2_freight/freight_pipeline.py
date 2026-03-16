"""
AgroTrade Platform — Module 2 : Freight Pipeline Master
"""

from rich.console import Console
from rich.table import Table
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_2_freight.collectors.baltic_collector       import fetch_all_baltic
from module_2_freight.calculators.freight_calculator    import estimate_freight_cost, print_freight_summary
from module_2_freight.calculators.arbitrage_calculator  import run_full_arbitrage_analysis

console = Console()

def run_freight_pipeline():
    console.print("\n[bold magenta]🚢 AgroTrade — Module 2 : Freight & Transport[/bold magenta]\n")
    status = {}

    # 1. Baltic Indices
    console.rule("[bold cyan]1/3 — Baltic Indices[/bold cyan]")
    try:
        baltic = fetch_all_baltic(save=True)
        # Récupère le BDI le plus récent
        bdi_current = 1800.0  # fallback
        if "BDI" in baltic and not baltic["BDI"].empty:
            bdi_current = float(baltic["BDI"].sort_values("date").iloc[-1]["close"])
            console.print(f"[bold]📊 BDI actuel : {bdi_current:.0f} points[/bold]")
        status["Baltic Indices"] = ("✅", len(baltic), "indices")
    except Exception as e:
        status["Baltic Indices"] = ("❌", 0, str(e))
        bdi_current = 1800.0

    # 2. Exemple calcul FOB→CIF
    console.rule("[bold cyan]2/3 — Exemple Calcul FOB→CIF[/bold cyan]")
    try:
        result = estimate_freight_cost(
            route_key="usgulf_egypt",
            fob_price_per_ton=220.0,
            bdi_current=bdi_current
        )
        print_freight_summary(result)
        status["Freight Calculator"] = ("✅", 1, "route calculée")
    except Exception as e:
        status["Freight Calculator"] = ("❌", 0, str(e))

    # 3. Analyse d'arbitrage
    console.rule("[bold cyan]3/3 — Arbitrage Inter-Origines[/bold cyan]")
    try:
        arb_results = run_full_arbitrage_analysis(bdi=bdi_current, save=True)
        status["Arbitrage Analysis"] = ("✅", len(arb_results), "analyses")
    except Exception as e:
        status["Arbitrage Analysis"] = ("❌", 0, str(e))

    # Rapport
    console.print()
    table = Table(title="📊 Module 2 — Rapport d'État")
    table.add_column("Composant",  style="cyan")
    table.add_column("Status",     style="green")
    table.add_column("Volume",     style="yellow")
    table.add_column("Détail",     style="white")
    for comp, (st, vol, detail) in status.items():
        table.add_row(comp, st, str(vol), detail)
    console.print(table)

if __name__ == "__main__":
    run_freight_pipeline()