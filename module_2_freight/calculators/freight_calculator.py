"""
Calculator : Coût de transport FOB → CIF
Formule    : CIF = FOB + Fret + Assurance + Surestaries (optionnel)
Données    : BDI actuel + distances maritimes estimées
"""

import pandas as pd
import math
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import MAJOR_PORTS, TRADE_ROUTES, VESSEL_CAPACITY, DATA_RAW

console = Console()


def haversine_distance_nm(lat1, lon1, lat2, lon2) -> float:
    """
    Calcule la distance orthodromique entre deux ports en milles nautiques.
    Approximation — pour les routes réelles il faudrait tenir compte des détroits.
    """
    R = 3440.07  # Rayon de la Terre en milles nautiques
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


# Corrections pour les routes qui passent par des détroits/canaux
# (la distance haversine est une droite — pas réaliste pour certaines routes)
ROUTE_DISTANCE_CORRECTIONS = {
    "usgulf_japan":      1.20,  # +20% via Panama Canal
    "usgulf_egypt":      1.05,  # +5% via Atlantique
    "brazil_china":      1.15,  # +15% via Cap de Bonne Espérance ou Panama
    "usgulf_china_soy":  1.20,  # +20% via Panama Canal
    "usgulf_ara":        1.05,
    "argentina_ara":     1.10,  # +10% via détroit de Magellan ou canal
    "australia_indo":    1.05,
    "blacksea_egypt":    1.30,  # +30% via Bosphore + Méditerranée
    "blacksea_turkey":   1.10,
    "argentina_china":   1.15,
}

def estimate_freight_cost(
    route_key: str,
    fob_price_per_ton: float,
    quantity_tons: float = None,
    bdi_current: float = 1800.0,
    insurance_rate: float = 0.001,   # 0.1% de la valeur CIF
    other_costs_per_ton: float = 2.0  # Port dues, inspection, etc.
) -> dict:
    """
    Calcule le coût CIF complet pour une route donnée.

    Args:
        route_key        : Clé de TRADE_ROUTES (ex: 'usgulf_egypt')
        fob_price_per_ton: Prix FOB en $/tonne
        quantity_tons    : Quantité en tonnes (si None, utilise capacité standard du navire)
        bdi_current      : Valeur actuelle du BDI
        insurance_rate   : Taux d'assurance sur valeur CIF
        other_costs_per_ton: Frais annexes

    Returns:
        Dict avec détail complet du coût CIF
    """
    if route_key not in TRADE_ROUTES:
        raise ValueError(f"Route '{route_key}' inconnue. Routes dispo : {list(TRADE_ROUTES.keys())}")

    route = TRADE_ROUTES[route_key]
    origin = MAJOR_PORTS[route["from"]]
    destination = MAJOR_PORTS[route["to"]]
    vessel_type = route["vessel"]

    if quantity_tons is None:
        quantity_tons = VESSEL_CAPACITY[vessel_type]

    # 1. Distance en milles nautiques
    raw_distance = haversine_distance_nm(
        origin["lat"], origin["lon"],
        destination["lat"], destination["lon"]
    )
    correction = ROUTE_DISTANCE_CORRECTIONS.get(route_key, 1.10)
    distance_nm = raw_distance * correction

    # 2. Durée du voyage (vitesse moyenne 13 nœuds pour Panamax chargé)
    speed_knots = 13.0
    voyage_days = distance_nm / (speed_knots * 24)

    # 3. TCE (Time Charter Equivalent) estimé depuis le BDI
    bdi_multipliers = {"handysize": 4.0, "supramax": 5.0, "panamax": 6.0, "capesize": 9.0}
    tce_per_day = bdi_current * bdi_multipliers.get(vessel_type, 6.0)

    # 4. Coût total du navire pour le voyage
    total_vessel_cost = tce_per_day * voyage_days

    # 5. Fret en $/tonne
    freight_per_ton = total_vessel_cost / quantity_tons

    # 6. Assurance (calculée sur FOB + fret, approximation)
    insurance_per_ton = (fob_price_per_ton + freight_per_ton) * insurance_rate

    # 7. CIF total
    cif_price = fob_price_per_ton + freight_per_ton + insurance_per_ton + other_costs_per_ton

    # 8. Ratio fret/FOB (indicateur de compétitivité)
    freight_to_fob_ratio = (freight_per_ton / fob_price_per_ton) * 100

    return {
        "route":               route_key,
        "from":                origin["name"],
        "to":                  destination["name"],
        "commodity":           route["commodity"],
        "vessel_type":         vessel_type,
        "quantity_tons":       round(quantity_tons, 0),
        "distance_nm":         round(distance_nm, 0),
        "voyage_days":         round(voyage_days, 1),
        "bdi_used":            bdi_current,
        "tce_per_day_usd":     round(tce_per_day, 0),
        "fob_per_ton":         round(fob_price_per_ton, 2),
        "freight_per_ton":     round(freight_per_ton, 2),
        "insurance_per_ton":   round(insurance_per_ton, 2),
        "other_costs_per_ton": round(other_costs_per_ton, 2),
        "cif_per_ton":         round(cif_price, 2),
        "freight_pct_of_fob":  round(freight_to_fob_ratio, 1),
    }


def print_freight_summary(result: dict):
    """Affiche un résumé formaté d'un calcul de fret"""
    table = Table(title=f"🚢 Fret : {result['from']} → {result['to']}")
    table.add_column("Paramètre",  style="cyan",   width=28)
    table.add_column("Valeur",     style="yellow",  width=20)
    table.add_column("Unité",      style="white",   width=15)

    rows = [
        ("Commodité",           result["commodity"],              ""),
        ("Type de navire",      result["vessel_type"],            ""),
        ("Distance",            f"{result['distance_nm']:,}",     "milles nautiques"),
        ("Durée voyage",        f"{result['voyage_days']}",       "jours"),
        ("BDI actuel",          f"{result['bdi_used']:,}",        "points"),
        ("TCE estimé",          f"${result['tce_per_day_usd']:,}","$/jour"),
        ("─" * 20,              "─" * 15,                         "─" * 10),
        ("Prix FOB",            f"${result['fob_per_ton']:.2f}",  "$/tonne"),
        ("Fret maritime",       f"${result['freight_per_ton']:.2f}", "$/tonne"),
        ("Assurance",           f"${result['insurance_per_ton']:.2f}", "$/tonne"),
        ("Frais annexes",       f"${result['other_costs_per_ton']:.2f}", "$/tonne"),
        ("─" * 20,              "─" * 15,                         "─" * 10),
        ("PRIX CIF",            f"${result['cif_per_ton']:.2f}",  "$/tonne"),
        ("Fret / FOB",          f"{result['freight_pct_of_fob']}%", ""),
    ]

    for name, val, unit in rows:
        table.add_row(name, str(val), unit)

    console.print(table)


if __name__ == "__main__":
    # Test : blé du Golfe vers l'Égypte
    result = estimate_freight_cost(
        route_key="usgulf_egypt",
        fob_price_per_ton=220.0,
        bdi_current=1800
    )
    print_freight_summary(result)