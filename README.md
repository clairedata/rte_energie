# RTE Energy Pipeline ⚡

Pipeline de collecte, d'ingestion et de stockage des données énergétiques du réseau électrique français (RTE France) et des données météorologiques associées.

Ce projet a pour objectif de constituer une base de données temporelle robuste sous PostgreSQL afin de servir d'infrastructure pour l'analyse de données et l'entraînement de modèles de prédiction (Machine Learning / Time Series).

---

## 📋 Table des Matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture du Projet](#-architecture-du-projet)
- [Prérequis](#-prérequis)
- [Installation & Démarrage](#-installation--démarrage)
- [Configuration (.env)](#-configuration-env)
- [Utilisation](#-utilisation)
- [Schéma de la Base de Données](#-schéma-de-la-base-de-données)
- [Feuille de Route (Roadmap)](#-feuille-de-route-roadmap)

---

## ✨ Fonctionnalités

- 🔐 **Authentification sécurisée OAuth2 :** Connexion aux API RTE via Client Credentials.
- 📊 **Ingestion des prévisions énergétiques :** Récupération des prévisions de production par filière (Solaire, Éolien terrestre/en mer, etc.) et par horizon (`CURRENT`, `D-1`, `D-2`, `D-3`).
- 🌦️ **Intégration météo (Open-Meteo) :** Collecte horaire de la température à 2m (°C) et de la vitesse du vent à 10m (km/h) pour la France.
- 🗄️ **Stockage PostgreSQL optimisé :** Séries temporelles horodatées (`TIMESTAMPTZ`), clés techniques `id` et gestion des conflits d'insertion (upsert).
- 🚀 **Outillage moderne :** Gestion des dépendances ultra-rapide avec [`uv`](https://docs.astral.sh/uv/) et Python 3.13+.

---

## 📂 Architecture du Projet

```text
rte-energy/
├── .env                  # Variables d'environnement (non commité)
├── .env.example          # Modèle des variables de configuration
├── .gitignore            # Fichiers et dossiers ignorés par Git
├── README.md             # Documentation principale
└── backend/
    ├── pyproject.toml    # Dépendances et métadonnées du projet (uv)
    ├── uv.lock           # Verrouillage exact des versions
    └── src/
        └── rte_energy/
            ├── __init__.py          # Point d'entrée du package
            ├── init_db.py           # Création et migration des tables PostgreSQL
            ├── ingest_rte.py        # Récupération API RTE et insertion en base
            └── ingest_weather.py    # Récupération API Open-Meteo et insertion en base
```

---

## 🛠️ Prérequis

- **Python :** Version `>= 3.13`
- **Gestionnaire de paquets :** [`uv`](https://docs.astral.sh/uv/) (recommandé) ou `pip`
- **Base de données :** Instance [PostgreSQL](https://www.postgresql.org/) active (locale ou distante)
- **Compte Développeur RTE :** Création d'une application sur le portail [RTE API Data](https://data.rte-france.com/) pour obtenir vos clés API (`Client ID` et `Client Secret`).

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

*(Si vous utilisez `pip`, activez votre environnement virtuel puis exécutez `pip install -e .`)*

---

## ⚙️ Configuration (.env)

Créez un fichier `.env` à la racine du projet (ou dans `backend/`) en vous basant sur l'exemple fourni :

```bash
cp .env.example .env
```

Renseignez vos identifiants :

```ini
# Identifiants API RTE (Réseau de Transport d'Électricité)
RTE_CLIENT_ID=votre_client_id_ici
RTE_CLIENT_SECRET=votre_client_secret_ici

# Paramètres de connexion PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=energy_db
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe

# Coordonnées géographiques optionnelles pour la météo (Centre de la France par défaut)
WEATHER_LAT=46.603354
WEATHER_LON=1.888334
```

> ⚠️ **Important :** Ne commitez **jamais** le fichier `.env` sur Git. Il contient des secrets et identifiants sensibles.

---

## 💻 Utilisation

### 1. Initialiser la base de données

Créez les tables nécessaires dans PostgreSQL en exécutant le script d'initialisation :

```bash
# Depuis le dossier backend/
uv run python src/rte_energy/init_db.py
```

### 2. Lancer l'ingestion des données RTE

Pour récupérer les prévisions de production électrique depuis l'API RTE et les insérer dans PostgreSQL :

```bash
# Depuis le dossier backend/
uv run python src/rte_energy/ingest_rte.py
```

### 3. Lancer l'ingestion des données Météo

Pour récupérer les données météorologiques (température, vent) via Open-Meteo et les insérer dans PostgreSQL :

```bash
# Depuis le dossier backend/
uv run python src/rte_energy/ingest_weather.py
```

---

## 🗄️ Schéma de la Base de Données

### Table : `consumption_forecast`

Stocke les prévisions énergétiques par tranche horaire et par filière.

| Colonne | Type | Description |
| :--- | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Identifiant technique unique |
| `start_date` | `TIMESTAMPTZ` | Début de l'intervalle de temps |
| `end_date` | `TIMESTAMPTZ` | Fin de l'intervalle de temps |
| `production_type` | `VARCHAR(50)` | Filière (ex: `SOLAR`, `WIND_ONSHORE`, `AGGREGATED_CPC`) |
| `forecast_type` | `VARCHAR(20)` | Horizon de prévision (`CURRENT`, `D-1`, `D-2`, `D-3`) |
| `sub_type` | `VARCHAR(20)` | Sous-type de prévision (ex: `DA01`, `DA02`) |
| `value_mw` | `FLOAT` | Puissance prévue en Mégawatts (MW) |
| `updated_at` | `TIMESTAMPTZ` | Date et heure de dernière mise à jour |

*Contrainte d'unicité (upsert) : `UNIQUE (start_date, production_type, forecast_type, sub_type)`.*

### Table : `weather`

Stocke les conditions météorologiques associées aux périodes d'analyse.

| Colonne | Type | Description |
| :--- | :--- | :--- |
| `id` | `SERIAL PRIMARY KEY` | Identifiant technique unique |
| `timestamp` | `TIMESTAMPTZ` | Horodatage de l'observation / prévision |
| `temperature_c` | `FLOAT` | Température moyenne à 2m (°C) |
| `wind_speed` | `FLOAT` | Vitesse du vent à 10m (km/h) |
| `updated_at` | `TIMESTAMPTZ` | Date et heure de dernière mise à jour |

*Contrainte d'unicité (upsert) : `UNIQUE (timestamp)`.*

---

## 🗺️ Feuille de Route (Roadmap)

- [x] Authentification OAuth2 avec le portail RTE
- [x] Initialisation du schéma PostgreSQL (tables `consumption_forecast` et `weather`)
- [x] Correction des clés primaires `id` et contraintes d'unicité composites
- [x] Ingestion par lot avec `execute_values` et upsert sans perte de données
- [x] Connecteur API Météo (Open-Meteo pour la France)
- [ ] Dynamisation des dates d'ingestion (calcul dynamique J à J+2)
- [ ] Script d'orchestration unifié (pipeline unique RTE + Météo)
- [ ] Automatisation de la collecte (Planificateur Windows / Cron / GitHub Actions)
- [ ] Pipeline Machine Learning de prévision de la demande / production énergétique
- [ ] Tableau de bord interactif (Streamlit / Grafana)
