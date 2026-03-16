"""
AgroTrade Platform — Module 3 : Market Signals Pipeline
"""

from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_3_signals.signals.signal_engine import run_signal_engine, print_signal_dashboard

console = Console()

def run_signals_pipeline():
    console.print("\n[bold magenta]📊 AgroTrade — Module 3 : Market Signals[/bold magenta]\n")

    results = run_signal_engine(save=True)
    print_signal_dashboard(results)

    console.print("\n[bold]📖 Lecture du dashboard :[/bold]")
    console.print("  Score composite : de -1 (très bearish) à +1 (très bullish)")
    console.print("  Conviction      : % de certitude du signal")
    console.print("  Sources         : Momentum + COT + Météo + BDI + RSI + Bollinger\n")

if __name__ == "__main__":
    run_signals_pipeline()