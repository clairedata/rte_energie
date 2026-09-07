import os
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# 1. Chargement des paramètres de connexion à PostgreSQL
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "energy_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD")
}

def load_data() -> pd.DataFrame:
    """
    Étape 1 : Récupération de la série temporelle propre de consommation (AGGREGATED_CPC D-1).
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

def train_test_split_temporal(df: pd.DataFrame, test_points: int = 96):
    """
    Étape 2 : Découpage chronologique strict (sans mélanger !).
    - test_points = 96 points (soit 24 heures de prévision au pas de 15 minutes : 24 x 4 = 96).
    - Train : tout l'historique précédent.
    - Test  : les 24 dernières heures que l'on veut prédire.
    """
    train_df = df.iloc[:-test_points]  # Tout sauf les 96 derniers
    test_df = df.iloc[-test_points:]   # Uniquement les 96 derniers
    return train_df, test_df

def seasonal_naive_predict(train_df: pd.DataFrame, test_points: int = 96) -> np.ndarray:
    """
    Étape 3 : Le Modèle Naïf Saisonnier (Baseline).
    Règle simple : la prédiction pour aujourd'hui est exactement égale
    aux valeurs constatées hier à la même heure (cycle de 24 heures = 96 quarts d'heure).
    """
    # On prend simplement les 96 derniers points connus du jeu d'entraînement (la veille)
    predictions = train_df["value_mw"].iloc[-test_points:].values
    return predictions

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Étape 4 : Calcul des 4 métriques de référence.
    """
    # Erreur absolue pour chaque quart d'heure
    errors = np.abs(y_true - y_pred)
    
    # 1. MAE : Moyenne des erreurs en Mégawatts (MW)
    mae = np.mean(errors)
    
    # 2. RMSE : Racine carrée de la moyenne des erreurs au carré (pénalise les grosses erreurs)
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    # 3. MAPE : Pourcentage d'erreur moyen relatif (%)
    mape = np.mean(errors / y_true) * 100
    
    # 4. WAPE : Erreur pondérée sur la somme totale (%)
    wape = (np.sum(errors) / np.sum(y_true)) * 100
    
    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "WAPE": wape
    }

def plot_baseline_results(test_df: pd.DataFrame, y_pred: np.ndarray, metrics: dict):
    """
    Étape 5 : Visualisation graphique de la vraie courbe vs la Baseline.
    """
    plt.figure(figsize=(14, 6))
    
    # Courbe réelle
    plt.plot(test_df.index, test_df["value_mw"], label="Consommation Réelle (Test)", color="black", linewidth=2.5)
    
    # Prédiction du modèle naïf
    plt.plot(test_df.index, y_pred, label="Baseline Naïve (J-1 répété)", color="#e74c3c", linestyle="--", linewidth=2)
    
    title = f"Baseline Naïve Saisonnier (24h) | MAE: {metrics['MAE']:.1f} MW | MAPE: {metrics['MAPE']:.2f}% | WAPE: {metrics['WAPE']:.2f}%"
    plt.title(title, fontsize=13, fontweight="bold")
    plt.xlabel("Date et Heure", fontsize=11)
    plt.ylabel("Consommation (MW)", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(fontsize=11)
    plt.tight_layout()
    
    output_image = "baseline_evaluation.png"
    plt.savefig(output_image, dpi=300)
    plt.close()
    print(f"📊 Graphique comparatif sauvegardé dans : backend/{output_image}")

def run_baseline():
    print("==================================================")
    print("  🎯 ÉTAPE 2 : ÉVALUATION DE LA BASELINE NAÏVE    ")
    print("==================================================")
    
    # 1. Charger les données
    df = load_data()
    print(f"Total points disponibles en base : {len(df)}")
    
    # 2. Découpage temporel
    test_horizon = 96  # 24 heures = 96 points de 15 minutes
    train_df, test_df = train_test_split_temporal(df, test_points=test_horizon)
    print(f"Jeu d'entraînement (Train / Passé) : {len(train_df)} points")
    print(f"Jeu de test (Test / Futur à évaluer): {len(test_df)} points ({test_df.index.min()} -> {test_df.index.max()})")
    
    # 3. Prédiction avec la Baseline naïve
    y_true = test_df["value_mw"].values
    y_pred = seasonal_naive_predict(train_df, test_points=test_horizon)
    
    # 4. Calcul des scores
    metrics = compute_metrics(y_true, y_pred)
    
    print("\n--------------------------------------------------")
    print("  🏆 SCORES OFFICIELS DE LA BASELINE (À BATTRE)   ")
    print("--------------------------------------------------")
    print(f"  MAE  : {metrics['MAE']:.2f} MW   (Erreur moyenne en valeur absolue)")
    print(f"  RMSE : {metrics['RMSE']:.2f} MW   (Pénalité sur les gros écarts)")
    print(f"  MAPE : {metrics['MAPE']:.2f} %    (Marge d'erreur en pourcentage)")
    print(f"  WAPE : {metrics['WAPE']:.2f} %    (Erreur globale pondérée)")
    print("--------------------------------------------------\n")
    print("👉 Ce sont les scores de référence. Tout modèle futur d'IA devra faire MIEUX !")

    # 5. Tracer et sauvegarder le graphique
    plot_baseline_results(test_df, y_pred, metrics)

if __name__ == "__main__":
    run_baseline()
