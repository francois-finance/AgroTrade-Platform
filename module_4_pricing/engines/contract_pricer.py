"""
Engine : Pricing complet d'un contrat physique grain
C'est l'assemblage final — M1 + M2 + M3 + M4 ensemble.

Un contrat physique céréalier se price ainsi :
PRIX = Futures CBOT (référence papier)
     + Basis (conditions locales)
     + Fret (FOB → CIF si livraison internationale)
     + Prime qualité (protéine, humidité, impuretés)
     + Coût de financement
     + Marge trader
"""

import pandas as pd
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW, DATA_PROCESSED, TRADE_ROUTES

from module_4_pricing.engines.basis_engine import compute_basis
from module_4_pricing.engines.carry_engine import compute_full_carry

console = Console()

# Primes/décotes qualité par commodité
QUALITY_PREMIUMS = {
    "wheat": {
        "protein_premium_per_pct_above_11": 4.0,    # cents/bu par % protéine au-dessus de 11%
        "moisture_discount_per_pct_above_14": -3.0, # cents/bu par % humidité au-dessus de 14%
        "test_weight_premium_60lb": 0.0,             # Base 60 lbs/bu
        "test_weight_discount_below_57lb": -8.0,     # cents/bu si poids spécifique < 57 lbs
    },
    "corn": {
        "moisture_discount_per_pct_above_15": -4.0,
        "test_weight_premium_56lb": 0.0,
    },
    "soybean": {
        "protein_premium_per_pct_above_34": 5.0,
        "oil_premium_per_pct_above_18": 8.0,
        "moisture_discount_per_pct_above_13": -5.0,
    },
}


def price_physical_contract(
    commodity: str,
    origin_location: str,
    destination: str = None,          # Si livraison CIF
    delivery_months_forward: int = 3,
    quantity_mt: float = 25000,       # Taille cargo standard (25k MT)
    quality_specs: dict = None,       # Specs qualité
    freight_route: str = None,        # Si calcul FOB→CIF
    trader_margin_usd_mt: float = 3.0,
    interest_rate: float = 0.055,
    bdi_current: float = 1800.0,
) -> dict:
    """
    Price un contrat physique complet.
    Retourne le prix FOB, le prix CIF si applicable, et la décomposition complète.
    """

    # ── 1. Prix futures de base ──────────────────────────────────────────
    path = DATA_RAW / f"{commodity}_futures.csv"
    if path.exists():
        df = pd.read_csv(path, index_col="date", parse_dates=True)
        futures_spot = float(df["close"].dropna().iloc[-1])
    else:
        futures_spot = {"wheat": 611, "corn": 447, "soybean": 1185}.get(commodity, 500)

    # ── 2. Prix forward (contrat à terme) ────────────────────────────────
    carry = compute_full_carry(commodity, futures_spot, delivery_months_forward, interest_rate)
    futures_forward = carry["theoretical_forward"]
    carry_cost = carry["carry_cost_total"]

    # ── 3. Basis local ───────────────────────────────────────────────────
    basis_result = compute_basis(commodity, origin_location)
    basis_value   = basis_result["actual_basis"]

    # Prix cash local (cents/boisseau)
    cash_price_cents_bu = futures_forward + basis_value

    # Conversion en $/tonne métrique
    # Blé/Maïs : 1 tonne = 36.744 boisseaux / Soja : 1 tonne = 36.744 bu
    bu_per_mt = 36.744
    cash_price_usd_mt = (cash_price_cents_bu / 100) * bu_per_mt

    # ── 4. Primes qualité ────────────────────────────────────────────────
    quality_premium_cents_bu = 0.0
    quality_details = {}

    if quality_specs and commodity in QUALITY_PREMIUMS:
        prems = QUALITY_PREMIUMS[commodity]
        if commodity == "wheat":
            protein = quality_specs.get("protein_pct", 11.0)
            if protein > 11:
                prem = (protein - 11) * prems["protein_premium_per_pct_above_11"]
                quality_premium_cents_bu += prem
                quality_details["protein_premium"] = f"+{prem:.1f}c ({protein}% protein)"

            moisture = quality_specs.get("moisture_pct", 14.0)
            if moisture > 14:
                disc = (moisture - 14) * prems["moisture_discount_per_pct_above_14"]
                quality_premium_cents_bu += disc
                quality_details["moisture_discount"] = f"{disc:.1f}c ({moisture}% moisture)"

        elif commodity == "soybean":
            oil = quality_specs.get("oil_pct", 18.0)
            if oil > 18:
                prem = (oil - 18) * prems["oil_premium_per_pct_above_18"]
                quality_premium_cents_bu += prem
                quality_details["oil_premium"] = f"+{prem:.1f}c ({oil}% oil)"

    quality_premium_usd_mt = (quality_premium_cents_bu / 100) * bu_per_mt

    # ── 5. Prix FOB ──────────────────────────────────────────────────────
    fob_usd_mt = cash_price_usd_mt + quality_premium_usd_mt + trader_margin_usd_mt

    # ── 6. Prix CIF (si route de fret fournie) ───────────────────────────
    cif_usd_mt = None
    freight_usd_mt = None

    if freight_route:
        try:
            from module_2_freight.calculators.freight_calculator import estimate_freight_cost
            freight = estimate_freight_cost(
                route_key=freight_route,
                fob_price_per_ton=fob_usd_mt,
                quantity_tons=quantity_mt,
                bdi_current=bdi_current,
            )
            freight_usd_mt = freight["freight_per_ton"]
            cif_usd_mt = freight["cif_per_ton"]
        except Exception as e:
            console.print(f"[yellow]⚠ Calcul fret impossible : {e}[/yellow]")

    # ── 7. Assemblage résultat ───────────────────────────────────────────
    result = {
        "commodity":                commodity,
        "origin":                   origin_location,
        "destination":              destination or "FOB seulement",
        "quantity_mt":              quantity_mt,
        "delivery_months_forward":  delivery_months_forward,

        # Décomposition prix
        "futures_spot_cents_bu":    round(futures_spot, 2),
        "futures_forward_cents_bu": round(futures_forward, 2),
        "carry_cost_cents_bu":      round(carry_cost, 2),
        "basis_cents_bu":           round(basis_value, 2),
        "cash_price_cents_bu":      round(cash_price_cents_bu, 2),
        "quality_premium_cents_bu": round(quality_premium_cents_bu, 2),
        "quality_details":          quality_details,

        # Prix finaux
        "cash_price_usd_mt":        round(cash_price_usd_mt, 2),
        "quality_premium_usd_mt":   round(quality_premium_usd_mt, 2),
        "trader_margin_usd_mt":     round(trader_margin_usd_mt, 2),
        "fob_price_usd_mt":         round(fob_usd_mt, 2),
        "freight_usd_mt":           round(freight_usd_mt, 2) if freight_usd_mt else None,
        "cif_price_usd_mt":         round(cif_usd_mt, 2) if cif_usd_mt else None,

        # Valeur totale cargo
        "total_cargo_value_fob":    round(fob_usd_mt * quantity_mt, 0),
        "total_cargo_value_cif":    round(cif_usd_mt * quantity_mt, 0) if cif_usd_mt else None,
    }

    return result


def print_contract_summary(result: dict):
    """Affiche le détail complet d'un contrat pricé"""
    title = f"📋 Contrat : {result['commodity'].upper()} | {result['origin']} → {result['destination']}"
    table = Table(title=title, show_lines=False)
    table.add_column("Composante",          style="cyan",        width=35)
    table.add_column("cents/bu",            style="white",       width=14)
    table.add_column("$/MT",                style="bold yellow", width=14)

    def bu_to_mt(cents_bu):
        return round((cents_bu / 100) * 36.744, 2)

    rows = [
        ("Futures Spot (M0)",                f"{result['futures_spot_cents_bu']:.1f}",    f"${bu_to_mt(result['futures_spot_cents_bu']):.2f}"),
        ("+ Carry ({} mois)".format(result['delivery_months_forward']), f"+{result['carry_cost_cents_bu']:.1f}", f"+${bu_to_mt(result['carry_cost_cents_bu']):.2f}"),
        ("= Futures Forward",                f"{result['futures_forward_cents_bu']:.1f}", f"${bu_to_mt(result['futures_forward_cents_bu']):.2f}"),
        ("+ Basis local",                    f"{result['basis_cents_bu']:+.1f}",          f"${bu_to_mt(result['basis_cents_bu']):+.2f}"),
        ("+ Prime qualité",                  f"{result['quality_premium_cents_bu']:+.1f}",f"${result['quality_premium_usd_mt']:+.2f}"),
        ("+ Marge trader",                   "—",                                          f"+${result['trader_margin_usd_mt']:.2f}"),
        ("━" * 28,                           "━" * 10,                                     "━" * 10),
        ("= PRIX FOB",                       "—",                                          f"[bold]${result['fob_price_usd_mt']:.2f}[/bold]"),
    ]

    if result.get("freight_usd_mt"):
        rows.append(("+ Fret maritime",      "—", f"+${result['freight_usd_mt']:.2f}"))
        rows.append(("= PRIX CIF",           "—", f"[bold green]${result['cif_price_usd_mt']:.2f}[/bold green]"))

    for name, bu_val, mt_val in rows:
        table.add_row(name, bu_val, mt_val)

    console.print(table)

    # Valeur totale cargo
    qty = result["quantity_mt"]
    console.print(f"\n  📦 Cargo : {qty:,.0f} MT")
    console.print(f"  💰 Valeur FOB totale : ${result['total_cargo_value_fob']:,.0f}")
    if result.get("total_cargo_value_cif"):
        console.print(f"  💰 Valeur CIF totale : ${result['total_cargo_value_cif']:,.0f}\n")