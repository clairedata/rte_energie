"""
================================================================================
  MODULE : config.py
  OBJECTIF : Centralisation des configurations, des chemins du projet,
             des accès à la base de données et du système de logs.
================================================================================
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any
import psycopg2
from dotenv import load_dotenv

# Encodage UTF-8 pour Windows PowerShell
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==============================================================================
# 1. ARBORESCENCE & CHEMINS DU PROJET
# ==============================================================================
# BASE_DIR pointe toujours vers la racine absolue du projet (e:\Projects\QRA\rte_energie)
BASE_DIR = Path(__file__).resolve().parents[2]

DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = BASE_DIR / "data"
FIGURES_DIR = BASE_DIR / "reports" / "figures"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"
DBT_DIR = BASE_DIR / "dbt_energy"
SRC_DIR = BASE_DIR / "src"

# Modèles spécifiques
CHRONOS_MODEL_DIR = MODELS_DIR / "chronos-bolt-rte"
LIGHTGBM_MODEL_FILE = MODELS_DIR / "lightgbm_rte.joblib"

# Graphiques de sortie
LATEST_FORECAST_PLOT = FIGURES_DIR / "latest_forecast.png"
BENCHMARK_PLOT = FIGURES_DIR / "benchmark_3_way.png"
LGBM_EVAL_PLOT = FIGURES_DIR / "lightgbm_evaluation.png"
LOSS_PLOT = FIGURES_DIR / "loss_convergence.png"

# ==============================================================================
# 2. CHARGEMENT DES VARIABLES D'ENVIRONNEMENT (.env)
# ==============================================================================
# Recherche automatique du fichier .env à la racine ou dans le parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

# Identifiants API RTE France
RTE_CLIENT_ID = os.getenv("RTE_CLIENT_ID")
RTE_CLIENT_SECRET = os.getenv("RTE_CLIENT_SECRET")

# Coordonnées géographiques Météo (France métropolitaine)
WEATHER_LAT = float(os.getenv("WEATHER_LAT", "46.603354"))
WEATHER_LON = float(os.getenv("WEATHER_LON", "1.888334"))

# Paramètres de connexion PostgreSQL
DB_CONFIG: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "energy_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD")
}


# ==============================================================================
# 3. GESTIONNAIRE DE CONNEXION POSTGRESQL
# ==============================================================================
def get_db_connection() -> psycopg2.extensions.connection:
    """
    Ouvre et renvoie une connexion à PostgreSQL avec encodage UTF-8.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    return conn


# ==============================================================================
# 4. CONFIGURATION CENTRALISÉE DES LOGS
# ==============================================================================
def setup_logger(name: str = "rte_energy") -> logging.Logger:
    """
    Configure un logger unifié écrivant à la fois dans la console
    et dans 'logs/pipeline.log'.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "pipeline.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Handler Fichier
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Handler Console
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger
