"""
================================================================================
  MODULE : db/init_schema.py
  OBJECTIF : Création et vérification du schéma PostgreSQL (tables et contraintes)
             incluant la table d'authentification RBAC et les utilisateurs initiaux.
================================================================================
"""

import sys
from pathlib import Path

# Ajout du dossier src au chemin d'importation Python
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rte_energy.config import get_db_connection
from rte_energy.auth.security import hash_password

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def init_db() -> None:
    """
    Initialise les 4 tables fondamentales de l'application dans PostgreSQL :
    1. consumption_forecast : Données brutes RTE (consommation & production)
    2. weather : Relevés météo Open-Meteo
    3. model_forecasts : Prévisions générées par les modèles d'IA
    4. users : Comptes utilisateurs et rôles pour l'authentification JWT / RBAC
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

    # 4. Table des utilisateurs & rôles (RBAC) pour l'authentification JWT
    # ==============================================================================
    # EXPLICATION DU SCHÉMA JWT / RBAC :
    # - email : Identifiant unique utilisé pour le login et comme claim 'sub' dans le JWT.
    # - hashed_password : Hash cryptographique bcrypt (le mot de passe en clair n'est JAMAIS stocké).
    # - role : Rôle RBAC ('viewer', 'analyst', 'admin') injecté dans le payload du JWT.
    # - is_active : Permet de désactiver un compte immédiatement sans supprimer l'historique.
    # ==============================================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('viewer', 'analyst', 'admin')),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Schéma initialisé avec succès dans PostgreSQL (consumption_forecast, weather, model_forecasts, users) !")


def seed_default_users() -> None:
    """
    Crée les comptes de démonstration pour chaque rôle RBAC s'ils n'existent pas encore :
    - Administrateur (admin@rte.fr / RteAdmin2026!)
    - Analyste Data (analyst@rte.fr / RteAnalyst2026!)
    - Observateur (viewer@rte.fr / RteViewer2026!)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    default_users = [
        {
            "email": "admin@rte.fr",
            "password": "RteAdmin2026!",
            "full_name": "Administrateur Système",
            "role": "admin"
        },
        {
            "email": "analyst@rte.fr",
            "password": "RteAnalyst2026!",
            "full_name": "Data Scientist RTE",
            "role": "analyst"
        },
        {
            "email": "viewer@rte.fr",
            "password": "RteViewer2026!",
            "full_name": "Consultant Énergie",
            "role": "viewer"
        }
    ]

    for u in default_users:
        cur.execute("SELECT id FROM users WHERE email = %s;", (u["email"],))
        if not cur.fetchone():
            hashed = hash_password(u["password"])
            cur.execute("""
                INSERT INTO users (email, hashed_password, full_name, role, is_active)
                VALUES (%s, %s, %s, %s, TRUE);
            """, (u["email"], hashed, u["full_name"], u["role"]))
            print(f"  👤 Utilisateur initial créé : {u['email']} [{u['role']}]")

    conn.commit()
    cur.close()
    conn.close()


def verify_database() -> None:
    """
    Affiche un état des lieux de la volumétrie, des plages temporelles et des utilisateurs en base.
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

    cur.execute("SELECT COUNT(*) FROM users;")
    nb_users = cur.fetchone()[0]

    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("  📊 ÉTAT DES LIEUX DE LA BASE DE DONNÉES POSTGRESQL")
    print("=" * 80)
    print(f"  • Points de consommation (AGGREGATED_CPC D-1) : {nb_points:,} quarts d'heure")
    print(f"  • Plage temporelle consommation                : du {min_d} au {max_d}")
    print(f"  • Relevés météorologiques (Open-Meteo)         : {nb_weather:,} heures")
    print(f"  • Prévisions d'IA enregistrées                 : {nb_forecasts:,} points")
    print(f"  • Utilisateurs enregistrés (RBAC)             : {nb_users} comptes")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    init_db()
    seed_default_users()
    verify_database()
