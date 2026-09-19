-- ==============================================================================
-- MODÈLE MARTS : fct_energy_features.sql (Feature Store)
-- ==============================================================================
-- Rôle : Table analytique centrale unifiant la consommation électrique (RTE)
--        et les relevés météo (Open-Meteo) au pas horaire, enrichie de
--        variables calendaires (Feature Engineering) pour le Machine Learning.
--
-- Matérialisation : TABLE physique dans PostgreSQL (schéma analytics)
-- ==============================================================================

WITH consumption_hourly AS (
    -- Étape 1 : Ré-échantillonnage de la consommation au pas horaire
    -- On fait la moyenne des 4 créneaux de 15 min pour chaque heure
    SELECT
        date_trunc('hour', start_date) AS observation_hour,
        ROUND(AVG(value_mw)::numeric, 2) AS consumption_mw
    FROM {{ ref('stg_consumption') }}
    WHERE production_type = 'AGGREGATED_CPC'
      AND forecast_type = 'D-1'
    GROUP BY date_trunc('hour', start_date)
),

weather_hourly AS (
    -- Étape 2 : Récupération des données météo nettoyées du staging
    SELECT
        observation_time AS observation_hour,
        temperature_c,
        wind_speed_kmh
    FROM {{ ref('stg_weather') }}
),

joined_features AS (
    -- Étape 3 : Jointure temporelle exacte entre énergie et météo
    SELECT
        c.observation_hour,
        c.consumption_mw,
        w.temperature_c,
        w.wind_speed_kmh,
        
        -- Feature Engineering Calendaire :
        -- 1. Heure de la journée (0 à 23) pour capter le cycle journalier
        EXTRACT(HOUR FROM c.observation_hour)::int AS hour_of_day,
        
        -- 2. Jour de la semaine (1 = Lundi, 7 = Dimanche selon le standard ISO)
        EXTRACT(ISODOW FROM c.observation_hour)::int AS day_of_week,
        
        -- 3. Indicateur Week-end (1 si Samedi/Dimanche, 0 si jour ouvré)
        CASE 
            WHEN EXTRACT(ISODOW FROM c.observation_hour) IN (6, 7) THEN 1 
            ELSE 0 
        END AS is_weekend,
        
        -- 4. Mois de l'année (1 à 12) pour capter la saisonnalité hiver/été
        EXTRACT(MONTH FROM c.observation_hour)::int AS month
    FROM consumption_hourly c
    LEFT JOIN weather_hourly w 
        ON c.observation_hour = w.observation_hour
)

-- Requête finale renvoyée par le modèle (JAMAIS de point-virgule à la fin en dbt !)
SELECT * 
FROM joined_features
ORDER BY observation_hour ASC
