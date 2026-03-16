"""
AgroTrade Platform — Module 4 : Pricing Engine Pipeline
"""

from rich.console import Console
from rich.table import Table
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_4_pricing.engines.basis_engine    import run_basis_analysis
from module_4_pricing.engines.crush_engine    import compute_crush_margin, compute_historical_crush, print_crush_summary
from module_4_pricing.engines.carry_engine    import run_carry_analysis
from module_4_pricing.engines.contract_pricer import price_physical_contract, print_contract_summary

console = Console()

def run_pricing_pipeline():
    console.print("\n[bold magenta]🧮 AgroTrade — Module 4 : Pricing Engine[/bold magenta]\n")
    status = {}

    # ── 1. Basis Analysis ────────────────────────────────────────────────
    console.rule("[bold cyan]1/4 — Basis Physique vs Futures[/bold cyan]")
    try:
        basis_df = run_basis_analysis(save=True)
        status["Basis Engine"] = ("✅", len(basis_df), "localisations")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["Basis Engine"] = ("❌", 0, str(e))

    # ── 2. Crush Margin ──────────────────────────────────────────────────
    console.rule("[bold cyan]2/4 — Soybean Crush Margin[/bold cyan]")
    try:
        from config import DATA_RAW
        import pandas as pd
        prices = {}
        for c in ["soybean", "soyoil", "soymeal"]:
            p = DATA_RAW / f"{c}_futures.csv"
            if p.exists():
                prices[c] = float(pd.read_csv(p, index_col="date").iloc[-1]["close"])

        crush = compute_crush_margin(
            soybean_price=prices.get("soybean", 1185),
            soyoil_price=prices.get("soyoil", 45),
            soymeal_price=prices.get("soymeal", 350),
        )
        print_crush_summary(crush)
        hist = compute_historical_crush(save=True)
        status["Crush Engine"] = ("✅", len(hist), "jours historique")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["Crush Engine"] = ("❌", 0, str(e))

    # ── 3. Carry & Forward Curve ─────────────────────────────────────────
    console.rule("[bold cyan]3/4 — Carry & Structure de Marché[/bold cyan]")
    try:
        carry_results = run_carry_analysis(save=True)
        status["Carry Engine"] = ("✅", len(carry_results), "commodités")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["Carry Engine"] = ("❌", 0, str(e))

    # ── 4. Contrat physique complet ──────────────────────────────────────
    console.rule("[bold cyan]4/4 — Pricing Contrat Physique[/bold cyan]")
    try:
        contracts = [
            {
                "label":    "Blé US Gulf → Égypte CIF",
                "params":   {
                    "commodity":               "wheat",
                    "origin_location":          "us_gulf_export",
                    "destination":              "Égypte (Damietta)",
                    "delivery_months_forward":  3,
                    "quantity_mt":              50000,
                    "freight_route":            "usgulf_egypt",
                    "quality_specs":            {"protein_pct": 12.5, "moisture_pct": 13.5},
                    "trader_margin_usd_mt":     3.5,
                }
            },
            {
                "label":    "Soja Brésil → Chine CIF",
                "params":   {
                    "commodity":               "soybean",
                    "origin_location":          "brazil_paranagua_fob",
                    "destination":              "Shanghai (Chine)",
                    "delivery_months_forward":  2,
                    "quantity_mt":              60000,
                    "freight_route":            "brazil_china_soy",
                    "quality_specs":            {"oil_pct": 19.5},
                    "trader_margin_usd_mt":     4.0,
                }
            },
        ]

        for contract in contracts:
            console.print(f"\n[bold]📋 {contract['label']}[/bold]")
            result = price_physical_contract(**contract["params"])
            print_contract_summary(result)

        status["Contract Pricer"] = ("✅", len(contracts), "contrats pricés")
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        status["Contract Pricer"] = ("❌", 0, str(e))

    # ── Rapport final ────────────────────────────────────────────────────
    console.print()
    table = Table(title="📊 Module 4 — Rapport d'État")
    table.add_column("Composant", style="cyan")
    table.add_column("Status",    style="green")
    table.add_column("Volume",    style="yellow")
    table.add_column("Détail",    style="white")
    for comp, (st, vol, detail) in status.items():
        table.add_row(comp, st, str(vol), detail)
    console.print(table)


if __name__ == "__main__":
    run_pricing_pipeline()