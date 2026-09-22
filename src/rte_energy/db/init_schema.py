"""
================================================================================
  MODULE : db/init_schema.py
  OBJECTIF : Création et vérification du schéma PostgreSQL (tables et contraintes).
================================================================================
"""

import sys
from rte_energy.config import get_db_connection

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def init_db() -> None:
    """
    Initialise les 3 tables fondamentales de l'application dans PostgreSQL :
    1. consumption_forecast : Données brutes RTE (consommation & production)
    2. weather : Relevés météo Open-Meteo
    3. model_forecasts : Prévisions générées par les modèles d'IA
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Table de consommation et production RTE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS consumption_forecast (
            id SERIAL PRIMARY KEY,
            start_date TIMESTAMPTZ NOT NULL,
            end_date TIMESTAMPTZ NOT NULL,
            value_mw FLOAT NOT NULL,
            production_type VARCHAR(50) NOT NULL,
            forecast_type VARCHAR(20) NOT NULL DEFAULT 'CURRENT',
            sub_type VARCHAR(20) DEFAULT '',
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT unique_forecast UNIQUE (start_date, production_type, forecast_type, sub_type)
        );
    """)

    # 2. Table météo Open-Meteo
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL UNIQUE,
            temperature_c FLOAT,
            wind_speed FLOAT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # 3. Table des prédictions d'IA en production
    cur.execute("""
        CREATE TABLE IF NOT EXISTS model_forecasts (
            id SERIAL PRIMARY KEY,
            target_date TIMESTAMPTZ NOT NULL,
            forecast_mw FLOAT NOT NULL,
            lower_bound_mw FLOAT,
            upper_bound_mw FLOAT,
            model_name VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT unique_model_forecast UNIQUE (model_name, target_date)
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Schéma initialisé avec succès dans PostgreSQL (consumption_forecast, weather, model_forecasts) !")


def verify_database() -> None:
    """
    Affiche un état des lieux de la volumétrie et des plages temporelles en base.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(DISTINCT start_date), MIN(start_date), MAX(start_date)
        FROM consumption_forecast
        WHERE production_type = 'AGGREGATED_CPC' AND forecast_type = 'D-1';
    """)
    res = cur.fetchone()
    nb_points, min_d, max_d = res if res else (0, None, None)

    cur.execute("SELECT COUNT(*) FROM weather;")
    nb_weather = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM model_forecasts;")
    nb_forecasts = cur.fetchone()[0]

    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("  📊 ÉTAT DES LIEUX DE LA BASE DE DONNÉES POSTGRESQL")
    print("=" * 80)
    print(f"  • Points de consommation (AGGREGATED_CPC D-1) : {nb_points:,} quarts d'heure")
    print(f"  • Plage temporelle consommation                : du {min_d} au {max_d}")
    print(f"  • Relevés météorologiques (Open-Meteo)         : {nb_weather:,} heures")
    print(f"  • Prévisions d'IA enregistrées                 : {nb_forecasts:,} points")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    init_db()
    verify_database()
