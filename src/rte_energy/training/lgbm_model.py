"""
================================================================================
  MODULE : training/lgbm_model.py
  OBJECTIF : Modèle prédictif Machine Learning tabulaire (LightGBM)
             multivarié combinant consommation électrique (RTE), météo
             (Open-Meteo), lags autorégressifs et variables calendaires.
================================================================================
"""

import sys
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import lightgbm as lgb
import joblib
from rte_energy.config import (
    get_db_connection,
    LIGHTGBM_MODEL_FILE,
    LGBM_EVAL_PLOT
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Paramètres temporels
TEST_HOURS = 24
VAL_HOURS = 48


def load_feature_store() -> pd.DataFrame:
    """
    Extrait les données combinées énergie + météo de 'analytics.fct_energy_features'.
    """
    conn = get_db_connection()
    query = """
        SELECT 
            observation_hour,
            consumption_mw,
            temperature_c,
            wind_speed_kmh,
            hour_of_day,
            day_of_week,
            is_weekend,
            month
        FROM analytics.fct_energy_features
        ORDER BY observation_hour ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["observation_hour"] = pd.to_datetime(df["observation_hour"])
    df.set_index("observation_hour", inplace=True)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature Engineering sans fuite temporelle (lags minimums de 24h).
    """
    data = df.copy()

    # 1. Variables autorégressives
    data["lag_24h"] = data["consumption_mw"].shift(24)
    data["lag_48h"] = data["consumption_mw"].shift(48)
    data["lag_168h"] = data["consumption_mw"].shift(168)

    # 2. Statistiques glissantes
    past_series = data["consumption_mw"].shift(24)
    data["rolling_mean_24h"] = past_series.rolling(window=24, min_periods=12).mean()
    data["rolling_std_24h"] = past_series.rolling(window=24, min_periods=12).std()
    data["rolling_min_24h"] = past_series.rolling(window=24, min_periods=12).min()
    data["rolling_max_24h"] = past_series.rolling(window=24, min_periods=12).max()

    # 3. Encodages cycliques
    data["sin_hour"] = np.sin(2 * np.pi * data["hour_of_day"] / 24.0)
    data["cos_hour"] = np.cos(2 * np.pi * data["hour_of_day"] / 24.0)
    data["sin_day"] = np.sin(2 * np.pi * data["day_of_week"] / 7.0)
    data["cos_day"] = np.cos(2 * np.pi * data["day_of_week"] / 7.0)

    # 4. Indicateurs thermiques non-linéaires
    data["heating_deg"] = np.maximum(0, 18.0 - data["temperature_c"])
    data["cooling_deg"] = np.maximum(0, data["temperature_c"] - 24.0)

    data.dropna(inplace=True)
    return data


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


def temporal_split(
    df: pd.DataFrame,
    feature_cols: list,
    target_col: str = "consumption_mw"
) -> Tuple:
    """
    Découpage chronologique strict : Train / Val (48h) / Test (24h).
    """
    n = len(df)
    test_idx = n - TEST_HOURS
    val_idx = test_idx - VAL_HOURS

    train_df = df.iloc[:val_idx]
    val_df = df.iloc[val_idx:test_idx]
    test_df = df.iloc[test_idx:]

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]

    X_val = val_df[feature_cols]
    y_val = val_df[target_col]

    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    return (X_train, y_train), (X_val, y_val), (X_test, y_test), test_df.index


def train_lightgbm(
    train_data: Tuple[pd.DataFrame, pd.Series],
    val_data: Tuple[pd.DataFrame, pd.Series]
) -> lgb.LGBMRegressor:
    """
    Entraîne le modèle LightGBM avec early stopping sur la validation.
    """
    X_train, y_train = train_data
    X_val, y_val = val_data

    model = lgb.LGBMRegressor(
        objective="regression_l1",
        n_estimators=1000,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=6,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_names=["Validation"],
        eval_metric="l1",
        callbacks=[
            lgb.early_stopping(stopping_rounds=40, verbose=False),
            lgb.log_evaluation(period=0)
        ]
    )

    return model


def plot_evaluation(
    test_dates: pd.DatetimeIndex,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    feature_names: list,
    feature_importances: np.ndarray,
    metrics: Dict[str, float],
    save_path: Path
) -> None:
    """
    Visuel à 2 panneaux : Prédiction vs Réel et Feature Importance.
    """
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Panneau 1 : Courbe Réel vs Prédiction
    ax1.plot(test_dates, y_true, label="Consommation Réelle (RTE)", color="#1f77b4", linewidth=2.5, marker="o", markersize=4)
    ax1.plot(test_dates, y_pred, label="Prédiction LightGBM", color="#2ca02c", linewidth=2.5, linestyle="--", marker="s", markersize=4)
    ax1.set_title(
        f"Prédiction LightGBM sur 24h\n"
        f"MAE: {metrics['MAE']:.1f} MW | RMSE: {metrics['RMSE']:.1f} MW | WAPE: {metrics['WAPE']:.2f}%",
        fontsize=12, fontweight="bold"
    )
    ax1.set_xlabel("Date et Heure", fontsize=10)
    ax1.set_ylabel("Puissance (MW)", fontsize=10)
    ax1.tick_params(axis="x", rotation=25)
    ax1.legend(loc="upper right", fontsize=10)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Panneau 2 : Importance des Variables
    importance_df = pd.DataFrame({
        "Feature": feature_names,
        "Importance": feature_importances
    }).sort_values("Importance", ascending=True)

    ax2.barh(importance_df["Feature"], importance_df["Importance"], color="#3b82f6", edgecolor="#1d4ed8")
    ax2.set_title("Importance des Variables (Feature Importance)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Nombre d'utilisations dans les arbres (Splits)", fontsize=10)
    ax2.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"📊 Graphique sauvegardé dans : {save_path}")


def main():
    print("=" * 80)
    print("  🚀 ENTRAÎNEMENT DU MODÈLE LIGHTGBM MULTIVARIÉ")
    print("=" * 80)

    print("\n⏳ 1/5 Chargement des données depuis 'analytics.fct_energy_features'...")
    raw_df = load_feature_store()
    print(f"   • {len(raw_df)} enregistrements horaires chargés.")

    print("\n⏳ 2/5 Ingénierie des variables (Lags, Moyennes mobiles, Thermique)...")
    featured_df = build_features(raw_df)

    feature_cols = [
        "temperature_c", "wind_speed_kmh", "heating_deg", "cooling_deg",
        "lag_24h", "lag_48h", "lag_168h",
        "rolling_mean_24h", "rolling_std_24h", "rolling_min_24h", "rolling_max_24h",
        "hour_of_day", "day_of_week", "is_weekend", "month",
        "sin_hour", "cos_hour", "sin_day", "cos_day"
    ]
    print(f"   • {len(featured_df)} heures exploitables après suppression des NaN.")
    print(f"   • {len(feature_cols)} variables explicatives sélectionnées.")

    print(f"\n⏳ 3/5 Découpage temporel (Test = {TEST_HOURS}h, Val = {VAL_HOURS}h)...")
    train_data, val_data, test_data, test_dates = temporal_split(featured_df, feature_cols)
    X_train, y_train = train_data
    X_val, y_val = val_data
    X_test, y_test = test_data

    print("\n⏳ 4/5 Entraînement de l'algorithme LightGBM...")
    model = train_lightgbm((X_train, y_train), (X_val, y_val))
    print(f"   • Arbres retenus : {model.best_iteration_}.")

    print("\n⏳ 5/5 Évaluation sur le jeu de test...")
    y_pred = model.predict(X_test)
    metrics = compute_metrics(y_test.values, y_pred)

    print("\n" + "=" * 80)
    print("  🏆 RÉSULTATS DU MODÈLE LIGHTGBM")
    print("=" * 80)
    print(f"  • MAE  : {metrics['MAE']:.2f} MW")
    print(f"  • RMSE : {metrics['RMSE']:.2f} MW")
    print(f"  • MAPE : {metrics['MAPE']:.2f} %")
    print(f"  • WAPE : {metrics['WAPE']:.2f} %")
    print("=" * 80)

    LIGHTGBM_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, LIGHTGBM_MODEL_FILE)
    print(f"\n💾 Modèle sauvegardé dans : {LIGHTGBM_MODEL_FILE}")

    plot_evaluation(
        test_dates=test_dates,
        y_true=y_test.values,
        y_pred=y_pred,
        feature_names=feature_cols,
        feature_importances=model.feature_importances_,
        metrics=metrics,
        save_path=LGBM_EVAL_PLOT
    )

    print("\n🎉 Modélisation LightGBM terminée avec succès !")


if __name__ == "__main__":
    main()
