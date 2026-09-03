import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def init_db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "energy_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD")
    )
    cur = conn.cursor()

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            timestamp TIMESTAMPTZ PRIMARY KEY,
            temperature_c FLOAT,
            wind_speed FLOAT
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Tables créées avec succès dans PostgreSQL !")

if __name__ == "__main__":
    init_db()