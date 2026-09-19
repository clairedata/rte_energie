-- ==============================================================================
-- MODÈLE MARTS : fct_national_consumption.sql
-- ==============================================================================
-- Rôle : Table analytique centrale de la consommation nationale électrique à J-1.
--        Ce modèle prend les données nettoyées du staging, applique les filtres
--        métiers ('AGGREGATED_CPC', 'D-1') et calcule la moyenne par créneau.
--
-- Matérialisation : TABLE physique dans PostgreSQL (définie dans dbt_project.yml)
-- C'est cette table que Python (baseline.py, chronos_predict.py) va lire directement !
-- ==============================================================================

WITH staging_consumption AS (
    -- On fait référence au modèle de staging via la macro ref('stg_consumption')
    -- dbt comprend ainsi que ce modèle dépend de stg_consumption (Lineage Graph)
    SELECT * 
    FROM {{ ref('stg_consumption') }}
),

national_consumption_d1 AS (
    SELECT
        start_date,
        -- On moyenne les éventuelles révisions pour garantir 1 point unique par quart d'heure
        ROUND(AVG(value_mw)::numeric, 2) AS value_mw
    FROM staging_consumption
    -- Règle métier : Consommation globale nationale à l'horizon J-1
    WHERE production_type = 'AGGREGATED_CPC'
      AND forecast_type = 'D-1'
    GROUP BY start_date
)

-- Requête finale renvoyant la série temporelle triée par ordre chronologique
SELECT 
    start_date,
    value_mw
FROM national_consumption_d1
ORDER BY start_date ASC
