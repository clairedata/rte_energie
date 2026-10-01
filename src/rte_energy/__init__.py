"""
================================================================================
  Package principal : rte_energy
  Pipeline de collecte, d'ingestion, d'automatisation et de modélisation prédictive
  de la consommation électrique française (RTE France).
================================================================================
"""

def main() -> None:
    """Point d'entrée CLI principal (uv run rte-energy)."""
    from rte_energy.production.pipeline import run_pipeline
    run_pipeline()
