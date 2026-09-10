import os
import sys
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import torch
from dotenv import load_dotenv
from chronos import BaseChronosPipeline

# ==============================================================================
# 1. CHARGEMENT DE LA CONFIGURATION
# ==============================================================================
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "energy_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD")
}

# ==============================================================================
# 2. RÉCUPÉRATION DES DONNÉES (MÊME REQUÊTE QUE POUR LA BASELINE)
# ==============================================================================
def load_data() -> pd.DataFrame:
    """
    Extrait la série temporelle unifiée de consommation électrique (AGGREGATED_CPC D-1).
    Chaque ligne correspond à la moyenne des révisions pour un quart d'heure donné.
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
# 3. DÉCOUPAGE TEMPOREL STRICT (TRAIN / TEST)
# ==============================================================================
def train_test_split_temporal(df: pd.DataFrame, test_points: int = 96):
    """
     Découpage chronologique strict :
    - test_points = 96 = 24 heures.
    - train_df = tous les points sauf les 96 derniers.
    - test_df = les 96 derniers points.
    """
    train_df = df.iloc[:-test_points]
    test_df = df.iloc[-test_points:]
    return train_df, test_df

# ==============================================================================
# 4. INFÉRENCE AVEC LE MODÈLE AMAZON CHRONOS-BOLT (ZERO-SHOT)
# ==============================================================================
def predict_with_chronos_bolt(train_df: pd.DataFrame, prediction_length: int = 96, model_name: str = "amazon/chronos-bolt-small"):
    """
    Utilise la nouvelle génération de modèles : Amazon Chronos-Bolt.
    
    Pourquoi Bolt ?
    - Contrairement au Chronos standard (autorégressif point par point),
      Chronos-Bolt utilise une architecture 'patchée' directe (non autorégressive).
    - Il génère directement tous les quantiles futurs en une seule passe ultra-rapide.
    - Il est jusqu'à 250 fois plus rapide et conserve une excellente précision
      sur les horizons de prédiction moyens à longs.
      
    Quantiles générés nativement :
    [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    - Index 4 = 0.5 (Médiane = prédiction centrale robuste)
    - Index 0 = 0.1 (Borne basse de l'intervalle à 80%)
    - Index 8 = 0.9 (Borne haute de l'intervalle à 80%)
    """
    print(f"\n⏳ Chargement du modèle Amazon Chronos-Bolt ({model_name})...")
    
    # 1. Préparation du tenseur d'entrée
    context = torch.tensor(train_df["value_mw"].values, dtype=torch.float32)

    # 2. Chargement du pipeline Chronos-Bolt optimisé CPU
    pipeline = BaseChronosPipeline.from_pretrained(
        model_name,
        device_map="cpu"
    )

    print("==========================================")
    print("CONFIGURATION CHRONOS-BOLT")
    print("==========================================")

    print("Context length :", pipeline.model_context_length)
    print("Prediction length :", pipeline.model_prediction_length)
    print("Quantiles :", pipeline.quantiles)

    print("Chronos config :")
    print(pipeline.model.config.chronos_config)

    print(f"🤖 Inférence directe en cours sur un horizon de {prediction_length} pas de 15 minutes...")
    
    # 3. Prédiction directe des 9 quantiles futurs
    # forecast shape : (batch_size=1, 9 quantiles, prediction_length=96)
    forecast = pipeline.predict(
        context,
        prediction_length=prediction_length
    )

    quantiles = forecast[0].numpy()  # shape (9, 96)
    
    # Médiane (50e percentile)
    median_pred = quantiles[4]
    
    # Bornes 10% et 90% pour l'intervalle de confiance
    low_pred = quantiles[0]
    high_pred = quantiles[8]

    return median_pred, low_pred, high_pred

# ==============================================================================
# 5. CALCUL DES MÉTRIQUES D'ÉVALUATION (MAE, RMSE, MAPE, WAPE)
# ==============================================================================
def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Calcule les 4 métriques de référence :
    - MAE  : Erreur absolue moyenne (en MW)
    - RMSE : Racine carrée de l'erreur quadratique moyenne (pénalise les fortes erreurs en MW)
    - MAPE : Erreur moyenne en pourcentage (%)
    - WAPE : Erreur pondérée sur le volume global (%)
    """
    errors = np.abs(y_true - y_pred)
    mae = np.mean(errors)
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mape = np.mean(errors / y_true) * 100
    wape = (np.sum(errors) / np.sum(y_true)) * 100

    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "WAPE": wape
    }

# ==============================================================================
# 6. VISUALISATION GRAPHIQUE COMPARATIVE (3 COURBES)
# ==============================================================================
def plot_comparison(test_df: pd.DataFrame, 
                    y_baseline: np.ndarray, 
                    y_chronos: np.ndarray, 
                    low_pred: np.ndarray, 
                    high_pred: np.ndarray, 
                    metrics_base: dict, 
                    metrics_chronos: dict):
    """
    Génère un graphique comparatif sauvegardé dans backend/chronos_evaluation.png :
    - Courbe noire : Réalité observée
    - Courbe rouge pointillée : Baseline naïve saisonnière (J-1)
    - Courbe verte : Prédiction Amazon Chronos-Bolt
    - Zone ombrée verte : Intervalle de confiance (10% - 90%)
    """
    plt.figure(figsize=(14, 7))

    dates = test_df.index
    y_true = test_df["value_mw"].values

    # 1. Vraie consommation
    plt.plot(dates, y_true, label="Consommation Réelle (Observée)", color="black", linewidth=2.5)

    # 2. Baseline Naïve (J-1)
    plt.plot(dates, y_baseline, label=f"Baseline Naïve (MAE: {metrics_base['MAE']:.1f} MW, MAPE: {metrics_base['MAPE']:.1f}%)",
             color="#e74c3c", linestyle="--", linewidth=1.8)

    # 3. Modèle Amazon Chronos-Bolt
    plt.plot(dates, y_chronos, label=f"Amazon Chronos-Bolt Small (MAE: {metrics_chronos['MAE']:.1f} MW, MAPE: {metrics_chronos['MAPE']:.1f}%)",
             color="#2ecc71", linewidth=2.4)

    # 4. Zone d'incertitude Chronos (Percentiles 10% - 90%)
    plt.fill_between(dates, low_pred, high_pred, color="#2ecc71", alpha=0.2, label="Intervalle de confiance Chronos-Bolt (10%-90%)")

    # Mise en forme du graphique
    plt.title("Victoire de l'IA : Réalité vs Baseline Naïve vs Amazon Chronos-Bolt Small (24h)", fontsize=14, fontweight="bold")
    plt.xlabel("Date et Heure", fontsize=11)
    plt.ylabel("Consommation (Mégawatts - MW)", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper left", fontsize=10)
    plt.tight_layout()

    output_file = "chronos_evaluation.png"
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"📊 Graphique comparatif sauvegardé dans : backend/{output_file}")

# ==============================================================================
# 7. FONCTION PRINCIPALE (BENCHMARK)
# ==============================================================================
def run_benchmark():
    print("================================================================================")
    print("  🚀 ÉTAPE 3 : BENCHMARK AMAZON CHRONOS-BOLT (TSFM) vs BASELINE NAÏVE           ")
    print("================================================================================")

    # 1. Chargement des données
    df = load_data()
    print(f"Total de points historiques disponibles : {len(df)}")

    # 2. Découpage temporel
    test_horizon = 96
    train_df, test_df = train_test_split_temporal(df, test_points=test_horizon)
    print(f"Période historique d'entraînement : {len(train_df)} points ({train_df.index.min()} -> {train_df.index.max()})")
    print(f"Période de test à prédire         : {len(test_df)} points ({test_df.index.min()} -> {test_df.index.max()})")

    y_true = test_df["value_mw"].values

    # 3. Prédiction Baseline Naïve (J-1)
    y_baseline = train_df["value_mw"].iloc[-test_horizon:].values
    metrics_base = compute_metrics(y_true, y_baseline)

    # 4. Prédiction Amazon Chronos-Bolt (Small)
    y_chronos, low_pred, high_pred = predict_with_chronos_bolt(
        train_df, 
        prediction_length=test_horizon,
        model_name="amazon/chronos-bolt-small"
    )
    metrics_chronos = compute_metrics(y_true, y_chronos)

    # 5. Affichage du tableau comparatif
    def format_diff(val_chronos, val_base, is_percent=False):
        diff = val_chronos - val_base
        percent_change = (diff / val_base) * 100
        sign = "+" if diff > 0 else ""
        if diff < 0:
            status = "✅ GAGNÉ (Amélioration !)"
        else:
            status = "❌ EN RETRAIT"
        unit = "%" if is_percent else "MW"
        return f"{sign}{diff:.2f} {unit} ({sign}{percent_change:.1f}%) -> {status}"

    print("\n" + "=" * 80)
    print("  🏆 RÉSULTATS DU MATCH : BASELINE NAÏVE vs AMAZON CHRONOS-BOLT SMALL          ")
    print("=" * 80)
    print(f"{'Métrique':<10} | {'Baseline Naïve':<18} | {'Chronos-Bolt Small':<18} | {'Comparaison (Évolution)':<30}")
    print("-" * 80)
    print(f"{'MAE':<10} | {metrics_base['MAE']:>12.2f} MW     | {metrics_chronos['MAE']:>12.2f} MW     | {format_diff(metrics_chronos['MAE'], metrics_base['MAE'])}")
    print(f"{'RMSE':<10} | {metrics_base['RMSE']:>12.2f} MW     | {metrics_chronos['RMSE']:>12.2f} MW     | {format_diff(metrics_chronos['RMSE'], metrics_base['RMSE'])}")
    print(f"{'MAPE':<10} | {metrics_base['MAPE']:>14.2f} %     | {metrics_chronos['MAPE']:>14.2f} %     | {format_diff(metrics_chronos['MAPE'], metrics_base['MAPE'], is_percent=True)}")
    print(f"{'WAPE':<10} | {metrics_base['WAPE']:>14.2f} %     | {metrics_chronos['WAPE']:>14.2f} %     | {format_diff(metrics_chronos['WAPE'], metrics_base['WAPE'], is_percent=True)}")
    print("=" * 80 + "\n")

    # 6. Tracé graphique
    plot_comparison(test_df, y_baseline, y_chronos, low_pred, high_pred, metrics_base, metrics_chronos)

if __name__ == "__main__":
    run_benchmark()
