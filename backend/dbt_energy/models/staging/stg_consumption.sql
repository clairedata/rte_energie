-- ==============================================================================
-- MODÈLE STAGING : stg_consumption.sql
-- ==============================================================================
-- Rôle : Première couche de nettoyage pour les données de consommation RTE.
-- Matérialisation : VUE (définie dans dbt_project.yml sous staging: +materialized: view)
-- ==============================================================================

WITH source_data AS (
    -- La macro source() permet à dbt d'associer ce modèle à la table brute
    -- déclarée dans models/staging/sources.yml (schema 'public', table 'consumption_forecast')
    SELECT * 
    FROM {{ source('raw_energy', 'consumption_forecast') }}
),

cleaned AS (
    SELECT
        -- On renomme la clé technique pour éviter toute confusion lors des futures jointures
        id AS forecast_id,
        
        -- Les horodatages de début et de fin du créneau (au pas de 15 minutes)
        start_date,
        end_date,
        
        -- Type de prévision (ex: AGGREGATED_CPC, SOLAR, WIND_ONSHORE)
        production_type,
        
        -- Horizon de prévision (CURRENT, D-1, D-2, D-3)
        forecast_type,
        
        -- Sous-type ou guichet de révision (ex: DA01, ID00, ou chaîne vide)
        COALESCE(sub_type, '') AS sub_type,
        
        -- Puissance en Mégawatts arrondie à 2 décimales
        ROUND(value_mw::numeric, 2) AS value_mw,
        
        -- Date de dernière mise à jour de l'enregistrement
        updated_at
    FROM source_data
    -- Règle de qualité : on ignore d'éventuelles valeurs aberrantes ou nulles
    WHERE value_mw IS NOT NULL 
      AND value_mw >= 0
)

-- Requête finale renvoyée par le modèle (JAMAIS de point-virgule à la fin en dbt !)
SELECT * FROM cleaned
