"""
================================================================================
  MODULE : training/chronos_finetune.py
  OBJECTIF : Réentraînement (Fine-Tuning) du modèle Amazon Chronos-Bolt Small
             sur la série de consommation électrique française (RTE).
================================================================================
"""

import sys
import time
from pathlib import Path
from typing import List
import torch
import torch.optim as optim
import matplotlib.pyplot as plt
from chronos.chronos_bolt import ChronosBoltModelForForecasting
from rte_energy.config import CHRONOS_MODEL_DIR, LOSS_PLOT
from rte_energy.training.chronos_dataset import prepare_dataloaders

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Hyperparamètres
MODEL_NAME = "amazon/chronos-bolt-small"
CONTEXT_LENGTH = 512
PREDICTION_LENGTH = 64
STRIDE = 4
TEST_POINTS = 96
EPOCHS = 5
BATCH_SIZE = 16
LEARNING_RATE = 5e-5
WEIGHT_DECAY = 0.01
GRAD_CLIP_NORM = 1.0


def train_one_epoch(
    model: ChronosBoltModelForForecasting,
    dataloader: torch.utils.data.DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device
) -> float:
    """
    Exécute une passe d'apprentissage sur le jeu d'entraînement.
    """
    model.train()
    total_loss = 0.0

    for batch_x, batch_y in dataloader:
        context = batch_x.to(device)
        target = batch_y.to(device)

        optimizer.zero_grad()
        output = model(context=context, target=target)
        loss = output.loss

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=GRAD_CLIP_NORM)
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(dataloader)


def evaluate(
    model: ChronosBoltModelForForecasting,
    dataloader: torch.utils.data.DataLoader,
    device: torch.device
) -> float:
    """
    Évalue la perte de validation sans modifier les poids.
    """
    model.eval()
    total_loss = 0.0

    with torch.no_grad():
        for batch_x, batch_y in dataloader:
            context = batch_x.to(device)
            target = batch_y.to(device)

            output = model(context=context, target=target)
            total_loss += output.loss.item()

    return total_loss / len(dataloader)


def plot_loss_curves(train_losses: List[float], val_losses: List[float], save_path: Path):
    """
    Trace et sauvegarde la courbe d'apprentissage.
    """
    plt.figure(figsize=(10, 6))
    epochs_range = range(1, len(train_losses) + 1)

    plt.plot(epochs_range, train_losses, "o-", label="Perte Entraînement (Train)", color="#2563eb", linewidth=2)
    plt.plot(epochs_range, val_losses, "s--", label="Perte Validation (Val)", color="#ef4444", linewidth=2)

    plt.title("Convergence de la Perte pendant le Fine-Tuning de Chronos-Bolt", fontsize=13, fontweight="bold")
    plt.xlabel("Époque", fontsize=11)
    plt.ylabel("Perte Quantile (Loss)", fontsize=11)
    plt.xticks(epochs_range)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"📊 Courbe de perte sauvegardée dans : {save_path}")


def main():
    print("=" * 80)
    print("  🚀 ÉTAPE 2 : FINE-TUNING DE CHRONOS-BOLT SUR LES DONNÉES RTE")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Dispositif de calcul détecté : {device.type.upper()}")

    print("\n⏳ 1/5 Préparation des données par fenêtres glissantes...")
    train_loader, val_loader, _ = prepare_dataloaders(
        test_points=TEST_POINTS,
        context_length=CONTEXT_LENGTH,
        prediction_length=PREDICTION_LENGTH,
        stride=STRIDE,
        val_ratio=0.15,
        batch_size=BATCH_SIZE
    )
    print(f"   • Train : {len(train_loader.dataset)} échantillons ({len(train_loader)} batchs)")
    print(f"   • Val   : {len(val_loader.dataset)} échantillons ({len(val_loader)} batchs)")

    print(f"\n⏳ 2/5 Chargement du modèle pré-entraîné '{MODEL_NAME}'...")
    model = ChronosBoltModelForForecasting.from_pretrained(
        MODEL_NAME,
        device_map=device.type
    )
    model.to(device)

    optimizer = optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    initial_val_loss = evaluate(model, val_loader, device)
    print(f"   • Perte de validation initiale (Zero-Shot) : {initial_val_loss:.4f}")

    print(f"\n⏳ 3/5 Lancement de l'apprentissage sur {EPOCHS} époques...")
    train_losses, val_losses = [], []
    best_val_loss = float("inf")
    start_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        epoch_start = time.time()
        train_loss = train_one_epoch(model, train_loader, optimizer, device)
        val_loss = evaluate(model, val_loader, device)

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        epoch_duration = time.time() - epoch_start
        checkpoint_badge = ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            CHRONOS_MODEL_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(CHRONOS_MODEL_DIR)
            checkpoint_badge = "🌟 [Meilleur Checkpoint Sauvegardé]"

        print(
            f"   Époque {epoch:02d}/{EPOCHS:02d} [{epoch_duration:4.1f}s] "
            f"| Train Loss: {train_loss:.4f} "
            f"| Val Loss: {val_loss:.4f} {checkpoint_badge}"
        )

    total_duration = time.time() - start_time
    print(f"\n✅ Entraînement terminé en {total_duration:.1f} secondes !")
    print(f"   • Meilleure Perte de Validation : {best_val_loss:.4f} (vs {initial_val_loss:.4f} en Zero-Shot)")

    print(f"\n⏳ 4/5 Sauvegarde du modèle dans : {CHRONOS_MODEL_DIR}")
    print(f"\n⏳ 5/5 Génération du graphique de convergence...")
    plot_loss_curves(train_losses, val_losses, LOSS_PLOT)

    print("\n" + "=" * 80)
    print("  🎉 FINE-TUNING RÉUSSI AVEC SUCCÈS !")
    print("=" * 80)


if __name__ == "__main__":
    main()
