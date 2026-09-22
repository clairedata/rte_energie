"""
================================================================================
  MODULE : training/chronos_benchmark.py
  OBJECTIF : Benchmark comparatif à 3 voies :
             1. Baseline Naïve (J-7)
             2. Amazon Chronos-Bolt Small (Zero-Shot)
             3. Amazon Chronos-Bolt Small (Fine-Tuned RTE)
================================================================================
"""

import sys
from pathlib import Path
from typing import Tuple, Dict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import torch
from chronos import BaseChronosPipeline
from rte_energy.config import (
    get_db_connection,
    CHRONOS_MODEL_DIR,
    BENCHMARK_PLOT
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_MODEL_NAME = "amazon/chronos-bolt-small"
PREDICTION_LENGTH = 64


def load_data() -> pd.DataFrame:
    """
    Extrait la série unifiée de consommation.
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


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calcule MAE, RMSE, MAPE, WAPE.
    """
    errors = np.abs(y_true - y_pred)
    mae = float(np.mean(errors))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mape = float(np.mean(errors / y_true) * 100)
    wape = float((np.sum(errors) / np.sum(y_true)) * 100)
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape, "WAPE": wape}


def predict_naive_baseline(full_df: pd.DataFrame, test_index: pd.DatetimeIndex) -> np.ndarray:
    """
    Consommation observée 7 jours plus tôt (J-7).
    """
    naive_preds = []
    for target_time in test_index:
        same_time_last_week = target_time - pd.Timedelta(days=7)
        if same_time_last_week in full_df.index:
            naive_preds.append(full_df.loc[same_time_last_week, "value_mw"])
        else:
            naive_preds.append(full_df["value_mw"].mean())
    return np.array(naive_preds)


def predict_chronos_zero_shot(context_tensor: torch.Tensor, prediction_length: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Prédictions Zero-Shot.
    """
    print(f"⏳ Inférence Zero-Shot ({BASE_MODEL_NAME})...")
    pipeline = BaseChronosPipeline.from_pretrained(BASE_MODEL_NAME, device_map="cpu")
    forecast = pipeline.predict(context_tensor, prediction_length=prediction_length)
    quantiles = forecast[0].numpy()
    return quantiles[4], quantiles[0], quantiles[8]


def predict_chronos_finetuned(context_tensor: torch.Tensor, prediction_length: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Prédictions Fine-Tuned.
    """
    if not CHRONOS_MODEL_DIR.exists():
        raise FileNotFoundError(f"Modèle fine-tuné introuvable dans '{CHRONOS_MODEL_DIR}'.")

    print(f"⏳ Inférence Fine-Tuned (depuis {CHRONOS_MODEL_DIR})...")
    pipeline = BaseChronosPipeline.from_pretrained(str(CHRONOS_MODEL_DIR), device_map="cpu")
    forecast = pipeline.predict(context_tensor, prediction_length=prediction_length)
    quantiles = forecast[0].numpy()
    return quantiles[4], quantiles[0], quantiles[8]


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
    Superpose les prédictions et la réalité.
    """
    plt.figure(figsize=(15, 8))
    plt.plot(test_dates, y_true, label="Réalité (RTE Consommation)", color="#0f172a", linewidth=2.5, zorder=5)
    plt.plot(test_dates, y_naive, label="Baseline Naïve (J-7)", color="#ef4444", linestyle=":", linewidth=1.8, alpha=0.8)
    plt.plot(test_dates, y_zero_shot, label="Chronos-Bolt (Zero-Shot)", color="#f59e0b", linestyle="--", linewidth=2, alpha=0.85)
    plt.plot(test_dates, y_finetuned, label="Chronos-Bolt (Fine-Tuned RTE)", color="#2563eb", linewidth=2.5)

    plt.fill_between(test_dates, low_ft, high_ft, color="#3b82f6", alpha=0.18, label="Intervalle de confiance 80% (Fine-Tuned)")

    plt.title("🏆 BENCHMARK COMPARATIF : Baseline vs Zero-Shot vs Fine-Tuned", fontsize=14, fontweight="bold")
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


def main():
    print("=" * 85)
    print("  🏆 BENCHMARK COMPARATIF : NAÏVE vs ZERO-SHOT vs FINE-TUNED")
    print("=" * 85)

    df = load_data()
    train_df = df.iloc[:-PREDICTION_LENGTH]
    test_df = df.iloc[-PREDICTION_LENGTH:]

    test_dates = test_df.index
    y_true = test_df["value_mw"].values
    context_tensor = torch.tensor(train_df["value_mw"].values, dtype=torch.float32)

    print(f"Période de test : {len(test_df)} points ({test_dates.min()} -> {test_dates.max()})\n")

    y_naive = predict_naive_baseline(df, test_dates)
    y_zero_shot, _, _ = predict_chronos_zero_shot(context_tensor, PREDICTION_LENGTH)
    y_finetuned, low_ft, high_ft = predict_chronos_finetuned(context_tensor, PREDICTION_LENGTH)

    m_naive = compute_metrics(y_true, y_naive)
    m_zs = compute_metrics(y_true, y_zero_shot)
    m_ft = compute_metrics(y_true, y_finetuned)

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
    plot_benchmark(test_dates, y_true, y_naive, y_zero_shot, y_finetuned, low_ft, high_ft, BENCHMARK_PLOT)
    print("\n  🎉 BENCHMARK TERMINÉ AVEC SUCCÈS !\n")


if __name__ == "__main__":
    main()
