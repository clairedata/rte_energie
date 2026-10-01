"""
================================================================================
  MODULE : production/pipeline.py
  OBJECTIF : Orchestrateur unifié de bout en bout (End-to-End) :
             1. Ingestion quotidienne RTE France (réalisé + prévisions)
             2. Ingestion Météo Open-Meteo (synchronisée)
             3. Nettoyage et purge des données anciennes (> 45 jours)
             4. Transformations ELT dbt Core (schéma analytics)
             5. Inférence IA en production (modèle Chronos-Bolt)
================================================================================
"""

import sys
import time
import subprocess
from rte_energy.config import DBT_DIR, DATA_RETENTION_DAYS, setup_logger
from rte_energy.ingestion.rte_client import ingest_rte
from rte_energy.ingestion.weather_client import ingest_weather
from rte_energy.db.retention import cleanup_old_data
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
    Exécute les 5 étapes du cycle de vie quotidien de manière ordonnée :
    - [1/5] Ingestion RTE (données fraîches et prévisions)
    - [2/5] Ingestion Météo (températures et vent)
    - [3/5] Nettoyage / Purge automatique (> 45 jours pour alléger PostgreSQL)
    - [4/5] Transformations ELT dbt (vues et tables de données préparées)
    - [5/5] Inférence IA (génération des prévisions J+1)
    """
    start_time = time.time()
    logger.info("==========================================")
    logger.info("  DÉMARRAGE DU PIPELINE UNIFIÉ QUOTIDIEN  ")
    logger.info("==========================================")

    # 1. Ingestion RTE
    try:
        logger.info("--- [1/5] Ingestion RTE France (J-2 à J+2) ---")
        ingest_rte()
        logger.info("Ingestion RTE terminée avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion RTE : {e}", exc_info=True)

    # 2. Ingestion Météo
    try:
        logger.info("--- [2/5] Ingestion Open-Meteo ---")
        ingest_weather()
        logger.info("Ingestion Météo terminée avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion Météo : {e}", exc_info=True)

    # 3. Nettoyage et purge des données anciennes (> 45 jours)
    try:
        logger.info(f"--- [3/5] Purge des données obsolètes (> {DATA_RETENTION_DAYS} jours) ---")
        cleanup_old_data(retention_days=DATA_RETENTION_DAYS)
        logger.info("Purge des données anciennes effectuée.")
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage de la base : {e}", exc_info=True)

    # 4. Transformations dbt
    try:
        logger.info("--- [4/5] Transformations ELT dbt Core ---")
        run_dbt()
    except Exception as e:
        logger.error(f"Erreur lors de l'étape dbt : {e}", exc_info=True)

    # 5. Inférence IA en production
    try:
        logger.info("--- [5/5] Inférence IA Production (Chronos-Bolt) ---")
        generate_and_save_forecasts()
        logger.info("Inférence et génération des prédictions terminées.")
    except Exception as e:
        logger.error(f"Erreur lors de l'inférence IA : {e}", exc_info=True)

    duration = round(time.time() - start_time, 2)
    logger.info("==========================================")
    logger.info(f" PIPELINE COMPLET TERMINÉ EN {duration}s ")
    logger.info("==========================================")


if __name__ == "__main__":
    run_pipeline()
