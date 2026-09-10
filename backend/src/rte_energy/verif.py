from enum import verify
import os
import sys
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

CLIENT_ID = os.getenv("RTE_CLIENT_ID")
CLIENT_SECRET = os.getenv("RTE_CLIENT_SECRET")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "energy_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD")
}

def get_token() -> str:
    """
    Récupère le jeton OAuth2 auprès du portail développeur RTE France.
    """
    url = "https://digital.iservices.rte-france.com/token/oauth/"
    resp = requests.post(
        url,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def verif():    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT start_date), MIN(start_date), MAX(start_date)
        FROM consumption_forecast
        WHERE production_type = 'AGGREGATED_CPC' AND forecast_type = 'D-1';
    """)
    nb_distinct, min_d, max_d = cur.fetchone()
    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("  🎉 EXPANSION RÉUSSIE DU DATASET HISTORIQUE !")
    print("=" * 80)
    print(f"  • Total de points uniques (quarts d'heure) : {nb_distinct:,} points")
    print(f"  • Plage temporelle disponible en base      : du {min_d} au {max_d}")
    print(f"  • Soit environ                             : {nb_distinct // 96} jours complets de données !")
    print("=" * 80 + "\n")
    print("👉 Nous avons maintenant la matière indispensable pour créer nos fenêtres d'apprentissage !")

if __name__ == "__main__":
    verif()
