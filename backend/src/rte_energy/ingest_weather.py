import os
import requests
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "energy_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD")
}

# Coordonnées géographiques (Centre de la France par défaut)
LATITUDE = float(os.getenv("WEATHER_LAT", "46.603354"))
LONGITUDE = float(os.getenv("WEATHER_LON", "1.888334"))

def ingest_weather(start_date: str = "2026-09-04", end_date: str = "2026-09-06"):
    """
    Récupère les prévisions météo (température et vitesse du vent)
    via l'API Open-Meteo et les enregistre dans PostgreSQL.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": ["temperature_2m", "wind_speed_10m"],
        "timezone": "Europe/Paris",
        "start_date": start_date,
        "end_date": end_date
    }

    print(f"Interrogation de l'API Open-Meteo ({start_date} -> {end_date})...")
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    timestamps = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    wind_speeds = hourly.get("wind_speed_10m", [])

    rows = []
    for ts, temp, wind in zip(timestamps, temperatures, wind_speeds):
        # Formatage du timestamp avec le fuseau horaire de Paris (+02:00 en heure d'été)
        formatted_ts = f"{ts}:00+02:00" if len(ts) == 16 else ts
        rows.append((
            formatted_ts,
            temp,
            wind
        ))

    print(f"{len(rows)} relevés météo récupérés. Insertion dans PostgreSQL...")

    conn = psycopg2.connect(**DB_CONFIG)
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

    print("Données météo insérées avec succès dans la table 'weather' !")

if __name__ == "__main__":
    ingest_weather()
