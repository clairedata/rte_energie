"""
================================================================================
  MODULE : ingestion/rte_client.py
  OBJECTIF : Ingestion des données énergétiques prévisionnelles depuis l'API RTE France.
================================================================================
"""

import sys
from datetime import datetime, timedelta
from typing import Optional
import requests
from psycopg2.extras import execute_values
from rte_energy.config import get_db_connection, RTE_CLIENT_ID, RTE_CLIENT_SECRET

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_token() -> str:
    """
    Récupère le jeton OAuth2 auprès du portail développeur RTE France.
    """
    if not RTE_CLIENT_ID or not RTE_CLIENT_SECRET:
        raise ValueError("RTE_CLIENT_ID et RTE_CLIENT_SECRET doivent être configurés dans le fichier .env.")

    url = "https://digital.iservices.rte-france.com/token/oauth/"
    resp = requests.post(
        url,
        auth=(RTE_CLIENT_ID, RTE_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def ingest_rte(start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
    """
    Interroge l'API RTE France pour la plage demandée (par défaut J à J+2)
    et effectue un upsert dans la table PostgreSQL 'consumption_forecast'.
    """
    if not start_date or not end_date:
        now = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = now.isoformat()
        end_date = (now + timedelta(days=2)).isoformat()

    print(f"🔑 Récupération du jeton OAuth2 RTE...")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://digital.iservices.rte-france.com/open_api/generation_forecast/v3/forecasts"
    params = {"start_date": start_date, "end_date": end_date}

    print(f"📡 Interrogation de l'API RTE ({start_date} -> {end_date})...")
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
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
        print("⚠️ Aucun point retourné par l'API RTE sur ce créneau.")
        return 0

    print(f"📥 {len(rows)} points récupérés. Insertion / Upsert dans PostgreSQL...")
    conn = get_db_connection()
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

    print(f"✅ {len(rows)} points RTE insérés/mis à jour avec succès dans PostgreSQL !")
    return len(rows)


if __name__ == "__main__":
    ingest_rte()
