"""
================================================================================
  MODULE : db/retention.py
  OBJECTIF : Gestion de la rétention et purge automatique des données historiques
             dans PostgreSQL (fenêtre glissante paramétrable, max 45 jours).
================================================================================
"""

import sys
from pathlib import Path
from typing import Dict

# Ajout du dossier src au sys.path si exécuté directement
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rte_energy.config import get_db_connection, DATA_RETENTION_DAYS, setup_logger

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = setup_logger("rte_retention")


def cleanup_old_data(retention_days: int = DATA_RETENTION_DAYS) -> Dict[str, int]:
    """
    Purge les données antérieures à la fenêtre de rétention (par défaut 45 jours)
    afin d'éviter la surcharge de la base de données PostgreSQL.

    Tables nettoyées :
    1. consumption_forecast : Données de consommation/production RTE (start_date < NOW() - X jours)
    2. weather              : Relevés météo Open-Meteo (timestamp < NOW() - X jours)
    3. model_forecasts      : Anciennes prédictions d'IA (target_date < NOW() - X jours)

    Paramètres :
    ------------
    retention_days : int
        Nombre maximal de jours d'historique à conserver (ex: 45 jours).

    Retourne :
    ----------
    Dict[str, int] : Nombre de lignes supprimées pour chaque table.
    """
    logger.info(f"🧹 Démarrage du nettoyage des données anciennes (Rétention max : {retention_days} jours)...")

    conn = get_db_connection()
    cur = conn.cursor()
    deleted_counts: Dict[str, int] = {}

    try:
        # 1. Purge des données RTE (consumption_forecast)
        cur.execute("""
            DELETE FROM consumption_forecast
            WHERE start_date < NOW() - (INTERVAL '1 day' * %s);
        """, (retention_days,))
        deleted_counts["consumption_forecast"] = cur.rowcount
        logger.info(f"   • consumption_forecast : {cur.rowcount} lignes purgées (> {retention_days} jours)")

        # 2. Purge des relevés météo (weather)
        cur.execute("""
            DELETE FROM weather
            WHERE timestamp < NOW() - (INTERVAL '1 day' * %s);
        """, (retention_days,))
        deleted_counts["weather"] = cur.rowcount
        logger.info(f"   • weather              : {cur.rowcount} lignes purgées (> {retention_days} jours)")

        # 3. Purge des prévisions IA obsolètes (model_forecasts)
        cur.execute("""
            DELETE FROM model_forecasts
            WHERE target_date < NOW() - (INTERVAL '1 day' * %s);
        """, (retention_days,))
        deleted_counts["model_forecasts"] = cur.rowcount
        logger.info(f"   • model_forecasts      : {cur.rowcount} lignes purgées (> {retention_days} jours)")

        # Validation des suppressions dans PostgreSQL
        conn.commit()
        total_deleted = sum(deleted_counts.values())
        logger.info(f"✅ Nettoyage terminé avec succès : {total_deleted} enregistrements obsolètes supprimés au total.")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erreur lors du nettoyage des données anciennes : {e}", exc_info=True)
        raise e
    finally:
        cur.close()
        conn.close()

    return deleted_counts


if __name__ == "__main__":
    cleanup_old_data()
