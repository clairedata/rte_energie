import os
import sys
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

# ==============================================================================
# 1. CONFIGURATION ET CONNEXION
# ==============================================================================
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

def ingest_period(start_date: str, end_date: str, token: str) -> int:
    """
    Interroge l'API RTE pour une tranche de dates et insère les lignes dans PostgreSQL.
    Gère les conflits via la contrainte UNIQUE (upsert).
    """
    url = "https://digital.iservices.rte-france.com/open_api/generation_forecast/v3/forecasts"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "start_date": start_date,
        "end_date": end_date
    }

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"⚠️ Erreur sur la période {start_date} -> {end_date} (Code {resp.status_code})")
        return 0

    data = resp.json()
    rows = []
    for item in data.get("forecasts", []):
        f_type = item.get("type", "UNKNOWN")
        prod_type = item.get("production_type", "UNKNOWN")
        sub_type = item.get("sub_type") or ""
        for point in item.get("values", []):
            rows.append((
                point["start_date"],
                point["end_date"],
                point["value"],
                prod_type,
                f_type,
                sub_type
            ))

    if not rows:
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    query = """
        INSERT INTO consumption_forecast (start_date, end_date, value_mw, production_type, forecast_type, sub_type)
        VALUES %s
        ON CONFLICT (start_date, production_type, forecast_type, sub_type)
        DO UPDATE SET
            value_mw = EXCLUDED.value_mw,
            end_date = EXCLUDED.end_date,
            updated_at = NOW();
    """
    execute_values(cur, query, rows)
    conn.commit()
    cur.close()
    conn.close()

    return len(rows)

def ingest_history():
    print("================================================================================")
    print("  📥 PHASE 1 : EXPANSION DU DATASET HISTORIQUE (1 MOIS DE DONNÉES RTE)          ")
    print("================================================================================")
    
    print("\n🔑 Récupération du jeton d'authentification OAuth2...")
    token = get_token()
    print("✅ Authentification réussie !")

    # Tranches hebdomadaires d'août à début septembre 2026
    # Pour ne pas surcharger l'API, on interroge par blocs de 7 jours
    periods = [
        ("2026-08-01T00:00:00+02:00", "2026-08-08T00:00:00+02:00"),
        ("2026-08-08T00:00:00+02:00", "2026-08-15T00:00:00+02:00"),
        ("2026-08-15T00:00:00+02:00", "2026-08-22T00:00:00+02:00"),
        ("2026-08-22T00:00:00+02:00", "2026-08-29T00:00:00+02:00"),
        ("2026-08-29T00:00:00+02:00", "2026-09-04T00:00:00+02:00"),
    ]

    total_inserted = 0
    for i, (start, end) in enumerate(periods, 1):
        print(f"\n⏳ [{i}/{len(periods)}] Téléchargement de la semaine : {start[:10]} au {end[:10]}...")
        nb = ingest_period(start, end, token)
        total_inserted += nb
        print(f"   -> {nb:,} points insérés/mis à jour dans PostgreSQL.")

    # Vérification du nouveau volume total en base
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
    ingest_history()
