"""
================================================================================
  MODULE : training/baseline.py
  OBJECTIF : Modèle de référence (Baseline Naïve Saisonnière J-1) et métriques.
================================================================================
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from rte_energy.config import get_db_connection, FIGURES_DIR

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_data() -> pd.DataFrame:
    """
    Extrait la série temporelle unifiée de consommation depuis dbt.
    """
    conn = get_db_connection()
    query = """
        SELECT start_date, value_mw 
        FROM analytics.fct_national_consumption 
        ORDER BY start_date ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["start_date"] = pd.to_datetime(df["start_date"])
    df.set_index("start_date", inplace=True)
    return df


def train_test_split_temporal(df: pd.DataFrame, test_points: int = 96):
    """
    Découpage chronologique strict : 96 points de test (24h).
    """
    train_df = df.iloc[:-test_points]
    test_df = df.iloc[-test_points:]
    return train_df, test_df


def seasonal_naive_predict(train_df: pd.DataFrame, test_points: int = 96) -> np.ndarray:
    """
    Modèle Naïf Saisonnier : la prévision d'aujourd'hui est la consommation d'hier.
    """
    return train_df["value_mw"].iloc[-test_points:].values


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Calcule les 4 métriques de référence : MAE, RMSE, MAPE, WAPE.
    """
    errors = np.abs(y_true - y_pred)
    mae = float(np.mean(errors))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mape = float(np.mean(errors / y_true) * 100)
    wape = float((np.sum(errors) / np.sum(y_true)) * 100)
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape, "WAPE": wape}


def plot_baseline_results(test_df: pd.DataFrame, y_pred: np.ndarray, metrics: dict):
    """
    Trace le graphique comparatif Réel vs Baseline Naïve.
    """
    plt.figure(figsize=(14, 6))
    plt.plot(test_df.index, test_df["value_mw"], label="Consommation Réelle (Test)", color="black", linewidth=2.5)
    plt.plot(test_df.index, y_pred, label="Baseline Naïve (J-1 répété)", color="#e74c3c", linestyle="--", linewidth=2)

    title = f"Baseline Naïve Saisonnier (24h) | MAE: {metrics['MAE']:.1f} MW | MAPE: {metrics['MAPE']:.2f}% | WAPE: {metrics['WAPE']:.2f}%"
    plt.title(title, fontsize=13, fontweight="bold")
    plt.xlabel("Date et Heure", fontsize=11)
    plt.ylabel("Puissance (MW)", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    output_image = FIGURES_DIR / "baseline_evaluation.png"
    plt.savefig(output_image, dpi=150)
    plt.close()
    print(f"✅ Graphique Baseline sauvegardé dans : {output_image}")


def main():
    print("=" * 60)
    print("   ÉVALUATION DU MODÈLE DE RÉFÉRENCE (BASELINE NAÏVE) ")
    print("=" * 60)

    df = load_data()
    print(f"Total de points historiques disponibles : {len(df)}")

    train_df, test_df = train_test_split_temporal(df, test_points=96)
    print(f"Jeu d'entraînement (Train) : {len(train_df)} quarts d'heure")
    print(f"Jeu de test (Test 24h)      : {len(test_df)} quarts d'heure ({test_df.index.min()} -> {test_df.index.max()})")

    y_pred = seasonal_naive_predict(train_df, test_points=96)
    metrics = compute_metrics(test_df["value_mw"].values, y_pred)

    print("\n" + "=" * 60)
    print("   MÉTRIQUES DE PERFORMANCE (BASELINE NAÏVE)")
    print("=" * 60)
    print(f"MAE  (Erreur Absolue Moyenne) : {metrics['MAE']:.2f} MW")
    print(f"RMSE (Erreur Quadratique)     : {metrics['RMSE']:.2f} MW")
    print(f"MAPE (Erreur Relative)        : {metrics['MAPE']:.2f} %")
    print(f"WAPE (Erreur Pondérée)        : {metrics['WAPE']:.2f} %")
    print("=" * 60 + "\n")

    plot_baseline_results(test_df, y_pred, metrics)


if __name__ == "__main__":
    main()
