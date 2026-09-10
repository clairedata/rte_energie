"""
================================================================================
  MODULE : chronos_finetune.py
  OBJECTIF : Réentraînement (Fine-Tuning) du modèle Amazon Chronos-Bolt Small
             sur la série de consommation électrique française (RTE).
================================================================================
Ce script réalise les opérations suivantes :
1. Chargement des DataLoaders Train / Validation préparés à l'Étape 1.
2. Téléchargement et initialisation du modèle pré-entraîné
   'amazon/chronos-bolt-small' avec ses poids initiaux.
3. Configuration de l'optimiseur (AdamW) avec un taux d'apprentissage adapté
   au transfert d'apprentissage (Transfer Learning).
4. Boucle d'entraînement supervisé (5 époques) :
   - Calcul de la perte quantile native (Pinball Loss) via `output.loss`.
   - Rétropropagation du gradient et mise à jour des poids.
   - Évaluation périodique sur l'ensemble de Validation.
   - Sauvegarde automatique du meilleur checkpoint (Best Val Loss).
5. Sauvegarde finale du modèle au format standard Hugging Face (dossier 'models/chronos-bolt-rte').
6. Génération et sauvegarde d'un graphique d'évolution de la perte (loss_convergence.png).
"""

import os
import time
from pathlib import Path
from typing import List, Tuple
import torch
import torch.optim as optim
import matplotlib.pyplot as plt
from chronos.chronos_bolt import ChronosBoltModelForForecasting

# Import robuste du Dataset (compatible exécution directe ou comme package)
try:
    from rte_energy.chronos_dataset import prepare_dataloaders
except ImportError:
    from chronos_dataset import prepare_dataloaders


# ==============================================================================
# 1. CONFIGURATION DES HYPERPARAMÈTRES DU FINE-TUNING
# ==============================================================================
# Modèle de départ
MODEL_NAME = "amazon/chronos-bolt-small"

# Paramètres temporels
CONTEXT_LENGTH = 512      # 128 heures passées (~5.3 jours) données en entrée
PREDICTION_LENGTH = 64   # 16 heures futures à prédire (taille native de Chronos-Bolt)
STRIDE = 4               # Décalage d'1 heure entre chaque fenêtre glissante
TEST_POINTS = 96         # 24 heures finales strictement préservées pour le test

# Hyperparamètres d'optimisation
EPOCHS = 5               # Nombre de passages complets sur les données
BATCH_SIZE = 16          # Taille du mini-batch
LEARNING_RATE = 5e-5     # Taux d'apprentissage doux (évite l'oubli catastrophique)
WEIGHT_DECAY = 0.01      # Régularisation L2 pour limiter le surapprentissage
GRAD_CLIP_NORM = 1.0     # Écrêtage des gradients pour garantir la stabilité numérique

# Chemins de sauvegarde
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "models" / "chronos-bolt-rte"
PLOT_OUTPUT = Path(__file__).resolve().parents[2] / "loss_convergence.png"


# ==============================================================================
# 2. FONCTION D'ENTRAÎNEMENT POUR UNE ÉPOQUE
# ==============================================================================
def train_one_epoch(
    model: ChronosBoltModelForForecasting,
    dataloader: torch.utils.data.DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device
) -> float:
    """
    Exécute une passe complète d'apprentissage (Train) sur le jeu de données :
    1. Active le mode d'entraînement (model.train()).
    2. Pour chaque batch :
       - Calcule la prédiction et la perte quantile native (output.loss).
       - Remet les gradients à zéro (optimizer.zero_grad()).
       - Rétropropage les erreurs (loss.backward()).
       - Écrête la norme des gradients pour la stabilité.
       - Met à jour les poids du réseau (optimizer.step()).
    
    Retour :
        float : Perte moyenne sur l'ensemble de l'époque d'entraînement.
    """
    model.train()
    total_loss = 0.0

    for step, (batch_x, batch_y) in enumerate(dataloader):
        # Déplacement des tenseurs vers le processeur (CPU ou GPU)
        context = batch_x.to(device)
        target = batch_y.to(device)

        # Réinitialisation des gradients
        optimizer.zero_grad()

        # Passe avant (Forward Pass)
        # La méthode forward calcule automatiquement la perte quantile
        # lorsque le paramètre 'target' est fourni !
        output = model(context=context, target=target)
        loss = output.loss

        # Passe arrière (Backward Pass)
        loss.backward()

        # Écrêtage du gradient pour éviter les explosions numériques
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=GRAD_CLIP_NORM)

        # Mise à jour des poids du modèle
        optimizer.step()

        total_loss += loss.item()

    avg_loss = total_loss / len(dataloader)
    return avg_loss


# ==============================================================================
# 3. FONCTION D'ÉVALUATION SUR LE SET DE VALIDATION
# ==============================================================================
def evaluate(
    model: ChronosBoltModelForForecasting,
    dataloader: torch.utils.data.DataLoader,
    device: torch.device
) -> float:
    """
    Évalue les performances du modèle sur les données de validation (non apprises) :
    1. Désactive le calcul des gradients (torch.no_grad()) pour économiser la mémoire.
    2. Calcule la perte quantile moyenne sans modifier les poids du modèle.
    
    Retour :
        float : Perte moyenne de validation.
    """
    model.eval()
    total_loss = 0.0

    with torch.no_grad():
        for batch_x, batch_y in dataloader:
            context = batch_x.to(device)
            target = batch_y.to(device)

            output = model(context=context, target=target)
            total_loss += output.loss.item()

    avg_loss = total_loss / len(dataloader)
    return avg_loss


# ==============================================================================
# 4. TRACÉ ET SAUVEGARDE DE LA COURBE DE PERTE
# ==============================================================================
def plot_loss_curves(train_losses: List[float], val_losses: List[float], save_path: Path):
    """
    Génère un graphique montrant l'évolution des pertes d'entraînement et de validation.
    Permet de diagnostiquer visuellement :
    - La convergence de l'apprentissage (courbes descendantes).
    - L'absence de surapprentissage (la courbe de validation reste proche de celle d'entraînement).
    """
    epochs = range(1, len(train_losses) + 1)
    
    plt.figure(figsize=(10, 6))
    plt.plot(epochs, train_losses, "o-", label="Perte Entraînement (Train Loss)", color="#2563eb", linewidth=2)
    plt.plot(epochs, val_losses, "s--", label="Perte Validation (Val Loss)", color="#16a34a", linewidth=2)
    
    plt.title("Convergence du Fine-Tuning - Amazon Chronos-Bolt Small (RTE)", fontsize=14, fontweight="bold")
    plt.xlabel("Époque", fontsize=12)
    plt.ylabel("Perte Quantile (Pinball Loss)", fontsize=12)
    plt.xticks(epochs)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"📊 Graphique de convergence sauvegardé dans : {save_path}")


# ==============================================================================
# 5. BOUCLE PRINCIPALE DE FINE-TUNING
# ==============================================================================
def main():
    print("=" * 80)
    print("  🚀 ÉTAPE 2 : FINE-TUNING DU MODÈLE AMAZON CHRONOS-BOLT SMALL SUR RTE")
    print("=" * 80)

    # 1. Sélection automatique du matériel (GPU si disponible, sinon CPU)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️ Matériel d'exécution sélectionné : {device.type.upper()}")
    if device.type == "cpu":
        print("   (Le modèle Chronos-Bolt Small est très léger et s'entraîne en quelques minutes sur CPU)")

    # 2. Préparation des données via le module chronos_dataset
    print("\n⏳ 1/5 Préparation des données par fenêtres glissantes...")
    train_loader, val_loader, test_series = prepare_dataloaders(
        test_points=TEST_POINTS,
        context_length=CONTEXT_LENGTH,
        prediction_length=PREDICTION_LENGTH,
        stride=STRIDE,
        val_ratio=0.15,
        batch_size=BATCH_SIZE
    )
    print(f"   • Échantillons d'entraînement : {len(train_loader.dataset)} ({len(train_loader)} batchs)")
    print(f"   • Échantillons de validation    : {len(val_loader.dataset)} ({len(val_loader)} batchs)")

    # 3. Chargement du modèle de fondation pré-entraîné
    print(f"\n⏳ 2/5 Chargement du modèle pré-entraîné '{MODEL_NAME}'...")
    model = ChronosBoltModelForForecasting.from_pretrained(
        MODEL_NAME,
        device_map=device.type
    )
    model.to(device)

    # 4. Configuration de l'optimiseur AdamW
    optimizer = optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    # 5. Évaluation initiale (Avant entraînement : Perte Zero-Shot)
    initial_val_loss = evaluate(model, val_loader, device)
    print(f"   • Perte de validation initiale (Zero-Shot) : {initial_val_loss:.4f}")

    # 6. Boucle d'entraînement
    print(f"\n⏳ 3/5 Lancement de l'apprentissage sur {EPOCHS} époques...")
    train_losses = []
    val_losses = []
    best_val_loss = float("inf")
    start_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        epoch_start = time.time()

        # Passe d'entraînement
        train_loss = train_one_epoch(model, train_loader, optimizer, device)
        # Passe de validation
        val_loss = evaluate(model, val_loader, device)

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        epoch_duration = time.time() - epoch_start

        # Sauvegarde du meilleur modèle
        is_best = val_loss < best_val_loss
        checkpoint_badge = ""
        if is_best:
            best_val_loss = val_loss
            # Création du dossier et sauvegarde
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(OUTPUT_DIR)
            checkpoint_badge = "🌟 [Meilleur Checkpoint Sauvegardé]"

        print(
            f"   Époque {epoch:02d}/{EPOCHS:02d} [{epoch_duration:4.1f}s] "
            f"| Train Loss: {train_loss:.4f} "
            f"| Val Loss: {val_loss:.4f} {checkpoint_badge}"
        )

    total_duration = time.time() - start_time
    print(f"\n✅ Entraînement terminé en {total_duration:.1f} secondes !")
    print(f"   • Meilleure Perte de Validation : {best_val_loss:.4f} "
          f"(contre {initial_val_loss:.4f} en Zero-Shot)")

    # 7. Sauvegarde du modèle final et de la courbe de convergence
    print(f"\n⏳ 4/5 Vérification des artefacts sauvegardés...")
    print(f"   • Dossier du modèle fine-tuné : {OUTPUT_DIR}")
    
    print(f"\n⏳ 5/5 Génération du graphique de convergence...")
    plot_loss_curves(train_losses, val_losses, PLOT_OUTPUT)

    print("\n" + "=" * 80)
    print("  🎉 FINE-TUNING RÉUSSI AVEC SUCCÈS !")
    print("  Le modèle est prêt pour le Benchmark final (Étape 3) !")
    print("=" * 80)


if __name__ == "__main__":
    main()
