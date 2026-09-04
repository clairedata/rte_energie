import os
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

# cette fonction permet d'avoir le Token d'accès du portail rte
def get_token():
    url = "https://digital.iservices.rte-france.com/token/oauth/"
    resp = requests.post(
        url,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "client_credentials"}
    )
    resp.raise_for_status()
    return resp.json()["access_token"]
    
# Cette fonction permet d'insérer les données dans la base de données à partir du portail rte
def ingest(start_date: str | None = None, end_date: str | None = None):
    # Si aucune date n'est fournie, on calcule dynamiquement : aujourd'hui 00:00 -> J+2 00:00
    if not start_date or not end_date:
        now = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = now.isoformat()
        end_date = (now + timedelta(days=2)).isoformat()

    print("Récupération du token OAuth2 RTE...")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Endpoint testé précédemment
    url = "https://digital.iservices.rte-france.com/open_api/generation_forecast/v3/forecasts"
    
    params = {
        "start_date": start_date,
        "end_date": end_date
    }

    print(f"Interrogation de l'API RTE ({start_date} -> {end_date})...")
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()

    # Extraction et aplatissement des données
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

    print(f"{len(rows)} points récupérés. Insertion dans PostgreSQL...")

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

    print("Données insérées avec succès dans la base !")

if __name__ == "__main__":
    ingest()    