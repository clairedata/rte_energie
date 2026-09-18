-- ==============================================================================
-- MODÈLE STAGING : stg_weather.sql
-- ==============================================================================
-- Rôle : Première couche de nettoyage pour les données météo Open-Meteo.
-- Matérialisation : VUE (définie dans dbt_project.yml sous staging: +materialized: view)
-- ==============================================================================

WITH source_data AS (
    -- Lecture de la table 'weather' déclarée dans sources.yml
    SELECT * 
    FROM {{ source('raw_energy', 'weather') }}
),

cleaned AS (
    SELECT
        -- Clé primaire renommée
        id AS weather_id,
        
        -- On normalise l'horodatage à l'heure exacte (ex: 2026-03-01 14:00:00+01)
        date_trunc('hour', timestamp) AS observation_time,
        
        -- Température en °C arrondie à 2 décimales
        ROUND(temperature_c::numeric, 2) AS temperature_c,
        
        -- Vitesse du vent en km/h arrondie à 2 décimales
        ROUND(wind_speed::numeric, 2) AS wind_speed_kmh,
        
        -- Date d'ingestion/mise à jour
        updated_at
    FROM source_data
    WHERE timestamp IS NOT NULL
)

-- Requête finale (JAMAIS de point-virgule à la fin en dbt !)
SELECT * FROM cleaned
