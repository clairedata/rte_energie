# ==============================================================================
# DOCKERFILE - RTE ENERGY PIPELINE & INFERENCE BACKEND
# ==============================================================================
# Image officielle Python 3.13 Debian Slim (légère, sécurisée et rapide)
FROM python:3.13-slim

# Configuration des variables d'environnement Python et uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Installation des dépendances système légères :
# - libgomp1 : indispensable pour l'accélération OpenMP (LightGBM & PyTorch CPU)
# - curl : utile pour les diagnostics réseau et vérifications
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation ultra-rapide de uv via l'image officielle d'Astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Définition du répertoire de travail dans le conteneur
WORKDIR /app

# 1. Copie des fichiers de verrouillage des dépendances (mise en cache Docker optimale)
COPY pyproject.toml uv.lock ./

# 2. Installation préalable des dépendances sans le code métier
RUN uv sync --frozen --no-dev --no-install-project

# 3. Copie du code applicatif, du projet dbt et de la documentation
COPY src/ ./src/
COPY dbt_energy/ ./dbt_energy/
COPY README.md ./

# 4. Synchronisation finale et enregistrement du package 'rte-energy'
RUN uv sync --frozen --no-dev

# Commande par défaut : exécution du pipeline unifié complet (Ingestion -> dbt -> Inférence)
CMD ["uv", "run", "rte-energy"]
