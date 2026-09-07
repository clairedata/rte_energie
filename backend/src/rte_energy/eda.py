import os
import psycopg2
import pandas as pd
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# 1. Charger les variables d'environnement du fichier .env (mots de passe, host, port)
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "energy_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD")
}

def load_consumption_data() -> pd.DataFrame:
    """
    Étape 1 : Connexion à PostgreSQL et extraction de la consommation électrique nationale.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    
    # On récupère la prévision de la veille (D-1) pour la consommation nationale (AGGREGATED_CPC)
    # Le 'GROUP BY start_date' avec 'AVG(value_mw)' garantit d'avoir exactement 1 point unique par créneau horaire
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
    
    # pd.read_sql_query convertit directement la réponse SQL en tableau Pandas (DataFrame)
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Conversion de la colonne textuelle 'start_date' en vrai format de date datetime
    df["start_date"] = pd.to_datetime(df["start_date"])
    
    # On place la date comme index temporel (l'étiquette de chaque ligne devient sa date et heure)
    df.set_index("start_date", inplace=True)
    
    return df

def analyze_and_plot(df: pd.DataFrame) -> None:
    """
    Étape 2 : Calcul des statistiques de base et tracé du graphique.
    """
    print("==================================================")
    print("   STATISTIQUES DE CONSOMMATION ÉLECTRIQUE (D-1) ")
    print("==================================================")
    print(f"Nombre de points temporels relevés : {len(df)}")
    print(f"Période couverte : du {df.index.min()} au {df.index.max()}")
    print(f"Consommation Moyenne  : {df['value_mw'].mean():.2f} MW")
    print(f"Consommation Minimale : {df['value_mw'].min():.2f} MW (creux de la nuit)")
    print(f"Consommation Maximale : {df['value_mw'].max():.2f} MW (pic d'activité)")
    print("==================================================\n")

    # Étape 3 : Dessin du graphique temporel
    plt.figure(figsize=(14, 6))
    plt.plot(df.index, df["value_mw"], label="Consommation prévue (D-1)", color="#1f77b4", linewidth=2)
    
    # Ajout des labels et de la grille pour une lecture facile
    plt.title("Série Temporelle : Consommation Électrique en France (RTE)", fontsize=14, fontweight="bold")
    plt.xlabel("Date et Heure", fontsize=12)
    plt.ylabel("Puissance (Mégawatts - MW)", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()

    # Sauvegarde du graphique au format image PNG
    output_image = "consumption_eda.png"
    plt.savefig(output_image, dpi=300)
    plt.close()
    print(f"✅ Graphique sauvegardé avec succès : backend/{output_image}")
    print("👉 Vous pourrez ouvrir cette image pour observer la forme de la courbe !")

if __name__ == "__main__":
    df = load_consumption_data()
    if df.empty:
        print("⚠️ Aucune donnée trouvée avec forecast_type = 'D-1'.")
    else:
        analyze_and_plot(df)
