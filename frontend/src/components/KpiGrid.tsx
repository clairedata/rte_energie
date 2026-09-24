import React from "react";
import { Zap, TrendingUp, TrendingDown, Thermometer, Wind } from "lucide-react";
import type { KpiData } from "../types/energy";
import { KpiCard } from "./KpiCard";

interface KpiGridProps {
  data: KpiData | null;
}

const frNum = new Intl.NumberFormat("fr-FR");

/**
 * Grille des 4 indicateurs de synthèse en direct (Style éCO2mix).
 */
export const KpiGrid: React.FC<KpiGridProps> = ({ data }) => {
  if (!data) {
    return (
      <section className="kpi-grid" aria-label="Chargement des indicateurs">
        {[1, 2, 3, 4].map((i) => (
          <article key={i} className="kpi-card">
            <div className="kpi-title">Chargement des données...</div>
          </article>
        ))}
      </section>
    );
  }

  const isUp = data.delta_24h_mw > 0;
  const isDown = data.delta_24h_mw < 0;
  const arrow = isUp ? "🔺" : isDown ? "🔻" : "➡️";
  const trendColor = isUp ? "text-accent-red" : isDown ? "text-accent-cyan" : "";

  // Extraction de l'heure exacte du relevé (ex: "23h45")
  let recordTime = "";
  if (data.current_time) {
    const match = data.current_time.match(/T(\d{2}):(\d{2})/);
    if (match) {
      recordTime = `${match[1]}h${match[2]}`;
    }
  }
  const currentTag = recordTime ? `Relevé de ${recordTime}` : (data.selected_date ? `Jour ${data.selected_date}` : "En direct");

  return (
    <section className="kpi-grid" aria-label="Indicateurs clés de consommation">
      {/* 1. Puissance Appelée */}
      <KpiCard
        id="kpi-current"
        isPrimary={true}
        icon={<Zap size={18} />}
        title="Puissance Appelée"
        tag={currentTag}
        value={frNum.format(Math.round(data.current_consumption_mw))}
        unit="MW"
        subContent={
          <div className="kpi-trend" id="kpi-current-trend">
            <span className="trend-icon">{arrow}</span>
            <span className={`trend-text ${trendColor}`}>
              {isUp ? "+" : ""}{frNum.format(Math.round(data.delta_24h_mw))} MW (
              {isUp ? "+" : ""}{data.delta_24h_pct.toFixed(1)}%) vs J-1
            </span>
          </div>
        }
      />

      {/* 2. Pic Journalier */}
      <KpiCard
        id="kpi-peak"
        icon={<TrendingUp size={18} />}
        title="Pic Journalier (Pointe)"
        tag={data.day_peak.time}
        value={frNum.format(Math.round(data.day_peak.value_mw))}
        unit="MW"
        valueColorClass="text-accent-red"
        subContent={<p className="kpi-subtext">Pointe d'appel maximale observée ou estimée</p>}
      />

      {/* 3. Creux Nocturne */}
      <KpiCard
        id="kpi-low"
        icon={<TrendingDown size={18} />}
        title="Creux Nocturne"
        tag={data.day_low.time}
        value={frNum.format(Math.round(data.day_low.value_mw))}
        unit="MW"
        valueColorClass="text-accent-cyan"
        subContent={<p className="kpi-subtext">Consommation socle d'heures creuses</p>}
      />

      {/* 4. Météo & Thermosensibilité */}
      <KpiCard
        id="kpi-weather"
        icon={<Thermometer size={18} />}
        title="Météo & Thermosensibilité"
        tag="France"
        value={data.weather.temperature_c.toFixed(1)}
        unit="°C"
        valueColorClass="text-accent-yellow"
        subContent={
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4, color: "var(--text-secondary)" }}>
              <Wind size={14} />
              <span>{Math.round(data.weather.wind_speed_kmh)} km/h</span>
            </div>
            <div className="kpi-thermo-badge" id="kpi-thermo-badge">
              <span>Effet froid : <strong>{frNum.format(Math.round(data.weather.thermosensitive_mw))} MW</strong></span>
            </div>
          </div>
        }
      />
    </section>
  );
};
