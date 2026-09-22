"""
================================================================================
  MODULE : production/predict.py
  OBJECTIF : Service d'inférence en production pour la prévision de consommation
             électrique française (RTE).
================================================================================
"""

import sys
from datetime import timedelta
from typing import Tuple
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import torch
from psycopg2.extras import execute_values
from chronos import BaseChronosPipeline
from rte_energy.config import (
    get_db_connection,
    CHRONOS_MODEL_DIR,
    LATEST_FORECAST_PLOT
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Paramètres du service
FALLBACK_MODEL = "amazon/chronos-bolt-small"
CONTEXT_LENGTH = 512     # 5.3 jours d'historique en contexte
PREDICTION_HOURS = 24    # Horizon à prédire
PREDICTION_POINTS = PREDICTION_HOURS * 4  # 96 créneaux de 15 minutes


def load_recent_history(context_points: int = CONTEXT_LENGTH) -> pd.DataFrame:
    """
    Extrait les derniers points observés dans PostgreSQL.
    """
    conn = get_db_connection()
    try:
        query = f"""
            SELECT start_date, value_mw
            FROM analytics.fct_national_consumption
            ORDER BY start_date DESC
            LIMIT {context_points};
        """
        df = pd.read_sql_query(query, conn)
        if df.empty:
            raise ValueError("Table analytics.fct_national_consumption vide.")
    except Exception:
        query = f"""
            SELECT start_date, ROUND(AVG(value_mw)::numeric, 2) AS value_mw
            FROM consumption_forecast
            WHERE production_type = 'AGGREGATED_CPC' AND forecast_type = 'D-1'
            GROUP BY start_date
            ORDER BY start_date DESC
            LIMIT {context_points};
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    if df.empty:
        raise RuntimeError("Aucune donnée historique de consommation trouvée dans PostgreSQL.")

    df["start_date"] = pd.to_datetime(df["start_date"])
    df.sort_values("start_date", inplace=True)
    df.set_index("start_date", inplace=True)
    return df


def run_model_inference(
    history_series: pd.Series,
    prediction_points: int = PREDICTION_POINTS
) -> Tuple[str, pd.DatetimeIndex, np.ndarray, np.ndarray, np.ndarray]:
    """
    Exécute l'inférence avec Chronos-Bolt (Fine-Tuned ou Zero-Shot).
    """
    if CHRONOS_MODEL_DIR.exists():
        model_source = str(CHRONOS_MODEL_DIR)
        model_label = "chronos-bolt-rte"
        print(f"📦 Utilisation du modèle Champion Fine-Tuned : {model_source}")
    else:
        model_source = FALLBACK_MODEL
        model_label = "chronos-bolt-small-zeroshot"
        print(f"⚠️ Modèle local non trouvé, repli sur : {FALLBACK_MODEL}")

    pipeline = BaseChronosPipeline.from_pretrained(
        model_source,
        device_map="cpu"
    )

    context_tensor = torch.tensor(history_series.values, dtype=torch.float32)

    last_date = history_series.index[-1]
    future_dates = pd.date_range(
        start=last_date + timedelta(minutes=15),
        periods=prediction_points,
        freq="15min"
    )

    print(f"🔮 Inférence en cours sur {prediction_points} pas de 15 min (du {future_dates[0]} au {future_dates[-1]})...")
    forecast = pipeline.predict(context_tensor, prediction_length=prediction_points)
    quantiles = forecast[0].numpy()

    median_pred = quantiles[4]
    lower_pred = quantiles[0]
    upper_pred = quantiles[8]

    return model_label, future_dates, median_pred, lower_pred, upper_pred


def save_forecasts_to_db(
    model_name: str,
    future_dates: pd.DatetimeIndex,
    median_pred: np.ndarray,
    lower_pred: np.ndarray,
    upper_pred: np.ndarray
) -> int:
    """
    Insère ou met à jour les prévisions dans 'model_forecasts'.
    """
    rows = []
    for dt, med, low, upp in zip(future_dates, median_pred, lower_pred, upper_pred):
        rows.append((
            dt.to_pydatetime(),
            float(round(med, 2)),
            float(round(low, 2)),
            float(round(upp, 2)),
            model_name
        ))

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO model_forecasts (target_date, forecast_mw, lower_bound_mw, upper_bound_mw, model_name)
        VALUES %s
        ON CONFLICT (model_name, target_date)
        DO UPDATE SET
            forecast_mw = EXCLUDED.forecast_mw,
            lower_bound_mw = EXCLUDED.lower_bound_mw,
            upper_bound_mw = EXCLUDED.upper_bound_mw,
            created_at = NOW();
    """
    execute_values(cur, query, rows)
    conn.commit()
    cur.close()
    conn.close()

    return len(rows)


def plot_latest_forecast(
    recent_history: pd.DataFrame,
    future_dates: pd.DatetimeIndex,
    median_pred: np.ndarray,
    lower_pred: np.ndarray,
    upper_pred: np.ndarray,
    model_name: str
) -> None:
    """
    Génère un graphique raccordant historique récent et prévision future.
    """
    plt.figure(figsize=(14, 7))

    recent_tail = recent_history.iloc[-96:]
    plt.plot(
        recent_tail.index,
        recent_tail["value_mw"].values,
        label="Historique Récent (RTE)",
        color="#0f172a",
        linewidth=2.2
    )

    plt.plot(
        future_dates,
        median_pred,
        label=f"Prévision IA ({model_name})",
        color="#2563eb",
        linewidth=2.5,
        linestyle="--"
    )

    plt.fill_between(
        future_dates,
        lower_pred,
        upper_pred,
        color="#3b82f6",
        alpha=0.2,
        label="Intervalle d'incertitude 80% (q10 - q90)"
    )

    plt.axvline(
        x=recent_tail.index[-1],
        color="#ef4444",
        linestyle=":",
        linewidth=1.8,
        label="Instant Présent"
    )

    plt.title("⚡ PRÉVISION DE CONSOMMATION ÉLECTRIQUE EN PRODUCTION (J+1)", fontsize=13, fontweight="bold")
    plt.xlabel("Date et Heure", fontsize=11)
    plt.ylabel("Puissance (MW)", fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right", fontsize=10, framealpha=0.95)
    plt.xticks(rotation=20)
    plt.tight_layout()

    LATEST_FORECAST_PLOT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(LATEST_FORECAST_PLOT, dpi=150)
    plt.close()
    print(f"📊 Graphique de prévision sauvegardé dans : {LATEST_FORECAST_PLOT}")


def generate_and_save_forecasts() -> None:
    """
    Point d'entrée du service d'inférence en production.
    """
    print("=" * 80)
    print("  ⚡ DÉMARRAGE DU SERVICE D'INFÉRENCE EN PRODUCTION (CHRONOS-BOLT)")
    print("=" * 80)

    print(f"⏳ 1/4 Récupération des {CONTEXT_LENGTH} derniers points d'historique en base...")
    df_history = load_recent_history(CONTEXT_LENGTH)
    print(f"   • Plage : du {df_history.index.min()} au {df_history.index.max()} ({len(df_history)} points)")

    print(f"\n⏳ 2/4 Calcul des prévisions à J+1 ({PREDICTION_HOURS}h)...")
    model_name, future_dates, median_pred, lower_pred, upper_pred = run_model_inference(
        df_history["value_mw"],
        PREDICTION_POINTS
    )

    print(f"\n⏳ 3/4 Sauvegarde des prévisions dans PostgreSQL ('model_forecasts')...")
    nb_saved = save_forecasts_to_db(model_name, future_dates, median_pred, lower_pred, upper_pred)
    print(f"   ✅ {nb_saved} points de prévision enregistrés avec succès !")

    print(f"\n⏳ 4/4 Génération du graphique récapitulatif...")
    plot_latest_forecast(
        df_history,
        future_dates,
        median_pred,
        lower_pred,
        upper_pred,
        model_name
    )

    print("\n" + "=" * 80)
    print("  🎉 SERVICE D'INFÉRENCE TERMINÉ AVEC SUCCÈS !")
    print("=" * 80)


if __name__ == "__main__":
    generate_and_save_forecasts()
