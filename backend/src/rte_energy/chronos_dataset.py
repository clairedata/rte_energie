"""
================================================================================
  MODULE : chronos_dataset.py
  OBJECTIF : Préparation des données par fenêtres glissantes pour le Fine-Tuning
             du modèle Amazon Chronos-Bolt sur les données RTE.
================================================================================
Ce module réalise les opérations suivantes :
1. Extraction de la série temporelle unifiée depuis la base PostgreSQL (RTE).
2. Séparation stricte du jeu de Test final (les 96 derniers points = 24h).
   ⚠️ Ce jeu de Test est sanctuarisé : le modèle ne doit JAMAIS le voir à l'entraînement.
3. Découpage de l'historique d'entraînement en couples (Contexte, Cible) via
   une fenêtre glissante (Sliding Window).
4. Création des classes Dataset et DataLoader PyTorch pour alimenter la descente
   de gradient (avec split Train / Validation).
"""

import os
from typing import Tuple
import psycopg2
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from dotenv import load_dotenv

# ==============================================================================
# 1. CONFIGURATION DE L'ACCÈS À LA BASE DE DONNÉES POSTGRESQL
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
# 2. CHARGEMENT DE LA SÉRIE HISTORIQUE DEPUIS POSTGRESQL
# ==============================================================================
def load_historical_series() -> pd.Series:
    """
    Extrait l'ensemble des données de consommation électrique disponibles en base.
    
    Requête :
    - Filtre sur 'AGGREGATED_CPC' et 'D-1' (consommation globale agrégée à J-1).
    - Moyenne les révisions éventuelles pour chaque quart d'heure ('start_date').
    - Trie par ordre chronologique strict.
    
    Retour :
        pd.Series : Série temporelle indexée par la date, avec les valeurs en MW.
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

    # Conversion en datetime et indexation
    df["start_date"] = pd.to_datetime(df["start_date"])
    df.set_index("start_date", inplace=True)
    
    return df["value_mw"]


# ==============================================================================
# 3. DÉCOUPAGE EN FENÊTRES GLISSANTES (SLIDING WINDOWS)
# ==============================================================================
def create_sliding_windows(
    series: np.ndarray,
    context_length: int = 512,
    prediction_length: int = 64,
    stride: int = 4
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Transforme une série temporelle continue en une collection de paires (X, Y) :
    - X (contexte) : les 'context_length' valeurs passées (ex: 512 quarts d'heure = 128 heures).
    - Y (cible)    : les 'prediction_length' valeurs futures immédiates (ex: 64 quarts d'heure = 16 heures).
    
    Paramètres :
        series (np.ndarray) : Tableau 1D de la série de consommation (MW).
        context_length (int) : Longueur de l'historique donné en entrée au modèle (défaut : 512).
        prediction_length (int) : Horizon que le modèle doit apprendre à prédire (défaut : 64).
        stride (int) : Pas de déplacement de la fenêtre (ex: 4 quarts d'heure = 1 heure de décalage).
                       Un stride plus faible génère plus d'exemples d'apprentissage.
                       
    Retour :
        Tuple[torch.Tensor, torch.Tensor] :
            - context_tensors : Tenseur de forme (N_échantillons, context_length)
            - target_tensors  : Tenseur de forme (N_échantillons, prediction_length)
    """
    total_window = context_length + prediction_length
    num_samples = (len(series) - total_window) // stride + 1

    if num_samples <= 0:
        raise ValueError(
            f"La série temporelle ({len(series)} points) est trop courte pour une fenêtre "
            f"totale de {total_window} points (contexte={context_length} + cible={prediction_length})."
        )

    contexts = []
    targets = []

    # Parcours de la série avec le pas 'stride'
    for i in range(0, len(series) - total_window + 1, stride):
        # 1. Fenêtre de contexte passée (X)
        window_ctx = series[i : i + context_length]
        # 2. Fenêtre future cible (Y)
        window_tgt = series[i + context_length : i + total_window]

        contexts.append(window_ctx)
        targets.append(window_tgt)

    # Conversion en tenseurs PyTorch float32
    contexts_tensor = torch.tensor(np.array(contexts), dtype=torch.float32)
    targets_tensor = torch.tensor(np.array(targets), dtype=torch.float32)

    return contexts_tensor, targets_tensor


# ==============================================================================
# 4. CLASSE PYTORCH DATASET
# ==============================================================================
class RTEChronoDataset(Dataset):
    """
    Dataset PyTorch standard contenant les couples (contexte, cible).
    Permet à PyTorch de mélanger (shuffle), découper en batchs et charger les données en mémoire.
    """
    def __init__(self, contexts: torch.Tensor, targets: torch.Tensor):
        self.contexts = contexts
        self.targets = targets

    def __len__(self) -> int:
        """Retourne le nombre total de fenêtres disponibles."""
        return len(self.contexts)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """Retourne un exemple unique : (tenseur_contexte, tenseur_cible)."""
        return self.contexts[idx], self.targets[idx]


# ==============================================================================
# 5. GÉNÉRATION DES DATALOADERS D'ENTRAÎNEMENT ET DE VALIDATION
# ==============================================================================
def prepare_dataloaders(
    test_points: int = 96,
    context_length: int = 512,
    prediction_length: int = 64,
    stride: int = 4,
    val_ratio: float = 0.15,
    batch_size: int = 16
) -> Tuple[DataLoader, DataLoader, pd.Series]:
    """
    Pipeline complet de préparation des données :
    1. Charge toute la série depuis la base.
    2. Isole les 'test_points' derniers points pour l'évaluation finale.
    3. Découpe le reste en fenêtres glissantes.
    4. Sépare chronologiquement en Train (ex: 85%) et Validation (ex: 15%).
    5. Retourne les DataLoaders PyTorch prêts pour l'entraînement.
    
    Retour :
        (train_loader, val_loader, test_series)
    """
    # 1. Chargement de toute la série
    full_series = load_historical_series()
    
    # 2. Isolation du jeu de Test final (les 96 derniers points)
    train_val_series = full_series.iloc[:-test_points].values
    test_series = full_series.iloc[-test_points:]

    # 3. Génération de toutes les fenêtres glissantes
    contexts, targets = create_sliding_windows(
        series=train_val_series,
        context_length=context_length,
        prediction_length=prediction_length,
        stride=stride
    )

    # 4. Séparation chronologique : Train (début) vs Validation (fin de la période d'entraînement)
    # Important : pour les séries temporelles, on ne mélange pas aléatoirement Train et Val
    # pour éviter la fuite d'information future dans la validation.
    total_samples = len(contexts)
    val_size = int(total_samples * val_ratio)
    train_size = total_samples - val_size

    train_contexts, val_contexts = contexts[:train_size], contexts[train_size:]
    train_targets, val_targets = targets[:train_size], targets[train_size:]

    # 5. Création des Datasets PyTorch
    train_dataset = RTEChronoDataset(train_contexts, train_targets)
    val_dataset = RTEChronoDataset(val_contexts, val_targets)

    # 6. Création des DataLoaders (on mélange seulement à l'intérieur du set d'entraînement)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_series


# ==============================================================================
# 6. POINT D'ENTRÉE : TEST ET DIAGNOSTIC DU DATASET
# ==============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("  🧪 ÉTAPE 1 : TEST ET VALIDATION DU PIPELINE DE DONNÉES (DATASET)")
    print("=" * 80)

    # Paramètres de test
    TEST_POINTS = 96       # 24 heures réservées au test final
    CONTEXT_LEN = 512      # 128 heures (~5.3 jours) en entrée
    PRED_LEN = 64          # 16 heures en sortie (optimal pour Chronos-Bolt)
    STRIDE = 4             # Décalage de 1h entre chaque fenêtre
    BATCH_SIZE = 16

    print(f"📊 Paramètres retenus :")
    print(f"   • Longueur du Contexte (X)   : {CONTEXT_LEN} quarts d'heure ({CONTEXT_LEN * 15 / 60:.1f} heures)")
    print(f"   • Longueur de la Cible  (Y)   : {PRED_LEN} quarts d'heure ({PRED_LEN * 15 / 60:.1f} heures)")
    print(f"   • Pas de glissement (Stride) : {STRIDE} quarts d'heure ({STRIDE * 15 / 60:.1f} heure)")
    print(f"   • Horizon réservé au Test    : {TEST_POINTS} quarts d'heure ({TEST_POINTS * 15 / 60:.1f} heures)")
    print()

    print("⏳ Chargement des données et découpage en fenêtres...")
    train_loader, val_loader, test_series = prepare_dataloaders(
        test_points=TEST_POINTS,
        context_length=CONTEXT_LEN,
        prediction_length=PRED_LEN,
        stride=STRIDE,
        val_ratio=0.15,
        batch_size=BATCH_SIZE
    )

    print(f"✅ Découpage terminé avec succès !")
    print(f"   • Nombre total d'échantillons d'entraînement (Train) : {len(train_loader.dataset)}")
    print(f"   • Nombre total d'échantillons de validation (Val)    : {len(val_loader.dataset)}")
    print(f"   • Nombre de batchs Train (taille={BATCH_SIZE})         : {len(train_loader)}")
    print(f"   • Nombre de batchs Val   (taille={BATCH_SIZE})         : {len(val_loader)}")
    print(f"   • Points du jeu de Test final préservés              : {len(test_series)} points")
    print(f"     (du {test_series.index.min()} au {test_series.index.max()})")
    print()

    # Inspection d'un premier batch réel
    for batch_x, batch_y in train_loader:
        print("🔍 Inspection de la structure d'un batch PyTorch d'entraînement :")
        print(f"   • batch_x.shape (Contexte d'entrée) : {batch_x.shape} -> attendu (batch_size, {CONTEXT_LEN})")
        print(f"   • batch_y.shape (Cible future)      : {batch_y.shape} -> attendu (batch_size, {PRED_LEN})")
        print(f"   • Plage de valeurs du Contexte      : min={batch_x.min():.1f} MW, max={batch_x.max():.1f} MW")
        print(f"   • Plage de valeurs de la Cible      : min={batch_y.min():.1f} MW, max={batch_y.max():.1f} MW")
        break

    print("\n" + "=" * 80)
    print("  🎉 LE DATASET EST PRÊT ET OPÉRATIONNEL POUR LE FINE-TUNING !")
    print("=" * 80)
