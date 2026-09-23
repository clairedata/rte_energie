"""
================================================================================
  MODULE : ingestion/history_loader.py
  OBJECTIF : Rapatriement par blocs de l'historique volumineux depuis RTE.
================================================================================
"""

import sys
from typing import List, Tuple
from rte_energy.ingestion.rte_client import ingest_rte
from rte_energy.db.init_schema import verify_database

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_full_history() -> None:
    """
    Télécharge l'historique complet par blocs hebdomadaires.
    """
    print("=" * 80)
    print("  📥 EXPANSION DU DATASET HISTORIQUE (1 MOIS DE DONNÉES RTE)")
    print("=" * 80)

    periods: List[Tuple[str, str]] = [
        
        
        ("2026-08-15T00:00:00+02:00", "2026-08-22T00:00:00+02:00"),
        ("2026-08-22T00:00:00+02:00", "2026-08-29T00:00:00+02:00"),
        ("2026-08-29T00:00:00+02:00", "2026-09-04T00:00:00+02:00"),
        ("2026-09-04T00:00:00+02:00", "2026-09-10T00:00:00+02:00"),
        ("2026-09-10T00:00:00+02:00", "2026-09-17T00:00:00+02:00"),
        ("2026-09-17T00:00:00+02:00", "2026-09-24T00:00:00+02:00"),
        
    ]

    total = 0
    for i, (start, end) in enumerate(periods, 1):
        print(f"\n⏳ [{i}/{len(periods)}] Semaine du {start[:10]} au {end[:10]}...")
        nb = ingest_rte(start, end)
        total += nb

    print(f"\n✅ Total récupéré : {total:,} points.")
    verify_database()


if __name__ == "__main__":
    load_full_history()
