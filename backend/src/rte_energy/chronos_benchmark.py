"""
================================================================================
  MODULE : chronos_benchmark.py
  OBJECTIF : Benchmark comparatif final à 3 voies :
             1. Baseline Naïve (J-7)
             2. Amazon Chronos-Bolt Small (Zero-Shot)
             3. Amazon Chronos-Bolt Small (Fine-Tuned sur RTE)
================================================================================
Ce script réalise les opérations suivantes :
1. Chargement de la série historique et isolation du jeu de Test final (non vu à l'entraînement).
2. Calcul des prédictions de la Baseline Naïve (consommation du même jour de la semaine précédente).
3. Génération des prédictions Zero-Shot avec le modèle générique pré-entraîné.
4. Génération des prédictions Fine-Tuned avec votre modèle adapté au réseau RTE.
5. Calcul des métriques d'évaluation clés :
   - MAE  (Erreur Absolue Moyenne en MW)
   - RMSE (Racine de l'Erreur Quadratique Moyenne en MW)
   - MAPE (Erreur Pourcentage Moyenne en %)
   - WAPE (Erreur Absolue Pondérée en %)
6. Affichage d'un tableau comparatif clair et synthèse des gains obtenus.
7. Sauvegarde d'un graphique haute résolution superposant les 3 prédictions
   face aux valeurs réelles (backend/benchmark_3_way.png).
"""

import os
from pathlib import Path
from typing import Tuple, Dict
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import torch
from dotenv import load_dotenv
from chronos import BaseChronosPipeline

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "energy_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD")
}

# Modèle original (Zero-Shot) et modèle réentraîné (Fine-Tuned)
BASE_MODEL_NAME = "amazon/chronos-bolt-small"
FINETUNED_DIR = Path(__file__).resolve().parents[2] / "models" / "chronos-bolt-rte"
BENCHMARK_PLOT = Path(__file__).resolve().parents[2] / "benchmark_3_way.png"

# Horizon d'évaluation : 64 quarts d'heure (16 heures = horizon natif optimal)
PREDICTION_LENGTH = 64


# ==============================================================================
# 2. CHARGEMENT DE LA SÉRIE HISTORIQUE
# ==============================================================================
def load_data() -> pd.DataFrame:
    """
    Récupère la série temporelle unifiée de consommation (AGGREGATED_CPC D-1).
    """
    conn = psycopg2.connect(**DB_CONFIG)
    query = """
        SELECT 
            start_date,
            AVG(value_mw) AS value_mw
        FROM consumption_forecast
        WHERE production_type = 'AGGREGATED_CPC'
          AND forecast_type = 'D-1'
        GROUP BY start_date
        ORDER BY start_date ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["start_date"] = pd.to_datetime(df["start_date"])
    df.set_index("start_date", inplace=True)
    return df


# ==============================================================================
# 3. CALCUL DES MÉTRIQUES D'ÉVALUATION
# ==============================================================================
def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calcule les 4 métriques de référence :
    - MAE  : Erreur moyenne en valeur absolue (MW)
    - RMSE : Pénalise fortement les grands écarts (MW)
    - MAPE : Pourcentage d'erreur moyen (%)
    - WAPE : Erreur absolue totale rapportée à la consommation totale (%)
    """
    errors = np.abs(y_true - y_pred)
    mae = float(np.mean(errors))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mape = float(np.mean(errors / y_true) * 100)
    wape = float((np.sum(errors) / np.sum(y_true)) * 100)

    return {"MAE": mae, "RMSE": rmse, "MAPE": mape, "WAPE": wape}


# ==============================================================================
# 4. INFÉRENCE MODÈLE 1 : BASELINE NAÏVE (J-7)
# ==============================================================================
def predict_naive_baseline(full_df: pd.DataFrame, test_index: pd.DatetimeIndex) -> np.ndarray:
    """
    Prédit la consommation en reprenant exactement la valeur observée 7 jours plus tôt (J-7).
    """
    naive_preds = []
    for target_time in test_index:
        same_time_last_week = target_time - pd.Timedelta(days=7)
        if same_time_last_week in full_df.index:
            naive_preds.append(full_df.loc[same_time_last_week, "value_mw"])
        else:
            # Repli sur la moyenne globale si J-7 manquant
            naive_preds.append(full_df["value_mw"].mean())
    return np.array(naive_preds)


# ==============================================================================
# 5. INFÉRENCE MODÈLE 2 : AMAZON CHRONOS-BOLT ZERO-SHOT
# ==============================================================================
def predict_chronos_zero_shot(context_tensor: torch.Tensor, prediction_length: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Génère les prévisions du modèle générique pré-entraîné (non fine-tuné).
    """
    print(f"⏳ Inférence Zero-Shot ({BASE_MODEL_NAME})...")
    pipeline = BaseChronosPipeline.from_pretrained(
        BASE_MODEL_NAME,
        device_map="cpu"
    )
    forecast = pipeline.predict(context_tensor, prediction_length=prediction_length)
    quantiles = forecast[0].numpy()
    
    # Médiane (indice 4), borne basse 10% (indice 0), borne haute 90% (indice 8)
    return quantiles[4], quantiles[0], quantiles[8]


# ==============================================================================
# 6. INFÉRENCE MODÈLE 3 : AMAZON CHRONOS-BOLT FINE-TUNED (RTE)
# ==============================================================================
def predict_chronos_finetuned(context_tensor: torch.Tensor, prediction_length: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Génère les prévisions du modèle adapté à vos données locales (Fine-Tuned).
    """
    if not FINETUNED_DIR.exists():
        raise FileNotFoundError(
            f"Le dossier du modèle fine-tuné '{FINETUNED_DIR}' n'existe pas encore.\n"
            f"Veuillez exécuter d'abord l'Étape 2 : 'uv run .\\chronos_finetune.py'"
        )

    print(f"⏳ Inférence Fine-Tuned (depuis {FINETUNED_DIR})...")
    pipeline = BaseChronosPipeline.from_pretrained(
        str(FINETUNED_DIR),
        device_map="cpu"
    )
    forecast = pipeline.predict(context_tensor, prediction_length=prediction_length)
    quantiles = forecast[0].numpy()
    
    return quantiles[4], quantiles[0], quantiles[8]


# ==============================================================================
# 7. TRACÉ COMPARATIF HAUTE RÉSOLUTION
# ==============================================================================
def plot_benchmark(
    test_dates: pd.DatetimeIndex,
    y_true: np.ndarray,
    y_naive: np.ndarray,
    y_zero_shot: np.ndarray,
    y_finetuned: np.ndarray,
    low_ft: np.ndarray,
    high_ft: np.ndarray,
    save_path: Path
):
    """
    Superpose les courbes réelles et les 3 prédictions avec intervalle de confiance à 80%.
    """
    plt.figure(figsize=(15, 8))
    
    # 1. Consommation réelle
    plt.plot(test_dates, y_true, label="Réalité (RTE Consommation)", color="#0f172a", linewidth=2.5, zorder=5)
    
    # 2. Baseline Naïve (J-7)
    plt.plot(test_dates, y_naive, label="Baseline Naïve (J-7)", color="#ef4444", linestyle=":", linewidth=1.8, alpha=0.8)
    
    # 3. Chronos-Bolt Zero-Shot
    plt.plot(test_dates, y_zero_shot, label="Chronos-Bolt (Zero-Shot)", color="#f59e0b", linestyle="--", linewidth=2, alpha=0.85)
    
    # 4. Chronos-Bolt Fine-Tuned
    plt.plot(test_dates, y_finetuned, label="Chronos-Bolt (Fine-Tuned RTE)", color="#2563eb", linewidth=2.5)
    
    # Intervalle de confiance à 80% du modèle Fine-Tuned
    plt.fill_between(
        test_dates,
        low_ft,
        high_ft,
        color="#3b82f6",
        alpha=0.18,
        label="Intervalle de confiance 80% (Fine-Tuned)"
    )

    plt.title(
        "🏆 BENCHMARK COMPARATIF : Baseline Naïve vs Chronos Zero-Shot vs Chronos Fine-Tuned",
        fontsize=14,
        fontweight="bold"
    )
    plt.xlabel("Date et Heure", fontsize=11)
    plt.ylabel("Consommation Électrique (MW)", fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right", fontsize=10, framealpha=0.95)
    plt.xticks(rotation=20)
    plt.tight_layout()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"📊 Graphique du Benchmark sauvegardé dans : {save_path}")


# ==============================================================================
# 8. EXÉCUTION DU BENCHMARK COMPARATIF
# ==============================================================================
def main():
    print("=" * 85)
    print("  🏆 ÉTAPE 3 : BENCHMARK COMPARATIF (NAÏVE vs ZERO-SHOT vs FINE-TUNED)")
    print("=" * 85)

    # 1. Chargement des données
    df = load_data()
    print(f"Total de points historiques disponibles : {len(df)}")

    # 2. Découpage strict Train / Test
    # On évalue sur les 'PREDICTION_LENGTH' derniers points
    train_df = df.iloc[:-PREDICTION_LENGTH]
    test_df = df.iloc[-PREDICTION_LENGTH:]

    test_dates = test_df.index
    y_true = test_df["value_mw"].values
    context_tensor = torch.tensor(train_df["value_mw"].values, dtype=torch.float32)

    print(f"Période de test évaluée : {len(test_df)} points ({test_dates.min()} -> {test_dates.max()})")
    print()

    # 3. Calcul des 3 prédictions
    # A. Baseline
    y_naive = predict_naive_baseline(df, test_dates)

    # B. Zero-Shot
    y_zero_shot, low_zs, high_zs = predict_chronos_zero_shot(context_tensor, PREDICTION_LENGTH)

    # C. Fine-Tuned
    y_finetuned, low_ft, high_ft = predict_chronos_finetuned(context_tensor, PREDICTION_LENGTH)

    # 4. Calcul des métriques
    m_naive = compute_metrics(y_true, y_naive)
    m_zs = compute_metrics(y_true, y_zero_shot)
    m_ft = compute_metrics(y_true, y_finetuned)

    # 5. Affichage du tableau de résultats
    print("\n" + "=" * 85)
    print("  📊 TABLEAU COMPARATIF DES PERFORMANCES")
    print("=" * 85)
    header = f"{'Métrique':<8} | {'1. Naïve (J-7)':<15} | {'2. Zero-Shot':<15} | {'3. Fine-Tuned':<15} | {'Gain vs Zero-Shot':<20}"
    print(header)
    print("-" * 85)

    for metric in ["MAE", "RMSE", "MAPE", "WAPE"]:
        v_naive = m_naive[metric]
        v_zs = m_zs[metric]
        v_ft = m_ft[metric]
        
        diff = v_ft - v_zs
        pct = (diff / v_zs) * 100
        unit = "MW" if metric in ["MAE", "RMSE"] else "%"
        
        badge = "✅ Amélioration" if diff < 0 else "➡️ Stable"
        print(f"{metric:<8} | {v_naive:>11.2f} {unit:<3} | {v_zs:>11.2f} {unit:<3} | {v_ft:>11.2f} {unit:<3} | {diff:>+8.2f} ({pct:>+5.1f}%) {badge}")

    print("=" * 85)

    # 6. Tracé graphique
    plot_benchmark(test_dates, y_true, y_naive, y_zero_shot, y_finetuned, low_ft, high_ft, BENCHMARK_PLOT)

    print("\n" + "=" * 85)
    print("  🎉 BENCHMARK TERMINÉ AVEC SUCCÈS !")
    print("=" * 85)


if __name__ == "__main__":
    main()
