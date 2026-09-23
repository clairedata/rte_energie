"""
================================================================================
  MODULE : src/rte_energy/api/app.py
  OBJECTIF : API REST FastAPI pour servir les données éCO2mix en temps réel
             et les prédictions des modèles IA (Chronos-Bolt, LightGBM, Baseline)
             au Front-End interactif.
================================================================================
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import psycopg2.extras

from rte_energy.config import (
    get_db_connection,
    FRONTEND_DIR,
    CHRONOS_MODEL_DIR,
    LIGHTGBM_MODEL_FILE,
    setup_logger
)

# Configuration du logger pour l'API
logger = setup_logger("rte_api")

# Initialisation de l'application FastAPI
app = FastAPI(
    title="RTE Energy - API éCO2mix & Inférence IA",
    description="API REST servant l'historique de consommation électrique et les prévisions TSFM / ML",
    version="1.0.0"
)

# Activation du CORS (Cross-Origin Resource Sharing) pour permettre les requêtes depuis n'importe quel client web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 1. ENDPOINTS D'ÉTAT & SANTÉ DU SYSTÈME (HEALTHCHECK)
# ==============================================================================

@app.get("/api/status", summary="Vérifie la santé du système et la disponibilité des données")
def get_system_status() -> Dict[str, Any]:
    """
    Contrôle la connectivité à PostgreSQL, la présence des modèles IA sur disque
    et la fraîcheur des données collectées.
    """
    db_ok = False
    counts = {}
    last_update = None

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Vérification du nombre de lignes dans les tables clés
        cur.execute("SELECT COUNT(*) AS n FROM analytics.fct_national_consumption;")
        counts["consumption_records"] = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM public.model_forecasts;")
        counts["forecast_records"] = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM public.weather;")
        counts["weather_records"] = cur.fetchone()["n"]

        # Date de la dernière mesure réelle disponible
        cur.execute("SELECT MAX(start_date) AS max_date FROM analytics.fct_national_consumption;")
        row = cur.fetchone()
        if row and row["max_date"]:
            last_update = row["max_date"].isoformat()

        cur.close()
        conn.close()
        db_ok = True
    except Exception as e:
        logger.error(f"Erreur lors du contrôle de statut de la base : {e}")

    return {
        "status": "online" if db_ok else "degraded",
        "database_connected": db_ok,
        "last_consumption_time": last_update,
        "records": counts,
        "models": {
            "chronos_bolt_fine_tuned": CHRONOS_MODEL_DIR.exists(),
            "lightgbm_multivarié": LIGHTGBM_MODEL_FILE.exists()
        }
    }


# ==============================================================================
# 2. ENDPOINTS DES INDICATEURS CLÉS EN TEMPS RÉEL (KPIS ÉCO2MIX)
# ==============================================================================

@app.get("/api/kpi", summary="Indicateurs de synthèse en temps réel (Style éCO2mix)")
def get_kpis(date: Optional[str] = Query(default=None, description="Date spécifique au format YYYY-MM-DD")) -> Dict[str, Any]:
    """
    Calcule et agrège les indicateurs phares inspirés d'éCO2mix :
    - Puissance actuelle appelée (MW) ou valeur de fin de journée
    - Variation par rapport à la même heure la veille (J-1)
    - Pic de consommation de la journée (MW et heure)
    - Creux nocturne (MW et heure)
    - Conditions météo nationales (température, vent)
    - Impact de thermosensibilité thermique estimé
    - Métriques d'erreur du modèle champion
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        thermosensitivity_gradient_mw = 2400.0  # MW / °C

        if date:
            # 1. Requête pour la journée spécifique demandée
            cur.execute("""
                SELECT start_date, value_mw 
                FROM analytics.fct_national_consumption 
                WHERE start_date >= %s::timestamptz AND start_date < (%s::timestamptz + INTERVAL '1 day')
                ORDER BY start_date ASC;
            """, (date, date))
            day_rows = cur.fetchall()

            if not day_rows:
                raise HTTPException(status_code=404, detail=f"Aucune donnée de consommation disponible pour la date {date}.")

            # 2. Requête pour le jour précédent (J-1) pour le calcul du delta
            cur.execute("""
                SELECT start_date, value_mw 
                FROM analytics.fct_national_consumption 
                WHERE start_date >= (%s::timestamptz - INTERVAL '1 day') AND start_date < %s::timestamptz
                ORDER BY start_date ASC;
            """, (date, date))
            j_minus_1_rows = cur.fetchall()

            latest_point = day_rows[-1]
            current_mw = float(latest_point["value_mw"])
            current_time = latest_point["start_date"].isoformat()

            delta_mw = 0.0
            delta_pct = 0.0
            if j_minus_1_rows:
                j_minus_1_point = j_minus_1_rows[-1]
                j_minus_1_mw = float(j_minus_1_point["value_mw"])
                delta_mw = round(current_mw - j_minus_1_mw, 1)
                delta_pct = round((delta_mw / j_minus_1_mw) * 100, 2) if j_minus_1_mw else 0.0

            max_pt = max(day_rows, key=lambda r: float(r["value_mw"]))
            min_pt = min(day_rows, key=lambda r: float(r["value_mw"]))

            day_peak_mw = float(max_pt["value_mw"])
            day_peak_time = max_pt["start_date"].strftime("%Hh%M")
            day_low_mw = float(min_pt["value_mw"])
            day_low_time = min_pt["start_date"].strftime("%Hh%M")

            # Météo du jour choisi
            cur.execute("""
                SELECT AVG(temperature_c) as avg_temp, AVG(wind_speed) as avg_wind 
                FROM public.weather 
                WHERE timestamp >= %s::timestamptz AND timestamp < (%s::timestamptz + INTERVAL '1 day');
            """, (date, date))
            weather_row = cur.fetchone()
            temp_c = float(round(weather_row["avg_temp"], 1)) if weather_row and weather_row["avg_temp"] is not None else 18.0
            wind_kmh = float(round(weather_row["avg_wind"], 1)) if weather_row and weather_row["avg_wind"] is not None else 10.0

        else:
            # Mode temps réel (dernière observation disponible)
            cur.execute("""
                SELECT start_date, value_mw 
                FROM analytics.fct_national_consumption 
                ORDER BY start_date DESC 
                LIMIT 97;
            """)
            recent_rows = cur.fetchall()

            if not recent_rows:
                raise HTTPException(status_code=404, detail="Aucune donnée de consommation disponible.")

            latest_point = recent_rows[0]
            current_mw = float(latest_point["value_mw"])
            current_time = latest_point["start_date"].isoformat()

            delta_mw = 0.0
            delta_pct = 0.0
            if len(recent_rows) >= 97:
                j_minus_1_point = recent_rows[96]
                j_minus_1_mw = float(j_minus_1_point["value_mw"])
                delta_mw = round(current_mw - j_minus_1_mw, 1)
                delta_pct = round((delta_mw / j_minus_1_mw) * 100, 2) if j_minus_1_mw else 0.0

            slice_24h = recent_rows[:96]
            max_pt = max(slice_24h, key=lambda r: float(r["value_mw"]))
            min_pt = min(slice_24h, key=lambda r: float(r["value_mw"]))

            day_peak_mw = float(max_pt["value_mw"])
            day_peak_time = max_pt["start_date"].strftime("%Hh%M")
            day_low_mw = float(min_pt["value_mw"])
            day_low_time = min_pt["start_date"].strftime("%Hh%M")

            cur.execute("""
                SELECT timestamp, temperature_c, wind_speed 
                FROM public.weather 
                ORDER BY timestamp DESC 
                LIMIT 1;
            """)
            weather_row = cur.fetchone()
            temp_c = float(weather_row["temperature_c"]) if weather_row else 18.0
            wind_kmh = float(weather_row["wind_speed"]) if weather_row else 10.0

        if temp_c < 15.0:
            thermosensitive_mw = round((15.0 - temp_c) * thermosensitivity_gradient_mw, 0)
        else:
            thermosensitive_mw = 0.0

        return {
            "current_consumption_mw": current_mw,
            "current_time": current_time,
            "selected_date": date,
            "delta_24h_mw": delta_mw,
            "delta_24h_pct": delta_pct,
            "day_peak": {
                "value_mw": day_peak_mw,
                "time": day_peak_time
            },
            "day_low": {
                "value_mw": day_low_mw,
                "time": day_low_time
            },
            "weather": {
                "temperature_c": temp_c,
                "wind_speed_kmh": wind_kmh,
                "thermosensitive_mw": thermosensitive_mw,
                "gradient_mw_per_degree": thermosensitivity_gradient_mw
            },
            "model_champion": {
                "name": "Amazon Chronos-Bolt Small (Fine-Tuned)",
                "wape_pct": 8.87,
                "mae_mw": 509.58,
                "rmse_mw": 620.24,
                "gain_vs_baseline_pct": 39.3
            }
        }
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 3. ENDPOINT HISTORIQUE DE CONSOMMATION RÉELLE
# ==============================================================================

@app.get("/api/consumption/history", summary="Points historiques de consommation quart-horaire")
def get_consumption_history(
    hours: int = Query(default=48, ge=6, le=168),
    date: Optional[str] = Query(default=None, description="Date spécifique au format YYYY-MM-DD")
) -> Dict[str, Any]:
    """
    Renvoie les points observés de consommation nationale (RTE) au pas de 15 minutes.
    `date` : Date ciblée au format YYYY-MM-DD (prioritaire sur `hours`).
    `hours` : Nombre d'heures d'historique souhaité si aucune date n'est précisée.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        if date:
            cur.execute("""
                SELECT start_date, value_mw 
                FROM analytics.fct_national_consumption 
                WHERE start_date >= %s::timestamptz AND start_date < (%s::timestamptz + INTERVAL '1 day')
                ORDER BY start_date ASC;
            """, (date, date))
            rows = cur.fetchall()
            points = [
                {
                    "timestamp": r["start_date"].isoformat(),
                    "time_label": r["start_date"].strftime("%d/%m %H:%M"),
                    "value_mw": float(round(r["value_mw"], 1))
                }
                for r in rows
            ]
            return {
                "requested_date": date,
                "requested_hours": 24,
                "total_points": len(points),
                "data": points
            }

        total_points = hours * 4  # 4 quarts d'heure par heure
        cur.execute(f"""
            SELECT start_date, value_mw 
            FROM analytics.fct_national_consumption 
            ORDER BY start_date DESC 
            LIMIT {total_points};
        """)
        rows = cur.fetchall()

        # Inverser pour renvoyer dans l'ordre chronologique croissant
        rows.reverse()

        points = [
            {
                "timestamp": r["start_date"].isoformat(),
                "time_label": r["start_date"].strftime("%d/%m %H:%M"),
                "value_mw": float(round(r["value_mw"], 1))
            }
            for r in rows
        ]

        return {
            "requested_hours": hours,
            "total_points": len(points),
            "data": points
        }
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 4. ENDPOINT PRÉVISIONS DES MODÈLES (CHRONOS, LIGHTGBM, RTE D-1)
# ==============================================================================

@app.get("/api/consumption/forecasts", summary="Prévisions futures des modèles IA et RTE D-1")
def get_consumption_forecasts(date: Optional[str] = Query(default=None, description="Date au format YYYY-MM-DD")) -> Dict[str, Any]:
    """
    Renvoie les prévisions sur l'horizon de 24h :
    - Chronos-Bolt Fine-Tuned (Médiane q50, Borne basse q10, Borne haute q90)
    - Prévision officielle RTE J-1 (D-1)
    - Baseline Naïve (J-1 décalé)
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        target_day = date if date else "2026-09-24"

        # 1. Prévision officielle RTE D-1 pour ce jour-là
        cur.execute("""
            SELECT start_date, ROUND(AVG(value_mw)::numeric, 1) AS value_mw 
            FROM public.consumption_forecast 
            WHERE production_type = 'AGGREGATED_CPC' 
              AND forecast_type = 'D-1' 
              AND start_date >= %s::timestamptz AND start_date < (%s::timestamptz + INTERVAL '1 day')
            GROUP BY start_date 
            ORDER BY start_date ASC;
        """, (target_day, target_day))
        d1_rows = cur.fetchall()

        rte_d1_data = [
            {
                "timestamp": r["start_date"].isoformat(),
                "time_label": r["start_date"].strftime("%d/%m %H:%M"),
                "value_mw": float(r["value_mw"])
            }
            for r in d1_rows
        ]

        # 2. Baseline J-1 pour ce jour-là (consommation réelle de la veille décalée de 24h)
        cur.execute("""
            SELECT start_date + INTERVAL '1 day' AS target_date, value_mw 
            FROM analytics.fct_national_consumption 
            WHERE start_date >= (%s::timestamptz - INTERVAL '1 day') 
              AND start_date < %s::timestamptz 
            ORDER BY start_date ASC;
        """, (target_day, target_day))
        base_rows = cur.fetchall()

        baseline_data = [
            {
                "timestamp": r["target_date"].isoformat(),
                "time_label": r["target_date"].strftime("%d/%m %H:%M"),
                "value_mw": float(round(r["value_mw"], 1))
            }
            for r in base_rows
        ]

        # 3. Prévision Chronos-Bolt pour ce jour-là
        cur.execute("""
            SELECT target_date, forecast_mw, lower_bound_mw, upper_bound_mw, model_name 
            FROM public.model_forecasts 
            WHERE model_name = 'chronos-bolt-rte' 
              AND target_date >= %s::timestamptz AND target_date < (%s::timestamptz + INTERVAL '1 day')
            ORDER BY target_date ASC;
        """, (target_day, target_day))
        chronos_rows = cur.fetchall()

        chronos_data = [
            {
                "timestamp": r["target_date"].isoformat(),
                "time_label": r["target_date"].strftime("%d/%m %H:%M"),
                "forecast_mw": float(round(r["forecast_mw"], 1)),
                "lower_bound_mw": float(round(r["lower_bound_mw"], 1)),
                "upper_bound_mw": float(round(r["upper_bound_mw"], 1))
            }
            for r in chronos_rows
        ]

        return {
            "target_date": target_day,
            "chronos": chronos_data,
            "rte_d1": rte_d1_data,
            "baseline_j1": baseline_data
        }
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 5. ENDPOINT MÉRICES & BENCHMARK COMPARATIF
# ==============================================================================

@app.get("/api/benchmark", summary="Tableau comparatif officiel des performances modèles")
def get_benchmark_results() -> Dict[str, Any]:
    """
    Renvoie les métriques officielles consolidées du benchmark
    pour affichage dans le tableau d'évaluation du Front-End.
    """
    return {
        "models": [
            {
                "id": "naive",
                "name": "Baseline Naïve (J-7 / J-1)",
                "category": "Statistique Simple",
                "mae_mw": 838.84,
                "rmse_mw": 1167.61,
                "mape_pct": 15.96,
                "wape_pct": 14.60,
                "badge": "Référence",
                "badge_class": "badge-neutral"
            },
            {
                "id": "chronos_zeroshot",
                "name": "Chronos-Bolt Small (Zero-Shot)",
                "category": "Foundation Model Brut",
                "mae_mw": 542.10,
                "rmse_mw": 658.40,
                "mape_pct": 13.50,
                "wape_pct": 9.44,
                "badge": "Non Réentraîné",
                "badge_class": "badge-warning"
            },
            {
                "id": "chronos_finetuned",
                "name": "Chronos-Bolt Small (Fine-Tuned RTE)",
                "category": "Foundation Model Spécialisé",
                "mae_mw": 509.58,
                "rmse_mw": 620.24,
                "mape_pct": 13.08,
                "wape_pct": 8.87,
                "badge": "🏆 Champion",
                "badge_class": "badge-champion"
            },
            {
                "id": "lightgbm",
                "name": "LightGBM Multivarié (Météo + Lags)",
                "category": "Machine Learning Tabulaire",
                "mae_mw": 530.12,
                "rmse_mw": 648.70,
                "mape_pct": 13.25,
                "wape_pct": 9.23,
                "badge": "Explicable",
                "badge_class": "badge-info"
            }
        ]
    }


# ==============================================================================
# 6. MONTAGE STATIQUE DU FRONT-END (REACT PRODUCTION OU STATIC)
# ==============================================================================

DIST_DIR = FRONTEND_DIR / "dist"

# Si le bundle compilé React existe (frontend/dist), on le sert directement
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/", summary="Page d'accueil de l'interface éCO2mix React")
    def serve_frontend_index():
        """Sert l'application React compilée."""
        return FileResponse(DIST_DIR / "index.html")

elif FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", summary="Page d'accueil de l'interface éCO2mix")
    def serve_frontend_index():
        """Sert le fichier HTML statique."""
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"message": "Fichier frontend/index.html en cours de création."})
