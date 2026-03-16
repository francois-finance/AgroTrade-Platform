# AgroTrade Intelligence Platform

> Agricultural Commodities Trading Intelligence — A full-stack trading analytics platform covering physical & paper grain markets, freight logistics, LLM-powered trade ideas, and risk management.

##  What This Project Does

AgroTrade replicates the analytical workflows of a trading desk at a tier-1 commodity house (Cargill, Louis Dreyfus, Viterra level).

Given a question like *"Is Ukrainian wheat competitive vs US Gulf wheat delivered CIF Egypt today?"*, the platform answers automatically by combining live CBOT prices, Baltic freight rates, FOB→CIF calculation, COT positioning, weather stress, and LLM-generated trade ideas.

## Architecture

8 modules covering the full trading value chain:

- Module 1 — Data Pipeline (CBOT, USDA, Weather, COT)
- Module 2 — Freight & Transport (BDI, FOB→CIF, Arbitrage)
- Module 3 — Market Signals (7 sources, composite score)
- Module 4 — Pricing Engine (Basis, Crush, Carry, Contracts)
- Module 5 — LLM Intelligence (Groq/Llama 3.3)
- Module 6 — Backtesting (2018-2025, 5 strategies)
- Module 7 — Risk Dashboard (VaR, CVaR, Stress Tests)
- Module 8 — Streamlit Frontend (Bloomberg-style)

## Quick Start
```bash
git clone https://github.com/francois-finance/AgroTrade-Platform.git
cd AgroTrade-Platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py
python -m streamlit run Home.py
```

## Data Sources

| Source | Data | Cost |
|--------|------|------|
| CME/CBOT via yfinance | Futures OHLCV | Free |
| CFTC.gov | COT positioning | Free |
| Open-Meteo ERA5 | Weather + NDVI proxy | Free |
| Stooq.com | Baltic indices | Free |
| USDA FAS PSD | Supply/demand | Free |
| Groq API (Llama 3.3) | LLM inference | Free |

## Key Concepts

**Stocks-to-Use Ratio** — The #1 fundamental indicator in grain trading. S/U < 12% = critical tightness = very bullish prices.

**Soybean Crush Margin** — Measures crusher profitability. High crush (> 90th percentile) signals strong soybean demand.

**COT Contrarian Signal** — When speculators are extremely long (> 80th percentile over 3 years), historically a bearish signal.

**FOB → CIF Pricing** — CIF = FOB + Freight + Insurance. The platform calculates this for 20+ global routes.

## Author

**François Dubreu** — Portfolio project demonstrating quantitative skills in agricultural commodities trading.
