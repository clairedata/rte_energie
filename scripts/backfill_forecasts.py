"""
Script pour pré-calculer et enregistrer les prévisions Chronos pour les journées de test.
"""
from datetime import timedelta
import pandas as pd
import numpy as np
from rte_energy.config import get_db_connection
from rte_energy.production.predict import run_model_inference, save_forecasts_to_db

def backfill():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Récupérer l'historique complet
    query = "SELECT start_date, value_mw FROM analytics.fct_national_consumption ORDER BY start_date ASC;"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("Aucune donnée dans analytics.fct_national_consumption.")
        return
        
    df["start_date"] = pd.to_datetime(df["start_date"], utc=True)
    df.set_index("start_date", inplace=True)
    
    unique_dates = df.index.normalize().unique()
    print(f"Nombre de dates à traiter : {len(unique_dates)}")
    
    # Pour chaque date après les 7 premiers jours (pour avoir du contexte)
    for dt in unique_dates[7:]:
        # Contexte : les points strictement avant dt 00:00:00
        cutoff = dt
        history_slice = df[df.index < cutoff]["value_mw"].tail(512)
        if len(history_slice) < 96:
            continue
            
        target_day_str = dt.strftime("%Y-%m-%d")
        print(f"Calcul des prévisions pour {target_day_str}...")
        
        # Inférence
        model_name, future_dates, median_pred, lower_pred, upper_pred = run_model_inference(
            history_slice,
            prediction_points=96
        )
        
        # Sauvegarde
        save_forecasts_to_db(model_name, future_dates, median_pred, lower_pred, upper_pred)
        
    print("✅ Backfill terminé avec succès !")

if __name__ == "__main__":
    backfill()
