"""
================================================================================
  MODULE : ingestion/history_loader.py
  OBJECTIF : Rapatriement automatique et par blocs de l'historique volumineux
             depuis l'API RTE France (sur les 45 derniers jours).
================================================================================
"""

import sys
from datetime import datetime, timedelta
from typing import List, Tuple
from rte_energy.config import DATA_RETENTION_DAYS, setup_logger
from rte_energy.ingestion.rte_client import ingest_rte
from rte_energy.ingestion.weather_client import ingest_weather
from rte_energy.db.init_schema import verify_database

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = setup_logger("rte_history_loader")


def generate_weekly_chunks(days_back: int = DATA_RETENTION_DAYS) -> List[Tuple[str, str]]:
    """
    Génère une liste d'intervalles temporels hebdomadaires (7 jours par bloc)
    couvrant les 'days_back' derniers jours jusqu'à J+2.
    L'API RTE limite la durée d'une requête unique, d'où le découpage en blocs.
    """
    now = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    start_point = now - timedelta(days=days_back)
    end_point = now + timedelta(days=2)

    chunks = []
    current_start = start_point

    while current_start < end_point:
        current_end = min(current_start + timedelta(days=7), end_point)
        chunks.append((current_start.isoformat(), current_end.isoformat()))
        current_start = current_end

    return chunks


def load_full_history(days_back: int = DATA_RETENTION_DAYS) -> None:
    """
    Télécharge l'historique complet RTE et Météo pour la fenêtre de rétention (45 jours).
    """
    print("=" * 80)
    print(f"  📥 CHARGEMENT DE L'HISTORIQUE GLOBAL ({days_back} JOURS DE DONNÉES)")
    print("=" * 80)

    periods = generate_weekly_chunks(days_back)
    total_rte = 0

    print(f"📌 {len(periods)} blocs hebdomadaires à télécharger...")
    for i, (start, end) in enumerate(periods, 1):
        print(f"\n⏳ [{i}/{len(periods)}] Période du {start[:10]} au {end[:10]}...")
        try:
            nb = ingest_rte(start, end)
            total_rte += nb
        except Exception as e:
            print(f"⚠️ Erreur lors de l'ingestion du bloc {start[:10]} -> {end[:10]}: {e}")

    print(f"\n✅ Total RTE récupéré : {total_rte:,} points.")

    # Ingestion météo synchronisée sur toute la période
    print("\n🌦️ Rapatriement synchronisé des relevés météo Open-Meteo...")
    try:
        ingest_weather()
    except Exception as e:
        print(f"⚠️ Erreur lors de l'ingestion météo : {e}")

    verify_database()


if __name__ == "__main__":
    load_full_history()
