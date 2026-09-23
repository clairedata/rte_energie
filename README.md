# RTE Energy Pipeline ⚡

Pipeline de collecte, d'ingestion, d'automatisation et de modélisation prédictive des données énergétiques du réseau électrique français (RTE France) et des données météorologiques associées.

Ce projet a pour objectif de constituer une base de données temporelle sous PostgreSQL et de développer des modèles d'Intelligence Artificielle (Time Series Foundation Models - TSFM / LLMs pour séries temporelles) pour anticiper la consommation électrique en France.

---

## 📋 Table des Matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture du Projet](#-architecture-du-projet)
- [Prérequis](#-prérequis)
- [Installation & Démarrage](#-installation--démarrage)
- [Configuration (.env)](#-configuration-env)
- [Transformation & Qualité des Données (dbt)](#-transformation--qualité-des-données-dbt)
- [Utilisation](#-utilisation)
- [Schéma de la Base de Données](#-schéma-de-la-base-de-données)
- [Modélisation & Baseline de Référence](#-modélisation--baseline-de-référence)
- [Feuille de Route (Roadmap)](#-feuille-de-route-roadmap)

---

## ✨ Fonctionnalités

- 🔐 **Authentification sécurisée OAuth2 :** Connexion aux API RTE via Client Credentials.
- 📊 **Ingestion des séries énergétiques :** Récupération des prévisions de consommation (`AGGREGATED_CPC`) et de production par filière (`SOLAR`, `WIND_ONSHORE`, `WIND_OFFSHORE`) par horizon (`CURRENT`, `D-1`, `D-2`, `D-3`).
- 🌦️ **Intégration météo (Open-Meteo) :** Collecte horaire de la température à 2m (°C) et du vent à 10m (km/h).
- 🗄️ **Stockage PostgreSQL optimisé :** Séries temporelles horodatées (`TIMESTAMPTZ`), clés techniques `id` et gestion des conflits d'insertion sans doublon (`ON CONFLICT ... DO UPDATE`).
- 🔄 **Transformation & Qualité des Données (dbt Core) :** Modélisation ELT modulaire dans PostgreSQL via `dbt-postgres`. Séparation stricte entre les données brutes (`public`) et transformées (`analytics`), vues de staging nettoyées et tests de validation de qualité automatisés (`dbt test`).
- ⏱️ **Double Automatisation (Cron Job) :**
  - **Local :** Tâche planifiée Windows via `run_pipeline.bat` (`schtasks`).
  - **Cloud :** Workflow GitHub Actions quotidien avec conteneur PostgreSQL (`.github/workflows/pipeline.yml`).
- 📈 **Modélisation & Baseline :** Analyse exploratoire (EDA), découpage chronologique train/test strict et calcul des métriques de référence (MAE, RMSE, MAPE, WAPE).
- 🚀 **Outillage moderne :** Gestion des dépendances ultra-rapide avec [`uv`](https://docs.astral.sh/uv/) et Python 3.13+.

---

## 📂 Architecture du Projet

```text
rte-energy/
├── .env                  # Variables d'environnement locales (non commité)
├── .env.example          # Modèle des variables de configuration
├── .gitignore            # Fichiers et dossiers ignorés par Git
├── README.md             # Documentation principale
├── Brique_Technique.md   # Spécification détaillée des 15 briques techniques
├── docker-compose.yml    # Déploiement multi-services conteneurisé
├── .github/
│   └── workflows/
│       └── pipeline.yml  # Cron Job quotidien GitHub Actions (06h00 UTC)
├── frontend/             # 🌐 Application Web Front-End React (éCO2mix)
│   ├── src/
│   │   ├── components/   # Composants modulaires (Header, KpiGrid, ChartSection...)
│   │   ├── types/        # Typage TypeScript strict (energy.ts)
│   │   ├── App.tsx       # Composant racine orchestrant l'état et le refresh
│   │   └── index.css     # Design System Vanilla CSS (Dark Mode & Néon)
│   ├── package.json      # Dépendances React 19, Lucide, Chart.js, Vite
│   └── vite.config.ts    # Configuration du proxy API /api -> :8000
├── frontend_vanilla/     # 📦 Version Vanilla HTML/JS archivée de secours
├── dbt_energy/           # Transformation & Modélisation ELT dbt Core
│   ├── dbt_project.yml
│   └── models/
│       ├── staging/      # Vues de nettoyage (stg_consumption, stg_weather)
│       └── marts/        # Tables de faits (fct_national_consumption, fct_energy_features)
├── models/               # Poids des modèles IA entraînés
│   ├── chronos-bolt-rte/ # Checkpoint Hugging Face Chronos-Bolt fine-tuné
│   └── lightgbm_rte.joblib # Modèle LightGBM tabulaire sérialisé
├── reports/figures/      # Graphiques d'évaluation et de prévision exportés
└── src/
    └── rte_energy/
        ├── config.py     # Configuration, chemins et accès PostgreSQL
        ├── api/          # 🚀 API REST FastAPI (Restitution des données)
        │   └── app.py    # Endpoints (/api/kpi, /api/consumption, /api/benchmark)
        ├── db/           # DDL, connexion et migrations SQL
        ├── ingestion/    # Connecteurs RTE (OAuth2) et Open-Meteo
        ├── training/     # Expérimentations (Baseline, Chronos, LightGBM, Benchmark)
        └── production/   # Services autonomes (predict.py, pipeline.py E2E)
```

---

## 🛠️ Prérequis

- **Python :** Version `>= 3.13`
- **Gestionnaire de paquets :** [`uv`](https://docs.astral.sh/uv/) (recommandé) ou `pip`
- **Base de données :** Instance [PostgreSQL](https://www.postgresql.org/) active (locale ou distante)
- **Compte Développeur RTE :** Clés d'API (`Client ID` et `Client Secret`) issues du portail [RTE API Data](https://data.rte-france.com/).

---

## 🚀 Installation & Démarrage

### 1. Cloner le projet

```bash
git clone https://github.com/clairedata/rte_energie.git
cd rte_energie
```

### 2. Installer les dépendances

Naviguez dans le dossier `backend` et synchronisez l'environnement avec `uv` :

```bash
cd backend
uv sync
```

---

## ⚙️ Configuration (.env)

Créez un fichier `.env` à la racine du projet (ou dans `backend/`) basé sur l'exemple :

```bash
cp .env.example .env
```

Renseignez vos identifiants :

```ini
# API RTE France
RTE_CLIENT_ID=votre_client_id
RTE_CLIENT_SECRET=votre_client_secret

# Base de données PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=energy_db
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe

# Coordonnées Météo (France métropolitaine)
WEATHER_LAT=46.603354
WEATHER_LON=1.888334
```

---

## 🔄 Transformation & Qualité des Données (dbt)

Le projet applique les principes de la **Modern Data Stack (ELT)**. Les données brutes ingérées par Python dans le schéma `public` sont transformées, standardisées et testées par **dbt Core** (`dbt-postgres`) dans un schéma dédié `analytics`.

```text
[API RTE & Météo] ──► Python (Extract & Load) ──► PostgreSQL (schema public)
                                                        │
                                                 dbt (Transform)
                                                        │
                                                        ▼
                                             PostgreSQL (schema analytics)
                                              ├── stg_consumption (vue)
                                              └── stg_weather (vue)
```

### Commandes dbt :

Se positionner dans le dossier `backend/dbt_energy` :
```bash
cd backend/dbt_energy
```

1. **Tester la connexion à PostgreSQL :**
   ```bash
   uv run dbt debug --profiles-dir .
   ```
2. **Compiler et exécuter les modèles (création des vues/tables) :**
   ```bash
   uv run dbt run --profiles-dir .
   ```
3. **Lancer les tests de qualité des données :**
   ```bash
   uv run dbt test --profiles-dir .
   ```

---

## 💻 Utilisation

### 1. Initialiser les tables PostgreSQL
```bash
uv run python src/rte_energy/init_db.py
```

### 2. Exécuter le pipeline complet (RTE + Météo)
```bash
uv run rte-energy
# ou : uv run python src/rte_energy/pipeline.py
```

### 3. Exécuter les transformations et tests dbt
```bash
cd dbt_energy
uv run dbt run --profiles-dir .
uv run dbt test --profiles-dir .
cd ..
```

### 4. Lancer l'analyse exploratoire (EDA)
```bash
uv run python src/rte_energy/eda.py
```

### 5. Évaluer la Baseline de référence
```bash
uv run python src/rte_energy/training/baseline.py
```

### 6. Entraîner le modèle LightGBM (Météo + Lags)
```bash
uv run python src/rte_energy/training/lgbm_model.py
```

### 7. Exécuter le Fine-Tuning de Chronos-Bolt Small
```bash
uv run python src/rte_energy/training/chronos_finetune.py
```

### 8. Lancer le Benchmark Comparatif (3-Way / 4-Way)
```bash
uv run python src/rte_energy/training/chronos_benchmark.py
```

### 9. 🌐 Lancer l'Application Web Front-End (React + FastAPI)

L'application supporte deux modes d'exécution :

#### Mode A — Production Unifié (Recommandé) :
Le serveur FastAPI distribue directement l'application React compilée :
```bash
# 1. Compiler le Front-End React (si modifications)
cd frontend && npm run build && cd ..

# 2. Lancer le serveur unifié (API + React)
uv run uvicorn rte_energy.api.app:app --host 127.0.0.1 --port 8000 --reload
```
*Accédez à l'application sur : [http://localhost:8000](http://localhost:8000).*

#### Mode B — Développement Rapide (Vite HMR) :
Deux terminaux séparés pour profiter du rechargement à chaud instantané :
* **Terminal 1 (Backend API) :** `uv run uvicorn rte_energy.api.app:app --host 127.0.0.1 --port 8000 --reload`
* **Terminal 2 (Frontend React) :** `cd frontend && npm run dev`
*Accédez au serveur de développement sur : [http://localhost:5173](http://localhost:5173).*

---

## 🗄️ Schéma de la Base de Données

L'architecture sépare strictement les données brutes des données analytiques préparées :

### 📁 1. Schéma `public` (Données Brutes)

#### Table : `consumption_forecast`
| Colonne | Type | Description |
| :--- | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Identifiant technique unique |
| `start_date` | `TIMESTAMPTZ` | Début du créneau |
| `end_date` | `TIMESTAMPTZ` | Fin du créneau |
| `production_type` | `VARCHAR(50)` | Série (ex: `AGGREGATED_CPC`, `SOLAR`, `WIND_ONSHORE`) |
| `forecast_type` | `VARCHAR(20)` | Horizon de prévision (`CURRENT`, `D-1`, `D-2`, `D-3`) |
| `sub_type` | `VARCHAR(20)` | Guichet de révision (ex: `DA01`, `DA02`, `ID00`) |
| `value_mw` | `FLOAT` | Puissance en Mégawatts (MW) |
| `updated_at` | `TIMESTAMPTZ` | Date et heure de mise à jour |

*Contrainte d'unicité (upsert) : `UNIQUE (start_date, production_type, forecast_type, sub_type)`.*

#### Table : `weather`
| Colonne | Type | Description |
| :--- | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Identifiant technique unique |
| `timestamp` | `TIMESTAMPTZ` | Horodatage de l'observation |
| `temperature_c` | `FLOAT` | Température à 2m (°C) |
| `wind_speed` | `FLOAT` | Vitesse du vent à 10m (km/h) |
| `updated_at` | `TIMESTAMPTZ` | Date et heure de mise à jour |

*Contrainte d'unicité (upsert) : `UNIQUE (timestamp)`.*

### 📁 2. Schéma `analytics` (Données Transformées & Testées dbt)

#### Vue : `stg_consumption`
Nettoyage de la consommation/production électrique. Clé primaire renommée `forecast_id`, arrondis décimaux, exclusion défensive des puissances négatives (`WHERE value_mw >= 0`).

#### Vue : `stg_weather`
Standardisation des données météo Open-Meteo. Clé primaire `weather_id`, horodatage normalisé à l'heure (`date_trunc('hour', timestamp)`).

---

## 🎯 Modélisation Prédictive & Benchmark (TSFM vs Baseline)

Pour anticiper la consommation électrique française (`AGGREGATED_CPC`) à horizon 24h (96 pas de 15 minutes), nous avons mis en compétition notre **Baseline Naïve Saisonnière (J-1)** face aux **Time Series Foundation Models (TSFM)** d'Amazon en mode **Zero-Shot** (sans ré-entraînement local).

### 🏆 Résultats Officiels du Benchmark

| Métrique | Baseline Naïve (J-1) | Chronos-T5-Tiny (~8M) | Chronos-Bolt Small (~48M) ⭐ | Gain vs Baseline |
| :--- | :---: | :---: | :---: | :---: |
| **MAE** | 838.84 MW | 2 969.51 MW | **509.58 MW** | **-39.3 % d'erreur** 🟢 |
| **RMSE** | 1 167.61 MW | 3 743.53 MW | **620.24 MW** | **-46.9 % d'erreur** 🟢 |
| **MAPE** | 15.96 % | 80.26 % | **13.08 %** | **-18.0 % d'erreur** 🟢 |
| **WAPE** | 14.60 % | 51.70 % | **8.87 %** | **-39.3 % d'erreur** 🟢 |

*Fichiers graphiques générés : `backend/consumption_eda.png`, `backend/baseline_evaluation.png` et `backend/chronos_evaluation.png`.*

### 💡 Enseignements Clés de la Modélisation

1. **L'écrasante victoire de Chronos-Bolt Small :**  
   * **Division par 2 de la RMSE** (620 MW vs 1 168 MW), prouvant que le modèle évite les gros écarts sur les pics journaliers.
   * **WAPE sous la barre symbolique des 10 % (8.87 %)**, atteignant les standards industriels de prévision à J-1 sans aucun entraînement local.
   * Restitution précise du pic du midi (montée jusqu'à 12 100 MW là où la baseline restait bloquée au niveau d'un dimanche à 11 300 MW).
   * La réalité reste intégralement contenue dans l'intervalle de confiance à 80 % généré par les quantiles du modèle.
2. **La leçon "Bigger is not always better" :**  
   * Les tests sur `chronos-bolt-base` (205M de paramètres) ont montré une baisse de performance due à la sur-paramétrisation face à un contexte historique court (288 points). Le modèle `small` (~48M) représente le **Sweet Spot idéal** alliant légèreté, rapidité d'exécution sur CPU (< 1 sec) et précision maximale.

---

## 🗺️ Feuille de Route (Roadmap)

- [x] Authentification OAuth2 avec le portail RTE
- [x] Initialisation du schéma PostgreSQL et contraintes d'unicité
- [x] Ingestion par lot avec `execute_values` et upsert sans perte de données
- [x] Connecteur API Météo (Open-Meteo pour la France)
- [x] Dynamisation automatique des dates (calcul quotidien J à J+2)
- [x] Script d'orchestration unifié (`pipeline.py` & commande `rte-energy`)
- [x] Double automatisation de la collecte (Planificateur Windows + Cron Job GitHub Actions)
- [x] Modélisation et transformation ELT avec **dbt Core** (`dbt-postgres`)
- [x] Découpage en schémas PostgreSQL (`public` brut vs `analytics` transformé)
- [x] Tests automatisés de qualité de données dbt (`not_null`, `unique`, `accepted_values`)
- [x] Analyse exploratoire des données (EDA) et tracé de la série temporelle
- [x] Modèle de référence (Baseline Naïve Saisonnière) et métriques (MAE, RMSE, MAPE, WAPE)
- [x] Expérimentation Zero-Shot avec Foundation Model (Amazon Chronos-Bolt)
- [x] Benchmark comparatif et validation du modèle champion V1 (Chronos-Bolt Small - WAPE 8.87%)
- [x] Couche Marts dbt (`fct_energy_features.sql`) unifiant consommation et météo
- [x] Modèle Machine Learning comparatif sur long historique (LightGBM avec météo et variables calendaires)
- [x] Module de prédiction réutilisable pour production (`predict.py`)
- [x] Tableau de bord interactif éCO2mix (FastAPI + HTML5/Vanilla CSS/Chart.js)

