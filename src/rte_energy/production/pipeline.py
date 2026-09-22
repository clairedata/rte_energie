"""
================================================================================
  MODULE : production/pipeline.py
  OBJECTIF : Orchestrateur unifié de bout en bout (End-to-End) :
             1. Ingestion RTE
             2. Ingestion Météo Open-Meteo
             3. Transformations ELT dbt Core
             4. Inférence IA en production (predict.py)
================================================================================
"""

import sys
import time
import subprocess
from rte_energy.config import DBT_DIR, setup_logger
from rte_energy.ingestion.rte_client import ingest_rte
from rte_energy.ingestion.weather_client import ingest_weather
from rte_energy.production.predict import generate_and_save_forecasts

logger = setup_logger("rte_pipeline")


def run_dbt() -> None:
    """
    Exécute les transformations dbt Core pour actualiser les tables du schéma analytics.
    """
    logger.info(f"Lancement de dbt run dans : {DBT_DIR}")
    cmd = [sys.executable, "-m", "dbt.cli.main", "run", "--profiles-dir", "."]
    res = subprocess.run(
        cmd,
        cwd=DBT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if res.returncode != 0:
        logger.error(f"Erreur dbt run :\n{res.stderr or res.stdout}")
        raise RuntimeError("Échec de l'étape dbt run.")
    else:
        logger.info("Transformations dbt exécutées avec succès.")


def run_pipeline() -> None:
    """
    Exécute les 4 étapes du cycle de vie quotidien de manière ordonnée.
    """
    start_time = time.time()
    logger.info("==========================================")
    logger.info("  DÉMARRAGE DU PIPELINE UNIFIÉ (E2E)      ")
    logger.info("==========================================")

    # 1. Ingestion RTE
    try:
        logger.info("--- [1/4] Ingestion RTE France ---")
        ingest_rte()
        logger.info("Ingestion RTE terminée.")
    except Exception as e:
        logger.error(f"Erreur RTE : {e}", exc_info=True)

    # 2. Ingestion Météo
    try:
        logger.info("--- [2/4] Ingestion Open-Meteo ---")
        ingest_weather()
        logger.info("Ingestion Météo terminée.")
    except Exception as e:
        logger.error(f"Erreur Météo : {e}", exc_info=True)

    # 3. Transformations dbt
    try:
        logger.info("--- [3/4] Transformations ELT dbt ---")
        run_dbt()
    except Exception as e:
        logger.error(f"Erreur dbt : {e}", exc_info=True)

    # 4. Inférence IA en production
    try:
        logger.info("--- [4/4] Inférence IA Production (Chronos-Bolt) ---")
        generate_and_save_forecasts()
        logger.info("Inférence terminée.")
    except Exception as e:
        logger.error(f"Erreur Inférence : {e}", exc_info=True)

    duration = round(time.time() - start_time, 2)
    logger.info("==========================================")
    logger.info(f" PIPELINE COMPLET TERMINÉ EN {duration}s ")
    logger.info("==========================================")


if __name__ == "__main__":
    run_pipeline()
