/**
 * ==============================================================================
 * MODULE TYPESCRIPT : frontend/src/types/energy.ts
 * OBJECTIF : Interfaces et types stricts pour les données du réseau RTE,
 *            les métriques éCO2mix et les prévisions des modèles IA.
 * ==============================================================================
 */

/**
 * Statut de connectivité du système et de la base de données.
 */
export interface SystemStatus {
    status: "online" | "degraded";
    database_connected: boolean;
    last_consumption_time: string | null;
    records: {
        consumption_records: number;
        forecast_records: number;
        weather_records: number;
    };
    models: {
        chronos_bolt_fine_tuned: boolean;
        lightgbm_multivarié: boolean;
    };
}

/**
 * Indicateurs clés de performance (KPIs) en temps réel inspirés d'éCO2mix.
 */
export interface KpiData {
    current_consumption_mw: number;
    current_time: string;
    selected_date?: string | null;
    delta_24h_mw: number;
    delta_24h_pct: number;
    day_peak: {
        value_mw: number;
        time: string;
    };
    day_low: {
        value_mw: number;
        time: string;
    };
    weather: {
        temperature_c: number;
        wind_speed_kmh: number;
        thermosensitive_mw: number;
        gradient_mw_per_degree: number;
    };
    model_champion: {
        name: string;
        wape_pct: number;
        mae_mw: number;
        rmse_mw: number;
        gain_vs_baseline_pct: number;
    };
}

/**
 * Point d'observation réel quart-horaire de la consommation nationale.
 */
export interface ConsumptionPoint {
    timestamp: string;
    time_label: string;
    value_mw: number;
}

/**
 * Réponse de l'API pour l'historique de consommation.
 */
export interface ConsumptionHistoryResponse {
    requested_hours: number;
    total_points: number;
    data: ConsumptionPoint[];
}

/**
 * Point de prévision issu d'un modèle avec intervalle de confiance quantile.
 */
export interface ForecastPoint {
    timestamp: string;
    time_label: string;
    forecast_mw: number;
    lower_bound_mw: number;
    upper_bound_mw: number;
}

/**
 * Point de prévision simple (ex: RTE D-1 ou Baseline).
 */
export interface SimpleForecastPoint {
    timestamp: string;
    time_label: string;
    value_mw: number;
}

/**
 * Réponse de l'API pour les prévisions futures à 24h.
 */
export interface ForecastsResponse {
    chronos: ForecastPoint[];
    rte_d1: SimpleForecastPoint[];
    baseline_j1: SimpleForecastPoint[];
}

/**
 * Entrée du tableau comparatif officiel de benchmark.
 */
export interface BenchmarkModel {
    id: string;
    name: string;
    category: string;
    mae_mw: number;
    rmse_mw: number;
    mape_pct: number;
    wape_pct: number;
    badge: string;
    badge_class: string;
}

/**
 * Réponse de l'API pour le benchmark des modèles.
 */
export interface BenchmarkResponse {
    models: BenchmarkModel[];
}
