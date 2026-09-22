"""
================================================================================
  MODULE : training/eda.py
  OBJECTIF : Analyse exploratoire des données (EDA) et tracé de la série temporelle.
================================================================================
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
from rte_energy.config import get_db_connection, FIGURES_DIR

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_consumption_data() -> pd.DataFrame:
    """
    Extrait la série temporelle unifiée de consommation depuis la table dbt.
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


def analyze_and_plot(df: pd.DataFrame) -> None:
    """
    Calcule les statistiques descriptives et génère le graphique exploratoire.
    """
    print("=" * 60)
    print("   STATISTIQUES DE CONSOMMATION ÉLECTRIQUE (D-1) ")
    print("=" * 60)
    print(f"Nombre de points temporels relevés : {len(df)}")
    print(f"Période couverte : du {df.index.min()} au {df.index.max()}")
    print(f"Consommation Moyenne  : {df['value_mw'].mean():.2f} MW")
    print(f"Consommation Minimale : {df['value_mw'].min():.2f} MW (creux de la nuit)")
    print(f"Consommation Maximale : {df['value_mw'].max():.2f} MW (pic d'activité)")
    print("=" * 60 + "\n")

    plt.figure(figsize=(14, 6))
    plt.plot(df.index, df["value_mw"], label="Consommation prévue (D-1)", color="#1f77b4", linewidth=2)
    plt.title("Série Temporelle : Consommation Électrique en France (RTE)", fontsize=14, fontweight="bold")
    plt.xlabel("Date et Heure", fontsize=12)
    plt.ylabel("Puissance (Mégawatts - MW)", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    output_image = FIGURES_DIR / "consumption_eda.png"
    plt.savefig(output_image, dpi=150)
    plt.close()
    print(f"✅ Graphique EDA sauvegardé dans : {output_image}")


if __name__ == "__main__":
    data = load_consumption_data()
    if data.empty:
        print("⚠️ Aucune donnée trouvée dans analytics.fct_national_consumption.")
    else:
        analyze_and_plot(data)
