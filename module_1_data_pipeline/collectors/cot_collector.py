"""
Collector : CFTC Commitment of Traders Report
Source    : CFTC.gov — gratuit, aucune clé API
Données   : Positions long/short des commercials, non-commercials, speculators
Fréquence : Hebdomadaire (mardi, publié vendredi)
"""

import requests
import pandas as pd
from io import StringIO
from rich.console import Console
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DATA_RAW

console = Console()

# URLs des rapports COT (format CSV historique CFTC)
COT_URLS = {
    2024: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2024.zip",
    2023: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2023.zip",
    2022: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2022.zip",
}

# Noms des commodités dans le rapport CFTC
CFTC_NAMES = {
    "wheat":   "WHEAT-SRW - CHICAGO BOARD OF TRADE",
    "corn":    "CORN - CHICAGO BOARD OF TRADE",
    "soybean": "SOYBEANS - CHICAGO BOARD OF TRADE",
}

# Colonnes clés du COT Report
COT_COLUMNS = [
    "Market_and_Exchange_Names",
    "As_of_Date_In_Form_YYMMDD",
    "NonComm_Positions_Long_All",
    "NonComm_Positions_Short_All",
    "Comm_Positions_Long_All",
    "Comm_Positions_Short_All",
    "NonRept_Positions_Long_All",
    "NonRept_Positions_Short_All",
    "Open_Interest_All",
]

COT_URLS = {
    2024: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2024.zip",
    2023: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2023.zip",
    2022: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2022.zip",
}

def fetch_cot_report(year: int) -> pd.DataFrame:
    import zipfile, io

    url = COT_URLS.get(year)
    try:
        console.print(f"[cyan]⬇ COT Report {year}...[/cyan]")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            candidates = [f for f in z.namelist() if f.endswith(".xls")]
            if not candidates:
                console.print(f"[red]✗ Aucun fichier .xls dans le ZIP {year}[/red]")
                return pd.DataFrame()

            with z.open(candidates[0]) as f:
                xls_bytes = io.BytesIO(f.read())
                df = pd.read_excel(xls_bytes, engine="xlrd")

        available_cols = [c for c in COT_COLUMNS if c in df.columns]
        df = df[available_cols].copy()
        console.print(f"[green]✓ {len(df)} entrées COT pour {year}[/green]")
        return df

    except Exception as e:
        console.print(f"[red]✗ Erreur COT {year}: {e}[/red]")
        return pd.DataFrame()


def filter_agri_cot(df: pd.DataFrame) -> pd.DataFrame:
    """Filtre le COT sur nos commodités agricoles uniquement"""
    mask = df["Market_and_Exchange_Names"].str.contains(
        "WHEAT|CORN|SOYBEANS", na=False, case=False
    )
    return df[mask].copy()


def compute_net_positions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les positions nettes et le Net Speculative Length (NSL).
    NSL = NonComm_Long - NonComm_Short → sentiment spéculatif
    """
    df = df.copy()
    df["net_speculative"] = (
        df["NonComm_Positions_Long_All"] - df["NonComm_Positions_Short_All"]
    )
    df["net_commercial"] = (
        df["Comm_Positions_Long_All"] - df["Comm_Positions_Short_All"]
    )
    df["spec_ratio"] = (
        df["NonComm_Positions_Long_All"] /
        (df["NonComm_Positions_Long_All"] + df["NonComm_Positions_Short_All"] + 1e-6)
    )
    return df


def fetch_all_cot(years: list = [2022, 2023, 2024], save: bool = True) -> pd.DataFrame:
    """Fetch et concatene les COT reports sur plusieurs années"""
    all_dfs = []

    for year in years:
        df = fetch_cot_report(year)
        if not df.empty:
            df = filter_agri_cot(df)
            df = compute_net_positions(df)
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    final = pd.concat(all_dfs, ignore_index=True)

    if save:
        path = DATA_RAW / "cot_agricultural.csv"
        final.to_csv(path, index=False)
        console.print(f"[blue]💾 Sauvegardé : {path}[/blue]")

    console.print(f"[bold green]✅ COT complet — {len(final)} entrées totales[/bold green]")
    return final


if __name__ == "__main__":
    fetch_all_cot(save=True)