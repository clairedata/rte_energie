"""
================================================================================
  MODULE : training/chronos_dataset.py
  OBJECTIF : Préparation des données par fenêtres glissantes pour le Fine-Tuning
             du modèle Amazon Chronos-Bolt sur les données RTE.
================================================================================
"""

import sys
from typing import Tuple
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from rte_energy.config import get_db_connection

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_historical_series() -> pd.Series:
    """
    Extrait l'ensemble des données de consommation électrique disponibles en base.
    """
    conn = get_db_connection()
    query = """
        SELECT 
            start_date,
            value_mw
        FROM analytics.fct_national_consumption
        ORDER BY start_date ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["start_date"] = pd.to_datetime(df["start_date"])
    df.set_index("start_date", inplace=True)
    return df["value_mw"]


def create_sliding_windows(
    series: np.ndarray,
    context_length: int = 512,
    prediction_length: int = 64,
    stride: int = 4
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Transforme une série temporelle continue en une collection de paires (X, Y).
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

    for i in range(0, len(series) - total_window + 1, stride):
        ctx = series[i:i + context_length]
        tgt = series[i + context_length:i + total_window]
        contexts.append(ctx)
        targets.append(tgt)

    context_tensors = torch.tensor(np.array(contexts), dtype=torch.float32)
    target_tensors = torch.tensor(np.array(targets), dtype=torch.float32)
    return context_tensors, target_tensors


class TimeSeriesDataset(Dataset):
    """
    Dataset PyTorch encapsulant les paires (contexte X, cible Y).
    """
    def __init__(self, contexts: torch.Tensor, targets: torch.Tensor):
        self.contexts = contexts
        self.targets = targets

    def __len__(self) -> int:
        return len(self.contexts)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.contexts[idx], self.targets[idx]


def prepare_dataloaders(
    test_points: int = 96,
    context_length: int = 512,
    prediction_length: int = 64,
    stride: int = 4,
    val_ratio: float = 0.15,
    batch_size: int = 16
) -> Tuple[DataLoader, DataLoader, pd.Series]:
    """
    Pipeline complet de préparation des données pour le fine-tuning.
    """
    series = load_historical_series()

    train_val_series = series.iloc[:-test_points]
    test_series = series.iloc[-test_points:]

    raw_values = train_val_series.values
    contexts, targets = create_sliding_windows(
        raw_values,
        context_length=context_length,
        prediction_length=prediction_length,
        stride=stride
    )

    total_samples = len(contexts)
    val_size = max(1, int(total_samples * val_ratio))
    train_size = total_samples - val_size

    train_x = contexts[:train_size]
    train_y = targets[:train_size]
    val_x = contexts[train_size:]
    val_y = targets[train_size:]

    train_dataset = TimeSeriesDataset(train_x, train_y)
    val_dataset = TimeSeriesDataset(val_x, val_y)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_series
