"""
================================================================================
  MODULE : src/rte_energy/auth/db_init.py
  OBJECTIF : Création automatique et sécurisée de la table 'users' dans PostgreSQL
             avec peuplement automatique des comptes de démonstration RBAC.
================================================================================
"""

import psycopg2.extras
from rte_energy.config import get_db_connection, setup_logger
from rte_energy.auth.security import hash_password

logger = setup_logger("rte_auth_db")


def ensure_users_table_exists() -> None:
    """
    Vérifie si la table 'users' existe dans la base PostgreSQL connectée.
    Si elle n'existe pas, elle est créée immédiatement et peuplée avec les 3 comptes de démo :
    - admin@rte.fr (RteAdmin2026! / admin)
    - analyst@rte.fr (RteAnalyst2026! / analyst)
    - viewer@rte.fr (RteViewer2026! / viewer)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Création de la table users si inexistante
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.users (
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

        # 2. Peuplement des comptes de démonstration initiaux
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
            cur.execute("SELECT id FROM public.users WHERE email = %s;", (u["email"],))
            if not cur.fetchone():
                hashed = hash_password(u["password"])
                cur.execute("""
                    INSERT INTO public.users (email, hashed_password, full_name, role, is_active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    ON CONFLICT (email) DO NOTHING;
                """, (u["email"], hashed, u["full_name"], u["role"]))
                logger.info(f"Compte RBAC initial créé : {u['email']} [{u['role']}]")

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Table 'public.users' vérifiée et synchronisée avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la table users : {e}")
