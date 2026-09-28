# ⚡ Guide d'Installation et de Déploiement : RTE Energy & IA

Ce guide détaille pas à pas la procédure pour installer, configurer et exécuter l'intégralité du projet **RTE Energy Pipeline & Inférence IA** sur une nouvelle machine (Windows, Linux ou macOS).

---

## 📋 1. Prérequis Système

Avant de commencer, assurez-vous que les outils suivants sont installés sur le poste :

| Outil | Version Requise | Utilité dans le projet | Lien de téléchargement |
| :--- | :--- | :--- | :--- |
| **Git** | Dernière version | Clonage du dépôt de code | [git-scm.com](https://git-scm.com/) |
| **Python** | `>= 3.11` (3.12 ou 3.13 recommandé) | Exécution du backend & modèles IA | [python.org](https://www.python.org/) |
| **uv** | Dernière version | Gestionnaire d'environnement et de paquets ultra-rapide | [astral.sh/uv](https://astral.sh/uv/) |
| **Node.js & npm** | Node `>= 18.0` (LTS 20 ou 22) | Build et exécution du Front-End React | [nodejs.org](https://nodejs.org/) |
| **PostgreSQL** | Version 15 ou 16 *(ou Docker Desktop)* | Base de données relationnelle persistante | [postgresql.org](https://www.postgresql.org/) |

> [!TIP]
> **Installation rapide de `uv` :**
> * **Sur Windows (PowerShell) :**
>   ```powershell
>   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
>   ```
> * **Sur Linux / macOS :**
>   ```bash
>   curl -LsSf https://astral.sh/uv/install.sh | sh
>   ```
> * **Ou via pip :** `pip install uv`

---

## 🚀 2. Procédure d'Installation pas à pas

### Étape 1 : Récupérer le Dépôt
Ouvrez votre terminal et clonez le dépôt Git :
```bash
git clone <URL_DE_VOTRE_DEPOT_GIT>
cd rte_energie
```

---

### Étape 2 : Configuration des Variables d'Environnement (`.env`)
À la racine du dossier `rte_energie/`, créez un fichier nommé **`.env`** (ou copiez depuis `.env.example`) avec vos accès locaux :

```ini
# ==============================================================================
# 1. Base de données PostgreSQL locale
# ==============================================================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=energy_db
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe_postgres

# ==============================================================================
# 2. Identifiants API RTE France (https://data.rte-france.com/)
# ==============================================================================
RTE_CLIENT_ID=votre_client_id_rte
RTE_CLIENT_SECRET=votre_client_secret_rte

# ==============================================================================
# 3. Paramètres Météo (France métropolitaine)
# ==============================================================================
WEATHER_LAT=46.603354
WEATHER_LON=1.888334
```

---

### Étape 3 : Préparer la Base de Données PostgreSQL
Vérifiez que votre service PostgreSQL est bien démarré, puis créez la base de données dédiée `energy_db` :

* **Via pgAdmin ou terminal `psql` :**
  ```sql
  CREATE DATABASE energy_db;
  ```
* **Alternative avec Docker :** Si Docker Desktop est installé, lancez simplement :
  ```bash
  docker compose up -d postgres
  ```

---

### Étape 4 : Installer les Dépendances Python et Créer les Tables SQL
Grâce à `uv`, l'ensemble des bibliothèques scientifiques et web (PyTorch, Chronos, FastAPI, dbt, LightGBM, etc.) s'installe en quelques secondes dans un environnement virtuel isolé :

```bash
# 1. Synchronisation automatique des dépendances
uv sync

# 2. Initialisation du schéma relationnel (tables consumption_forecast, weather, model_forecasts)
uv run python -m rte_energy.db.init_schema
```

---

### Étape 5 : Ingestion des Données & Transformations dbt
Alimentez la base locale avec les données du réseau français et de la météo, puis appliquez les transformations analytiques :

```bash
# 1. Rapatrier l'historique de consommation RTE
uv run python -m rte_energy.ingestion.history_loader

# 2. Rapatrier les relevés météo Open-Meteo
uv run python -m rte_energy.ingestion.weather_client

# 3. Exécuter les transformations ELT dbt (génère le schéma analytics)
uv run dbt run --project-dir dbt_energy --profiles-dir dbt_energy
```

---

### Étape 6 : Génération des Prévisions IA (Inférence)
Générez les prévisions des prochaines 24h avec le modèle champion **Amazon Chronos-Bolt** :

```bash
uv run python -m rte_energy.production.predict
```

> [!NOTE]
> *Optionnel :* Si vous souhaitez réentraîner le modèle depuis zéro sur les données locales :
> ```bash
> uv run python -m rte_energy.training.chronos_finetune
> ```

---

### Étape 7 : Installer et Compiler le Front-End React
Rendez-vous dans le dossier `frontend` pour installer les packages npm et construire le bundle de production optimisé :

```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 🌐 3. Lancer l'Application

Deux modes de lancement sont disponibles :

### Option A — Mode Production Unifié (Recommandé - 1 seule commande)
Le serveur FastAPI héberge l'API REST et sert directement les fichiers compilés du Front-End React sur le même port :

```bash
uv run uvicorn rte_energy.api.app:app --host 127.0.0.1 --port 8000
```
👉 **Accédez à l'application dans votre navigateur :** **[http://localhost:8000](http://localhost:8000)**

---

### Option B — Mode Développement (Hot-Reloading)
Pour modifier le code avec actualisation instantanée :

* **Terminal 1 (Backend FastAPI) :**
  ```bash
  uv run uvicorn rte_energy.api.app:app --host 127.0.0.1 --port 8000 --reload
  ```
* **Terminal 2 (Frontend React Vite) :**
  ```bash
  cd frontend
  npm run dev
  ```
👉 **Accédez au Front-End :** **[http://localhost:5173](http://localhost:5173)** *(le proxy Vite redirige automatiquement `/api/*` vers `:8000`)*.

---

## ⏰ 4. (Windows) Activer l'Ingestion Quotidienne Automatique

Pour que votre machine locale télécharge automatiquement les nouvelles données de consommation et recalcule les prédictions chaque matin à **06h00** :

* **Méthode simple :** Double-cliquez sur le fichier script :
  ```text
  scripts\setup_task_scheduler.bat
  ```
* **Ce que fait la tâche :**
  - Nom : `RTE_Energy_Daily_Pipeline`
  - Fréquence : Tous les jours à 06h00
  - Rattrapage : Si le PC est éteint à 06h00, Windows lance automatiquement la mise à jour dès l'allumage.
  - Logs : Enregistrés dans `logs/scheduler_execution.log`.

---

## ⚡ 5. Cheatsheet : Résumé des Commandes (Copier-Coller)

```bash
# 1. Récupération et configuration
git clone <URL_DU_REPO> && cd rte_energie
# [Créer le fichier .env avec vos identifiants]

# 2. Backend, BDD et Pipeline
uv sync
uv run python -m rte_energy.db.init_schema
uv run python -m rte_energy.ingestion.history_loader
uv run python -m rte_energy.ingestion.weather_client
uv run dbt run --project-dir dbt_energy --profiles-dir dbt_energy
uv run python -m rte_energy.production.predict

# 3. Frontend React
cd frontend && npm install && npm run build && cd ..

# 4. Lancement
uv run uvicorn rte_energy.api.app:app --host 127.0.0.1 --port 8000
```

---

## 🛠️ 6. Résolution des Problèmes Courants (Dépannage)

| Erreur / Symptôme | Cause Probable | Solution |
| :--- | :--- | :--- |
| `UnicodeDecodeError` sur connexion PostgreSQL | Mot de passe contenant des caractères spéciaux avec encodage console non UTF-8 | Vérifiez que le mot de passe dans `.env` est encadré par des guillemets si nécessaire, et que le terminal est en UTF-8 (`chcp 65001`). |
| `FATAL: database "energy_db" does not exist` | La base n'a pas encore été créée dans PostgreSQL | Lancez `CREATE DATABASE energy_db;` dans pgAdmin ou `psql`. |
| Erreur 401 lors de l'ingestion RTE | `RTE_CLIENT_ID` ou `RTE_CLIENT_SECRET` invalides ou expirés | Connectez-vous sur [data.rte-france.com](https://data.rte-france.com/), régénérez votre application API et copiez les clés dans `.env`. |
| Port 8000 ou 5173 déjà utilisé | Une ancienne instance de FastAPI ou de Vite tourne déjà en arrière-plan | Fermez le terminal existant ou tuez le processus via le Gestionnaire des tâches (`taskkill /F /IM python.exe`). |
