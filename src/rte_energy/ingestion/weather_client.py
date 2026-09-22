"""
================================================================================
  MODULE : ingestion/weather_client.py
  OBJECTIF : Ingestion des données météo (température et vent) depuis Open-Meteo.
================================================================================
"""

import sys
from datetime import datetime, timedelta
from typing import Optional
import requests
from psycopg2.extras import execute_values
from rte_energy.config import get_db_connection, WEATHER_LAT, WEATHER_LON

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def ingest_weather(start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
    """
    Récupère les relevés météo (température à 2m et vent à 10m) via Open-Meteo
    et les insère par upsert dans la table PostgreSQL 'weather'.
    """
    if not start_date or not end_date:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT MIN(start_date)::date, MAX(end_date)::date FROM consumption_forecast;")
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and row[0] and row[1]:
                start_date = row[0].strftime("%Y-%m-%d")
                end_date = (row[1] + timedelta(days=2)).strftime("%Y-%m-%d")
            else:
                now = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
                start_date = now.strftime("%Y-%m-%d")
                end_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        except Exception:
            now = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = now.strftime("%Y-%m-%d")
            end_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": WEATHER_LAT,
        "longitude": WEATHER_LON,
        "hourly": ["temperature_2m", "wind_speed_10m"],
        "timezone": "Europe/Paris",
        "start_date": start_date,
        "end_date": end_date
    }

    print(f"📡 Interrogation de l'API Open-Meteo ({start_date} -> {end_date})...")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    timestamps = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    wind_speeds = hourly.get("wind_speed_10m", [])

    rows = []
    for ts, temp, wind in zip(timestamps, temperatures, wind_speeds):
        formatted_ts = f"{ts}:00+02:00" if len(ts) == 16 else ts
        rows.append((formatted_ts, temp, wind))

    if not rows:
        print("⚠️ Aucun point météo retourné.")
        return 0

    print(f"📥 {len(rows)} relevés météo récupérés. Insertion / Upsert dans PostgreSQL...")
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO weather (timestamp, temperature_c, wind_speed)
        VALUES %s
        ON CONFLICT (timestamp)
        DO UPDATE SET 
            temperature_c = EXCLUDED.temperature_c,
            wind_speed = EXCLUDED.wind_speed,
            updated_at = NOW();
    """
    execute_values(cur, query, rows)
    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ {len(rows)} relevés météo insérés avec succès dans la table 'weather' !")
    return len(rows)


if __name__ == "__main__":
    ingest_weather()
