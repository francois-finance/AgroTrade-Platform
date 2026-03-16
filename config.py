import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Chemins
BASE_DIR = Path(__file__).parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
DATA_CACHE = BASE_DIR / "data" / "cache"

# Commodités suivies
COMMODITIES = {
    "wheat":  {"ticker": "ZW=F", "name": "Blé CBOT",  "unit": "cents/bushel"},
    "corn":   {"ticker": "ZC=F", "name": "Maïs CBOT", "unit": "cents/bushel"},
    "soybean":{"ticker": "ZS=F", "name": "Soja CBOT", "unit": "cents/bushel"},
    "soyoil": {"ticker": "ZL=F", "name": "Huile soja","unit": "cents/lb"},
    "soymeal":{"ticker": "ZM=F", "name": "Tourteau",  "unit": "$/ton"},
}

# Période historique par défaut
DEFAULT_START = "2015-01-01"

# API Keys (dans .env)
USDA_API_KEY = os.getenv("USDA_API_KEY", "")
#```

#**`.env`** — tes clés API (ne jamais committer !) :
#```
#USDA_API_KEY=your_key_here

# ─────────────────────────────────────────
# MODULE 2 — FREIGHT CONFIG
# ─────────────────────────────────────────

# Ports majeurs pour les céréales (lat, lon)
MAJOR_PORTS = {
    # Origines exportatrices
    "us_gulf":        {"lat": 29.95,  "lon": -90.07, "name": "US Gulf (New Orleans)",  "role": "origin"},
    "us_pnw":         {"lat": 46.20,  "lon": -123.8, "name": "US PNW (Portland)",      "role": "origin"},
    "brazil_santos":  {"lat": -23.95, "lon": -46.33, "name": "Santos (Brésil)",        "role": "origin"},
    "brazil_paranagua":{"lat":-25.52, "lon": -48.52, "name": "Paranaguá (Brésil)",     "role": "origin"},
    "argentina_up":   {"lat": -32.95, "lon": -60.63, "name": "Rosario/Up River (ARG)", "role": "origin"},
    "black_sea_odesa":{"lat":  46.48, "lon":  30.73, "name": "Odesa (Ukraine)",        "role": "origin"},
    "black_sea_novor":{"lat":  44.72, "lon":  37.77, "name": "Novorossiysk (Russie)",  "role": "origin"},
    "australia_kwinana":{"lat":-32.23,"lon": 115.78, "name": "Kwinana (Australie)",    "role": "origin"},

    # Destinations importatrices
    "egypt_damietta": {"lat":  31.42, "lon":  31.81, "name": "Damietta (Égypte)",      "role": "destination"},
    "japan_osaka":    {"lat":  34.65, "lon": 135.43, "name": "Osaka (Japon)",          "role": "destination"},
    "china_shanghai": {"lat":  31.23, "lon": 121.47, "name": "Shanghai (Chine)",       "role": "destination"},
    "netherlands_ara":{"lat":  51.90, "lon":   4.48, "name": "Rotterdam (ARA)",        "role": "destination"},
    "spain_barcelona":{"lat":  41.38, "lon":   2.17, "name": "Barcelone (Espagne)",    "role": "destination"},
    "turkey_derince": {"lat":  40.75, "lon":  29.82, "name": "Derince (Turquie)",      "role": "destination"},
    "indonesia_jakarta":{"lat":-6.10, "lon": 106.83, "name": "Jakarta (Indonésie)",    "role": "destination"},
    "south_korea_busan":{"lat":35.10, "lon": 129.04, "name": "Busan (Corée du Sud)",   "role": "destination"},
}

# Routes commerciales stratégiques (origin → destination)
TRADE_ROUTES = {
    # Blé
    "usgulf_egypt":     {"from": "us_gulf",          "to": "egypt_damietta",   "commodity": "wheat",   "vessel": "panamax"},
    "blacksea_egypt":   {"from": "black_sea_odesa",  "to": "egypt_damietta",   "commodity": "wheat",   "vessel": "supramax"},
    "blacksea_turkey":  {"from": "black_sea_novor",  "to": "turkey_derince",   "commodity": "wheat",   "vessel": "supramax"},
    "australia_indo":   {"from": "australia_kwinana","to": "indonesia_jakarta","commodity": "wheat",   "vessel": "panamax"},
    "usgulf_ara":       {"from": "us_gulf",          "to": "netherlands_ara",  "commodity": "wheat",   "vessel": "panamax"},

    # Maïs
    "usgulf_japan":     {"from": "us_gulf",          "to": "japan_osaka",      "commodity": "corn",    "vessel": "panamax"},
    "brazil_china":     {"from": "brazil_santos",    "to": "china_shanghai",   "commodity": "corn",    "vessel": "panamax"},
    "argentina_ara":    {"from": "argentina_up",     "to": "netherlands_ara",  "commodity": "corn",    "vessel": "panamax"},

    # Soja
    "brazil_china_soy": {"from": "brazil_paranagua", "to": "china_shanghai",  "commodity": "soybean", "vessel": "panamax"},
    "usgulf_china_soy": {"from": "us_gulf",           "to": "china_shanghai",  "commodity": "soybean", "vessel": "panamax"},
    "argentina_china":  {"from": "argentina_up",      "to": "china_shanghai",  "commodity": "soybean", "vessel": "panamax"},
}

# Taille des navires (en tonnes métriques de grain)
VESSEL_CAPACITY = {
    "handysize":  35000,
    "supramax":   57000,
    "panamax":    75000,
    "kamsarmax":  82000,
    "capesize":  180000,
}

# ─────────────────────────────────────────
# MODULE 1 — AGRI ZONES (météo)
# ─────────────────────────────────────────
AGRI_ZONES = {
    "us_midwest_corn_belt":  {"lat": 41.5,  "lon": -93.5,  "description": "Iowa — Corn Belt US",        "key_crops": ["corn", "soybean"]},
    "us_plains_wheat":       {"lat": 38.0,  "lon": -98.0,  "description": "Kansas — Winter Wheat",      "key_crops": ["wheat"]},
    "brazil_mato_grosso":    {"lat": -13.0, "lon": -56.0,  "description": "Mato Grosso — Soja Brésil",  "key_crops": ["soybean", "corn"]},
    "argentina_pampas":      {"lat": -34.0, "lon": -60.0,  "description": "Pampas — Soja/Blé Argentine","key_crops": ["soybean", "wheat"]},
    "ukraine_black_earth":   {"lat": 49.0,  "lon":  32.0,  "description": "Ukraine — Tchernozem",       "key_crops": ["wheat", "corn", "soybean"]},
    "australia_wheatbelt":   {"lat": -31.5, "lon": 117.0,  "description": "Western Australia — Blé",   "key_crops": ["wheat"]},
}

# MODULE 5 — LLM
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")

# Groq est gratuit et rapide — modèle recommandé
LLM_PROVIDER = "groq"
LLM_MODEL    = "llama-3.3-70b-versatile"   # Meilleur modèle Groq gratuit