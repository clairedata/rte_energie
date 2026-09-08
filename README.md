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
├── .github/
│   └── workflows/
│       └── pipeline.yml  # Cron Job quotidien GitHub Actions (06h00 UTC)
└── backend/
    ├── LLM.md            # Cadrage et stratégie pour les modèles prédictifs / TSFM
    ├── pyproject.toml    # Dépendances du projet (uv, pandas, matplotlib...)
    ├── uv.lock           # Verrouillage exact des versions
    ├── run_pipeline.bat  # Lanceur Windows pour le Planificateur de tâches
    ├── pipeline.log      # Fichier journal horodaté d'exécution
    ├── consumption_eda.png       # Graphique exploratoire de la consommation
    ├── baseline_evaluation.png  # Graphique d'évaluation de la Baseline naïve
    ├── chronos_evaluation.png   # Graphique comparatif Baseline vs Amazon Chronos-Bolt
    └── src/
        └── rte_energy/
            ├── __init__.py          # Point d'entrée CLI (uv run rte-energy)
            ├── init_db.py           # Création et migration des tables SQL
            ├── ingest_rte.py        # Ingestion des données RTE France
            ├── ingest_weather.py    # Ingestion météo Open-Meteo
            ├── pipeline.py          # Orchestrateur unifié (RTE + Météo)
            ├── eda.py               # Analyse exploratoire et statistiques
            ├── baseline.py          # Modèle naïf saisonnier et calcul des métriques
            └── chronos_predict.py   # Modèle TSFM Amazon Chronos-Bolt Small (Zero-Shot)
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

### 3. Lancer l'analyse exploratoire (EDA)
```bash
uv run python src/rte_energy/eda.py
```

### 4. Évaluer la Baseline de référence
```bash
uv run python src/rte_energy/baseline.py
```

### 5. Exécuter le modèle de fondation (Amazon Chronos-Bolt)
```bash
uv run python src/rte_energy/chronos_predict.py
```

---

## 🗄️ Schéma de la Base de Données

### Table : `consumption_forecast`
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

### Table : `weather`
| Colonne | Type | Description |
| :--- | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Identifiant technique unique |
| `timestamp` | `TIMESTAMPTZ` | Horodatage de l'observation |
| `temperature_c` | `FLOAT` | Température à 2m (°C) |
| `wind_speed` | `FLOAT` | Vitesse du vent à 10m (km/h) |
| `updated_at` | `TIMESTAMPTZ` | Date et heure de mise à jour |

*Contrainte d'unicité (upsert) : `UNIQUE (timestamp)`.*

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
- [x] Analyse exploratoire des données (EDA) et tracé de la série temporelle
- [x] Modèle de référence (Baseline Naïve Saisonnière) et métriques (MAE, RMSE, MAPE, WAPE)
- [x] Expérimentation Zero-Shot avec Foundation Model (Amazon Chronos-Bolt)
- [x] Benchmark comparatif et validation du modèle champion V1 (Chronos-Bolt Small - WAPE 8.87%)
- [ ] Modèle Machine Learning comparatif sur long historique (LightGBM avec météo et variables calendaires)
- [ ] Module de prédiction réutilisable pour production (`predict.py`)
- [ ] Tableau de bord interactif (Streamlit / Grafana)
