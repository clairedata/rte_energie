"""
Package principal rte_energy :
Pipeline de collecte, d'ingestion, d'automatisation et de modélisation prédictive
de la consommation électrique française (RTE France).
"""

from rte_energy.production.pipeline import run_pipeline
from rte_energy.production.predict import generate_and_save_forecasts
from rte_energy.ingestion.rte_client import ingest_rte
from rte_energy.ingestion.weather_client import ingest_weather
from rte_energy.db.init_schema import init_db, verify_database

def main() -> None:
    """Point d'entrée CLI : uv run rte-energy"""
    run_pipeline()

__all__ = [
    "run_pipeline",
    "generate_and_save_forecasts",
    "ingest_rte",
    "ingest_weather",
    "init_db",
    "verify_database",
    "main"
]
