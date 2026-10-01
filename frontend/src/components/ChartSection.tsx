import React, { useEffect, useRef, useState } from "react";
import { Chart, registerables } from "chart.js";
import type { ChartData, ChartOptions } from "chart.js";
import { Calendar, Check, RotateCcw } from "lucide-react";
import type { ConsumptionPoint, ForecastsResponse } from "../types/energy";

// Enregistrement exhaustif des composants, échelles et contrôleurs Chart.js
Chart.register(...registerables);

interface ChartSectionProps {
  history: ConsumptionPoint[];
  forecasts: ForecastsResponse | null;
  selectedDate: string;
  latestDate?: string;
  onDateApply: (date: string) => void;
  isLoading: boolean;
}

const frNum = new Intl.NumberFormat("fr-FR");

/**
 * Section graphique éCO2mix principale avec sélecteur de date débloqué et dynamique.
 */
export const ChartSection: React.FC<ChartSectionProps> = ({
  history,
  forecasts,
  selectedDate,
  latestDate,
  onDateApply,
  isLoading
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartInstanceRef = useRef<Chart | null>(null);

  const activeLatest = latestDate || selectedDate || new Date().toISOString().slice(0, 10);

  // État local de la date saisie dans le calendrier avant clic sur "Appliquer"
  const [inputDate, setInputDate] = useState<string>(selectedDate || activeLatest);

  // Synchroniser la date saisie si selectedDate change depuis l'extérieur
  useEffect(() => {
    if (selectedDate) {
      setInputDate(selectedDate);
    }
  }, [selectedDate]);

  // Visibilité des séries
  const [visibleSeries, setVisibleSeries] = useState<{ [key: string]: boolean }>({
    real: true,
    chronos: true,
    confidence: true,
    rteD1: true,
    baseline: true
  });

  const isLiveMode = (selectedDate === activeLatest || !selectedDate);

  const toggleSeries = (key: string) => {
    setVisibleSeries(prev => {
      const next = { ...prev, [key]: !prev[key] };
      if (chartInstanceRef.current) {
        if (key === "real") chartInstanceRef.current.setDatasetVisibility(0, next.real);
        if (key === "chronos") chartInstanceRef.current.setDatasetVisibility(1, next.chronos);
        if (key === "confidence") {
          chartInstanceRef.current.setDatasetVisibility(2, next.confidence);
          chartInstanceRef.current.setDatasetVisibility(3, next.confidence);
        }
        if (key === "rteD1") chartInstanceRef.current.setDatasetVisibility(4, next.rteD1);
        if (key === "baseline") chartInstanceRef.current.setDatasetVisibility(5, next.baseline);
        chartInstanceRef.current.update();
      }
      return next;
    });
  };

  // Création et mise à jour du graphique Chart.js
  useEffect(() => {
    if (!canvasRef.current) return;

    // Préparation des données dans une timeline unifiée continue
    const labels: string[] = [];
    const realData: (number | null)[] = [];
    const chronosData: (number | null)[] = [];
    const highBoundData: (number | null)[] = [];
    const lowBoundData: (number | null)[] = [];
    const rteD1Data: (number | null)[] = [];
    const baselineData: (number | null)[] = [];

    const hasChronos = Boolean(forecasts?.chronos && forecasts.chronos.length > 0);

    // 1. Ajout de l'historique réel (48h observées jusqu'à aujourd'hui 23:45)
    history.forEach((pt) => {
      labels.push(pt.time_label);
      realData.push(pt.value_mw);
      chronosData.push(null);
      highBoundData.push(null);
      lowBoundData.push(null);
      rteD1Data.push(null);
      baselineData.push(null);
    });

    // 2. Raccordement et ajout des prévisions à J+1 (Demain sur 24h)
    if (hasChronos && forecasts?.chronos) {
      if (history.length > 0) {
        const lastRealVal = history[history.length - 1].value_mw;
        const lastIdx = history.length - 1;
        chronosData[lastIdx] = lastRealVal;
        highBoundData[lastIdx] = lastRealVal;
        lowBoundData[lastIdx] = lastRealVal;
        rteD1Data[lastIdx] = lastRealVal;
        baselineData[lastIdx] = lastRealVal;
      }

      forecasts.chronos.forEach((fc) => {
        labels.push(fc.time_label);
        realData.push(null);
        chronosData.push(fc.forecast_mw);
        highBoundData.push(fc.upper_bound_mw);
        lowBoundData.push(fc.lower_bound_mw);

        const d1Match = forecasts.rte_d1?.find((d) => d.time_label === fc.time_label);
        rteD1Data.push(d1Match ? d1Match.value_mw : null);

        const baseMatch = forecasts.baseline_j1?.find((b) => b.time_label === fc.time_label);
        baselineData.push(baseMatch ? baseMatch.value_mw : null);
      });
    }

    const chartData: ChartData<"line"> = {
      labels,
      datasets: [
        {
          label: "Consommation Réelle (RTE)",
          data: realData,
          borderColor: "#00f0ff", // Cyan Électrique néon très distinct
          backgroundColor: "rgba(0, 240, 255, 0.08)",
          borderWidth: 2.6,
          pointRadius: 0,
          pointHoverRadius: 6,
          pointHoverBackgroundColor: "#00f0ff",
          pointHoverBorderColor: "#ffffff",
          pointHoverBorderWidth: 2,
          tension: 0.25,
          hidden: !visibleSeries.real
        },
        {
          label: "Prévision IA Chronos-Bolt (Médiane q50)",
          data: chronosData,
          borderColor: "#ff9f1c", // Ambre / Orange vif très distinct du bleu
          backgroundColor: "transparent",
          borderWidth: 3.2,
          pointRadius: 0,
          pointHoverRadius: 6,
          pointHoverBackgroundColor: "#ff9f1c",
          pointHoverBorderColor: "#ffffff",
          pointHoverBorderWidth: 2,
          tension: 0.25,
          hidden: !visibleSeries.chronos
        },
        {
          label: "Borne Haute (q90)",
          data: highBoundData,
          borderColor: "rgba(255, 159, 28, 0.35)",
          borderWidth: 1,
          borderDash: [3, 3],
          pointRadius: 0,
          fill: false,
          tension: 0.25,
          hidden: !visibleSeries.confidence
        },
        {
          label: "Intervalle de Confiance 80% (q10 - q90)",
          data: lowBoundData,
          borderColor: "rgba(255, 159, 28, 0.35)",
          borderWidth: 1,
          borderDash: [3, 3],
          backgroundColor: "rgba(255, 159, 28, 0.14)", // Remplissage ambré translucide
          fill: "-1",
          pointRadius: 0,
          tension: 0.25,
          hidden: !visibleSeries.confidence
        },
        {
          label: "Prévision Officielle RTE (J-1)",
          data: rteD1Data,
          borderColor: "#10b981", // Vert Émeraude officiel
          backgroundColor: "transparent",
          borderWidth: 2.4,
          borderDash: [6, 4],
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: "#10b981",
          tension: 0.2,
          hidden: !visibleSeries.rteD1
        },
        {
          label: "Baseline Naïve (J-1)",
          data: baselineData,
          borderColor: "#ef4444", // Rouge Corail
          backgroundColor: "transparent",
          borderWidth: 1.8,
          borderDash: [3, 3],
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: "#ef4444",
          tension: 0.15,
          hidden: !visibleSeries.baseline
        }
      ]
    };

    // Plugin personnalisé pour tracer la ligne de séparation verticale nette
    const verticalSeparationPlugin = {
      id: "verticalSeparation",
      afterDraw: (chart: any) => {
        if (history.length > 0 && hasChronos && forecasts?.chronos?.length) {
          const ctx = chart.ctx;
          const xAxis = chart.scales.x;
          const yAxis = chart.scales.y;
          const splitIndex = history.length - 1;
          const xPos = xAxis.getPixelForTick(splitIndex);

          if (xPos && xPos >= xAxis.left && xPos <= xAxis.right) {
            ctx.save();

            // 1. Tracé de la ligne verticale séparatrice pointillée
            ctx.beginPath();
            ctx.setLineDash([6, 5]);
            ctx.strokeStyle = "rgba(0, 240, 255, 0.7)";
            ctx.lineWidth = 2;
            ctx.moveTo(xPos, yAxis.top);
            ctx.lineTo(xPos, yAxis.bottom);
            ctx.stroke();

            // 2. Badge supérieur de repère temporel
            const badgeText = "⚡ PRÉVISIONS DEMAIN (J+1)";
            ctx.font = "bold 10px 'Inter', sans-serif";
            const textWidth = ctx.measureText(badgeText).width;
            const badgeW = textWidth + 20;
            const badgeH = 22;
            const badgeX = Math.max(xAxis.left + 5, Math.min(xPos - badgeW / 2, xAxis.right - badgeW - 5));
            const badgeY = yAxis.top + 6;

            // Fond du badge
            ctx.fillStyle = "rgba(10, 25, 47, 0.95)";
            ctx.strokeStyle = "#00f0ff";
            ctx.lineWidth = 1;
            ctx.beginPath();
            if (ctx.roundRect) {
              ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 4);
            } else {
              ctx.rect(badgeX, badgeY, badgeW, badgeH);
            }
            ctx.fill();
            ctx.stroke();

            // Texte du badge
            ctx.fillStyle = "#00f0ff";
            ctx.textAlign = "center";
            ctx.fillText(badgeText, badgeX + badgeW / 2, badgeY + 15);

            ctx.restore();
          }
        }
      }
    };

    const chartOptions: ChartOptions<"line"> = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(10, 25, 47, 0.96)",
          titleColor: "#f8fafc",
          titleFont: { family: "Outfit", size: 13, weight: "bold" },
          bodyColor: "#94a3b8",
          bodyFont: { family: "Inter", size: 12 },
          borderColor: "rgba(0, 240, 255, 0.35)",
          borderWidth: 1,
          padding: 12,
          boxPadding: 6,
          usePointStyle: true,
          callbacks: {
            label: (context) => {
              const val = context.parsed.y;
              if (val === null || val === undefined) return "";
              return ` ${context.dataset.label} : ${frNum.format(Math.round(val))} MW`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.04)" },
          ticks: {
            color: "#64748b",
            font: { family: "Inter", size: 11 },
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 12
          }
        },
        y: {
          position: "left",
          title: {
            display: true,
            text: "Puissance Appelée (MW)",
            color: "#94a3b8",
            font: { family: "Inter", size: 11, weight: "bold" }
          },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#64748b",
            font: { family: "Inter", size: 11 },
            callback: (val) => `${frNum.format(Number(val))} MW`
          }
        }
      }
    };

    // Nettoyer toute instance existante sur le canvas (gestion StrictMode)
    const existingChart = Chart.getChart(canvasRef.current);
    if (existingChart) {
      existingChart.destroy();
    }
    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
      chartInstanceRef.current = null;
    }

    try {
      chartInstanceRef.current = new Chart(canvasRef.current, {
        type: "line",
        data: chartData,
        options: chartOptions,
        plugins: [verticalSeparationPlugin]
      });
    } catch (e) {
      console.error("❌ Erreur d'initialisation Chart.js :", e);
    }

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
        chartInstanceRef.current = null;
      }
    };
  }, [history, forecasts, selectedDate]);

  const handleApply = () => {
    if (inputDate) {
      onDateApply(inputDate);
    }
  };

  const formattedDate = selectedDate.split("-").reverse().join("/");

  return (
    <section className="chart-section" aria-label="Graphique chronologique de consommation">
      {/* Barre d'outils avec Calendrier et Sélecteur de date */}
      <div className="chart-toolbar">
        <div className="toolbar-left">
          <div className="title-with-badge">
            <h2 className="chart-title">
              {isLiveMode ? "Consommation Électrique & Prévisions Réseau" : `Consommation Observée & Prévisions pour le Lendemain`}
            </h2>
            <span className="live-chip">
              {isLiveMode ? "🔴 DIRECT RÉSEAU" : `📅 JOUR SÉLECTIONNÉ : ${formattedDate}`}
            </span>
          </div>
          <span className="chart-subtitle">
            Courbe réelle observée sur 48h raccordée aux prévisions des modèles à horizon 24 heures (Demain J+1)
          </span>
        </div>

        {/* 3. Sélecteur par Calendrier & Bouton Appliquer */}
        <div className="toolbar-right">
          <div className="calendar-filter-bar">
            <div className="calendar-input-group">
              <Calendar size={16} className="calendar-icon" />
              <label htmlFor="calendar-date-input" className="calendar-label">Date :</label>
              <input
                id="calendar-date-input"
                type="date"
                min="2026-01-01"
                max="2026-12-31"
                value={inputDate}
                onChange={(e) => setInputDate(e.target.value)}
                className="calendar-date-input"
                title="Sélectionner une date pour charger l'historique et les prévisions"
              />
            </div>

            <button
              className="btn-apply-date"
              id="btn-apply-date"
              onClick={handleApply}
              disabled={isLoading || !inputDate}
              title="Afficher les statistiques et la courbe pour cette date"
            >
              <Check size={14} />
              <span>Appliquer</span>
            </button>

            {selectedDate !== activeLatest && (
              <button
                className="btn-reset-date"
                onClick={() => {
                  setInputDate(activeLatest);
                  onDateApply(activeLatest);
                }}
                title="Revenir à la dernière date disponible"
              >
                <RotateCcw size={13} />
                <span>Dernier Direct</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Bannière de séparation visuelle Passé Réel | Futur Prévision */}
      <div className="chart-legend-banner">
        <div className="legend-chip chip-real">
          <span className="chip-dot dot-real"></span>
          <span><strong>Passé Réel (48h observées) :</strong> {history.length ? `${history[0]?.time_label || ""} ➔ ${history[history.length - 1]?.time_label || ""}` : "..."}</span>
        </div>
        {forecasts?.chronos && forecasts.chronos.length > 0 && (
          <>
            <span className="legend-divider">┊</span>
            <div className="legend-chip chip-forecast">
              <span className="chip-dot dot-chronos"></span>
              <span><strong>Demain (Prévisions 24h) :</strong> {`${forecasts.chronos[0]?.time_label || ""} ➔ ${forecasts.chronos[forecasts.chronos.length - 1]?.time_label || ""}`}</span>
            </div>
          </>
        )}
      </div>

      {/* Interrupteurs de visibilité des séries */}
      <div className="series-toggles" id="series-toggles">
        <span className="toggle-hint">Séries affichées :</span>

        {/* 1. Consommation réelle en cyan néon */}
        <button
          className={`toggle-pill ${visibleSeries.real ? "active" : ""}`}
          onClick={() => toggleSeries("real")}
        >
          <span className="pill-dot dot-real"></span>
          <span>Consommation Réelle (RTE)</span>
        </button>

        {/* 2. Prévision Chronos en ambre/orange vif */}
        <button
          className={`toggle-pill ${visibleSeries.chronos ? "active" : ""}`}
          onClick={() => toggleSeries("chronos")}
        >
          <span className="pill-dot dot-chronos"></span>
          <span>Prévision IA (Chronos-Bolt Médiane)</span>
        </button>

        {/* 3. Intervalle de confiance 80% */}
        <button
          className={`toggle-pill ${visibleSeries.confidence ? "active" : ""}`}
          onClick={() => toggleSeries("confidence")}
        >
          <span className="pill-dot dot-confidence"></span>
          <span>Intervalle de Confiance 80%</span>
        </button>

        {/* 4. Prévision officielle RTE D-1 en vert */}
        <button
          className={`toggle-pill ${visibleSeries.rteD1 ? "active" : ""}`}
          onClick={() => toggleSeries("rteD1")}
          title="Prévision officielle du modèle RTE D-1"
        >
          <span className="pill-dot dot-rte-d1"></span>
          <span>Prévision Officielle RTE (J-1)</span>
        </button>

        {/* 5. Baseline naïve en rouge */}
        <button
          className={`toggle-pill ${visibleSeries.baseline ? "active" : ""}`}
          onClick={() => toggleSeries("baseline")}
        >
          <span className="pill-dot dot-baseline"></span>
          <span>Baseline Naïve (J-1)</span>
        </button>
      </div>

      {/* Conteneur Canvas */}
      <div className="chart-canvas-container">
        <canvas ref={canvasRef} id="consumptionChart"></canvas>
        {isLoading && (
          <div className="chart-loader">
            <div className="spinner"></div>
            <span>Chargement des données du réseau RTE...</span>
          </div>
        )}
      </div>
    </section>
  );
};
