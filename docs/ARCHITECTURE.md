# 🏛️ Architecture Technique & Schémas Détaillés du Projet

Ce document présente l'architecture complète du projet **RTE Energy Pipeline & Inférence IA**, depuis la collecte de données brutes jusqu'au déploiement conteneurisé sous Docker.

---

## 📋 Table des Matières

1. [Vue d'Ensemble : Pipeline de Données & Inférence End-to-End](#1-vue-densemble--pipeline-de-données--inférence-end-to-end)
2. [Architecture Conteneurisée Docker (Services, Réseau & Volumes)](#2-architecture-conteneurisée-docker-services-réseau--volumes)
3. [Cycle de Vie Quotidien & Séquence d'Exécution (Orchestrateur)](#3-cycle-de-vie-quotidien--séquence-dexécution-orchestrateur)
4. [Schéma de Données (ELT & Modèles dbt)](#4-schéma-de-données-elt--modèles-dbt)
5. [Fonctionnement Interne du Module d'Inférence (`predict.py`)](#5-fonctionnement-interne-du-module-dinférence-predictpy)

---

## 1. Vue d'Ensemble : Pipeline de Données & Inférence End-to-End

Le flux suit les standards industriels de la **Modern Data Stack** (ELT : *Extract, Load, Transform*) couplée à une couche **MLOps** (*Machine Learning Operations*) :

```mermaid
flowchart TB
    subgraph Sources ["🌐 1. SOURCES EXTERNES (APIs)"]
        A["API RTE France<br/>(OAuth2 - Prévisions & Consommation)"]
        B["API Open-Meteo<br/>(Relevés Température & Vent)"]
    end

    subgraph Ingestion ["📥 2. INGESTION PYTHON (Extract & Load)"]
        C["ingest_rte.py<br/>(Batch execute_values)"]
        D["ingest_weather.py<br/>(Horodatage horaire)"]
    end

    subgraph RawDB ["🗄️ 3. STOCKAGE BRUT (PostgreSQL - Schéma public)"]
        E[("Table: consumption_forecast<br/>(UNIQUE start_date, types)")]
        F[("Table: weather<br/>(UNIQUE timestamp)")]
    end

    subgraph dbtLayer ["🔄 4. TRANSFORMATION ELT (dbt Core - Schéma analytics)"]
        G["stg_consumption<br/>(Vérification valeurs >= 0)"]
        H["stg_weather<br/>(Normalisation des dates)"]
        I[("fct_national_consumption<br/>(Série unifiée quart-horaire)")]
        J[("fct_energy_features<br/>(Feature Store horaire + Météo + Calendrier)")]
    end

    subgraph ML ["🧠 5. MODÉLISATION PRÉDICTIVE & IA"]
        K["Modèle Champion Fine-Tuned<br/>(Amazon Chronos-Bolt RTE)"]
        L["Modèle Tabulaire Multivarié<br/>(LightGBM + Features thermiques)"]
    end

    subgraph Outputs ["📊 6. RESTITUTION & MONITORING"]
        M[("Table: model_forecasts<br/>(q10, q50 Médiane, q90)")]
        N["Graphique PNG : latest_forecast.png<br/>(Contrôle visuel immédiat)"]
    end

    %% Connexions
    A --> C --> E
    B --> D --> F
    E --> G --> I
    F --> H --> J
    G --> J
    I --> K
    J --> L
    K --> M
    K --> N

    classDef source fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1;
    classDef raw fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e;
    classDef dbt fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#15803d;
    classDef ml fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#5b21b6;
    classDef output fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b;

    class A,B source;
    class E,F raw;
    class G,H,I,J dbt;
    class K,L ml;
    class M,N output;
```

---

## 2. Architecture Conteneurisée Docker (Services, Réseau & Volumes)

La conteneurisation isole le système complet dans deux conteneurs qui communiquent à travers un réseau privé virtuel interne (`bridge`) :

```mermaid
flowchart LR
    subgraph Host ["💻 Machine Hôte (Windows / Serveur)"]
        subgraph LocalFiles ["Fichiers Locaux Synchronisés"]
            Env[".env (Identifiants & Clés)"]
            ModelsDir["backend/models/chronos-bolt-rte<br/>(Poids du modèle Fine-Tuned)"]
            LogFile["backend/pipeline.log<br/>(Journal d'exécution)"]
            PlotFile["backend/latest_forecast.png<br/>(Graphique de prévision)"]
        end

        PortMapping["Port 5432:5432<br/>(Accès Admin local via DBeaver / pgAdmin)"]
    end

    subgraph DockerBridge ["🐳 Docker Engine (Réseau Interne Virtuel)"]
        subgraph PostgresContainer ["Conteneur : energy_postgres"]
            PG["PostgreSQL 16 Alpine<br/>Port interne : 5432<br/>Healthcheck: pg_isready"]
            PGVol[("Volume Docker Nommé :<br/>postgres_energy_data<br/>(Persistance physique des tables)")]
            PG --- PGVol
        end

        subgraph PipelineContainer ["Conteneur : energy_pipeline"]
            App["Python 3.13 Debian Slim<br/>+ uv + libgomp1<br/>Point d'entrée : uv run rte-energy"]
        end
    end

    %% Liaisons de volumes et réseau
    ModelsDir -.->|"Montage Volume (Lecture)"| App
    App -.->|"Montage Volume (Écriture)"| LogFile
    App -.->|"Montage Volume (Écriture)"| PlotFile
    Env -.->|"Injection variables d'env"| App
    Env -.->|"Injection variables d'env"| PG

    PortMapping --- PG
    App ==>|"Connexion TCP interne (DB_HOST=postgres:5432)"| PG

    classDef host fill:#f1f5f9,stroke:#64748b,stroke-width:2px,color:#334155;
    classDef container fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e40af;
    classDef volume fill:#fef9c3,stroke:#ca8a04,stroke-width:2px,color:#854d0e;

    class Host host;
    class PostgresContainer,PipelineContainer container;
    class PGVol volume;
```

### 💡 Pourquoi cette organisation de volumes ?
1. **Poids du modèle (`./backend/models`) :** Le modèle fine-tuné pèse ~200 Mo. Au lieu de l'intégrer en dur dans l'image Docker (ce qui alourdirait le build à chaque modification de code), il est monté à la volée.
2. **Sorties (`pipeline.log`, `latest_forecast.png`) :** Dès que le conteneur calcule la prévision, le fichier image apparaît directement sur votre bureau Windows sans nécessiter de commande `docker cp`.
3. **Persistance (`postgres_energy_data`) :** Même si vous éteignez, recréez ou supprimez vos conteneurs, votre historique de données et vos prévisions ne sont **jamais perdus**.

---

## 3. Cycle de Vie Quotidien & Séquence d'Exécution (Orchestrateur)

Quand la commande `uv run rte-energy` (ou le conteneur Docker) démarre, l'orchestrateur [`pipeline.py`](file:///e:/Projects/QRA/rte_energie/backend/src/rte_energy/pipeline.py) exécute 4 étapes séquentielles :

```mermaid
sequenceDiagram
    autonumber
    actor Cron as Planificateur / Utilisateur
    participant Orch as pipeline.py (Orchestrateur)
    participant RTE as API RTE France
    participant Meteo as API Open-Meteo
    participant DB as PostgreSQL (energy_db)
    participant DBT as dbt Core
    participant AI as Modèle Chronos-Bolt RTE

    Note over Cron, Orch: Déclenchement automatique quotidien (ex: 06h00)
    Cron ->> Orch: uv run rte-energy

    rect rgb(224, 242, 254)
        Note over Orch, RTE: Étape 1 : Ingestion RTE
        Orch ->> RTE: Requête OAuth2 + Récupération consommations J à J+2
        RTE -->> Orch: Flux JSON des puissances (MW)
        Orch ->> DB: INSERT INTO consumption_forecast ON CONFLICT DO UPDATE
    end

    rect rgb(254, 243, 199)
        Note over Orch, Meteo: Étape 2 : Ingestion Météo
        Orch ->> Meteo: Récupération Température (°C) & Vent (km/h)
        Meteo -->> Orch: Flux météo horaire
        Orch ->> DB: INSERT INTO weather ON CONFLICT DO UPDATE
    end

    rect rgb(220, 252, 231)
        Note over Orch, DBT: Étape 3 : Transformations dbt
        Orch ->> DBT: Exécution de 'dbt run'
        DBT ->> DB: Recalcule les vues stg_ et matérialise fct_national_consumption
        DB -->> DBT: Tables analytiques à jour
        DBT -->> Orch: ✅ Modèles dbt compilés et validés
    end

    rect rgb(237, 233, 254)
        Note over Orch, AI: Étape 4 : Inférence IA de Production (predict.py)
        Orch ->> DB: SELECT 512 derniers points historiques
        DB -->> Orch: Série temporelle nettoyée
        Orch ->> AI: Passage du contexte dans Chronos-Bolt
        AI -->> Orch: Prévisions 96 pas de 15 min (q10, q50, q90)
        Orch ->> DB: INSERT INTO model_forecasts ON CONFLICT DO UPDATE
        Orch ->> Orch: Génère et sauvegarde latest_forecast.png
    end

    Note over Orch, Cron: Fin du cycle (durée moyenne : 15 à 30 secondes)
```

---

## 4. Schéma de Données (ELT & Modèles dbt)

Le schéma ci-dessous illustre comment les données brutes sont transformées et reliées entre elles :

```mermaid
erDiagram
    %% Tables Brutes (Schema public)
    consumption_forecast {
        SERIAL id PK
        TIMESTAMPTZ start_date
        TIMESTAMPTZ end_date
        FLOAT value_mw
        VARCHAR production_type
        VARCHAR forecast_type
        VARCHAR sub_type
        TIMESTAMPTZ updated_at
    }

    weather {
        SERIAL id PK
        TIMESTAMPTZ timestamp
        FLOAT temperature_c
        FLOAT wind_speed
        TIMESTAMPTZ updated_at
    }

    %% Vues Staging (Schema analytics)
    stg_consumption {
        INT forecast_id
        TIMESTAMPTZ start_date
        TIMESTAMPTZ end_date
        FLOAT value_mw
        VARCHAR production_type
        VARCHAR forecast_type
    }

    stg_weather {
        INT weather_id
        TIMESTAMPTZ observation_time
        FLOAT temperature_c
        FLOAT wind_speed_kmh
    }

    %% Tables Marts (Schema analytics)
    fct_national_consumption {
        TIMESTAMPTZ start_date PK
        FLOAT value_mw
    }

    fct_energy_features {
        TIMESTAMPTZ observation_hour PK
        FLOAT consumption_mw
        FLOAT temperature_c
        FLOAT wind_speed_kmh
        INT hour_of_day
        INT day_of_week
        INT is_weekend
        INT month
    }

    %% Table de Prédictions IA
    model_forecasts {
        SERIAL id PK
        TIMESTAMPTZ target_date
        FLOAT forecast_mw
        FLOAT lower_bound_mw
        FLOAT upper_bound_mw
        VARCHAR model_name
        TIMESTAMPTZ created_at
    }

    %% Relations dbt
    consumption_forecast ||--o{ stg_consumption : "dbt source"
    weather ||--o{ stg_weather : "dbt source"
    stg_consumption ||--o{ fct_national_consumption : "filtre AGGREGATED_CPC D-1"
    stg_consumption ||--o{ fct_energy_features : "moyenne horaire"
    stg_weather ||--o{ fct_energy_features : "jointure temporelle"
    fct_national_consumption ||--o{ model_forecasts : "alimente le modèle IA"
```

---

## 5. Fonctionnement Interne du Module d'Inférence (`predict.py`)

Comment le modèle **Chronos-Bolt Fine-Tuned** transforme le passé en prévisions futures :

```mermaid
flowchart TD
    subgraph Inputs ["Historique Contexte (512 points = 5.3 jours)"]
        H["[ 45 200 MW, 48 100 MW, ... , 54 300 MW ]<br/>(Dernier point connu : T_last)"]
    end

    subgraph BoltArch ["Modèle Amazon Chronos-Bolt Small (Fine-Tuned RTE)"]
        Norm["1. Normalisation par la moyenne locale (divisé par μ)"]
        Patch["2. Patching (regroupement par blocs temporels)"]
        Transf["3. Transformer Encoder-Decoder avec poids spécialisés RTE"]
        DeNorm["4. Dé-normalisation (remise à l'échelle en MW réels)"]
    end

    subgraph OutputForecast ["Sortie Prédictive (96 créneaux futurs de 15 minutes)"]
        Q50["Prédiction Médiane (q50)<br/>👉 La trajectoire centrale la plus probable"]
        Q10["Borne Basse (q10)<br/>👉 Scénario froid / basse conso (80% confiance)"]
        Q90["Borne Haute (q90)<br/>👉 Scénario pic / haute conso (80% confiance)"]
    end

    H --> Norm --> Patch --> Transf --> DeNorm
    DeNorm --> Q50
    DeNorm --> Q10
    DeNorm --> Q90
```

---

*Document d'architecture généré pour le projet RTE Energy Pipeline.*
