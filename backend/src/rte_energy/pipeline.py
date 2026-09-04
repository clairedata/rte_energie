import time
import logging
from rte_energy.ingest_rte import ingest as ingest_rte
from rte_energy.ingest_weather import ingest_weather

# Configuration des logs : à la fois dans la console et dans pipeline.log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def run_pipeline() -> None:
    """
    Orchestrateur principal : exécute la collecte RTE puis la collecte Météo.
    """
    start_time = time.time()
    logging.info("==========================================")
    logging.info("  DÉMARRAGE DU PIPELINE ÉNERGIE & MÉTÉO   ")
    logging.info("==========================================")

    # 1. Ingestion des données RTE
    try:
        logging.info("--- [1/2] Lancement ingestion RTE France ---")
        ingest_rte()
        logging.info("Ingestion RTE terminée avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors de l'ingestion RTE : {e}", exc_info=True)

    # 2. Ingestion des données Météo
    try:
        logging.info("--- [2/2] Lancement ingestion Open-Meteo ---")
        ingest_weather()
        logging.info("Ingestion Météo terminée avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors de l'ingestion Météo : {e}", exc_info=True)

    duration = round(time.time() - start_time, 2)
    logging.info("==========================================")
    logging.info(f" PIPELINE TERMINÉ EN {duration} SECONDES ")
    logging.info("==========================================")

if __name__ == "__main__":
    run_pipeline()
