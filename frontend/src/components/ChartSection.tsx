import React, { useEffect, useRef, useState } from "react";
import { Chart, registerables } from "chart.js";
import type { ChartData, ChartOptions } from "chart.js";
import { Calendar, Check, RotateCcw } from "lucide-react";
import type { ConsumptionPoint, ForecastsResponse, ForecastPoint } from "../types/energy";

// Enregistrement exhaustif des composants, échelles et contrôleurs Chart.js
Chart.register(...registerables);

interface ChartSectionProps {
  history: ConsumptionPoint[];
  forecasts: ForecastsResponse | null;
  selectedDate: string;
  onDateApply: (date: string) => void;
  isLoading: boolean;
}

const frNum = new Intl.NumberFormat("fr-FR");

/**
 * Section graphique éCO2mix principale avec sélecteur de date,
 * séparation visuelle nette entre passé réel et prévisions, et couleurs distinctives.
 */
export const ChartSection: React.FC<ChartSectionProps> = ({
  history,
  forecasts,
  selectedDate,
  onDateApply,
  isLoading
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartInstanceRef = useRef<Chart | null>(null);

  // État local de la date saisie dans le calendrier avant clic sur "Appliquer"
  const [inputDate, setInputDate] = useState<string>(selectedDate);

  // Synchroniser la date saisie si selectedDate change depuis l'extérieur
  useEffect(() => {
    setInputDate(selectedDate);
  }, [selectedDate]);

  // Visibilité des séries (toutes actives par défaut pour permettre la comparaison)
  const [visibleSeries, setVisibleSeries] = useState<{ [key: string]: boolean }>({
    real: true,
    chronos: true,
    confidence: true,
    rteD1: true,
    baseline: true
  });

  const isLiveMode = (selectedDate === "2026-09-23");

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

    // Préparation des données
    const labels: string[] = [];
    const realData: (number | null)[] = [];
    const chronosData: (number | null)[] = [];
    const highBoundData: (number | null)[] = [];
    const lowBoundData: (number | null)[] = [];
    const rteD1Data: (number | null)[] = [];
    const baselineData: (number | null)[] = [];

    const hasChronos = Boolean(forecasts?.chronos && forecasts.chronos.length > 0);

    if (isLiveMode) {
      // 1. MODE DIRECT / TEMPS RÉEL (48h Passé Réel + 24h Futur Prévisions raccordés)
      history.forEach((pt) => {
        labels.push(pt.time_label);
        realData.push(pt.value_mw);
        chronosData.push(null);
        highBoundData.push(null);
        lowBoundData.push(null);
        rteD1Data.push(null);
        baselineData.push(null);
      });

      if (hasChronos && forecasts?.chronos) {
        // Raccordement visuel au dernier point réel
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
    } else {
      // 2. MODE HISTORIQUE / ARCHIVE : SUPERPOSITION DIRECTE DES 4 COURBES SUR LA MÊME JOURNÉE
      // Dictionnaires par étiquette horaire (ex: "17/09 14:00") pour un alignement quart-horaire parfait
      const chronosMap = new Map<string, ForecastPoint>();
      forecasts?.chronos?.forEach((fc) => chronosMap.set(fc.time_label, fc));

      const rteD1Map = new Map<string, number>();
      forecasts?.rte_d1?.forEach((d) => rteD1Map.set(d.time_label, d.value_mw));

      const baselineMap = new Map<string, number>();
      forecasts?.baseline_j1?.forEach((b) => baselineMap.set(b.time_label, b.value_mw));

      history.forEach((pt) => {
        labels.push(pt.time_label);
        realData.push(pt.value_mw);

        const fc = chronosMap.get(pt.time_label);
        if (fc) {
          chronosData.push(fc.forecast_mw);
          highBoundData.push(fc.upper_bound_mw);
          lowBoundData.push(fc.lower_bound_mw);
        } else {
          chronosData.push(null);
          highBoundData.push(null);
          lowBoundData.push(null);
        }

        const d1Val = rteD1Map.get(pt.time_label);
        rteD1Data.push(d1Val !== undefined ? d1Val : null);

        const baseVal = baselineMap.get(pt.time_label);
        baselineData.push(baseVal !== undefined ? baseVal : null);
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

    // Plugin personnalisé pour tracer la ligne de séparation verticale nette (uniquement en mode direct)
    const verticalSeparationPlugin = {
      id: "verticalSeparation",
      afterDraw: (chart: any) => {
        if (!isLiveMode) return;
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
            const badgeText = "⚡ DÉBUT PRÉVISIONS 24H";
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

  // Calcul dynamique de la précision des modèles sur la journée sélectionnée
  const dayMetrics = React.useMemo(() => {
    if (isLiveMode || !history.length || !forecasts?.chronos?.length) return null;

    let chronosAbsErr = 0;
    let baseAbsErr = 0;
    let totalReal = 0;
    let count = 0;
    let baseCount = 0;

    const chronosMap = new Map<string, number>();
    forecasts.chronos.forEach(c => chronosMap.set(c.time_label, c.forecast_mw));

    const baseMap = new Map<string, number>();
    forecasts.baseline_j1?.forEach(b => baseMap.set(b.time_label, b.value_mw));

    history.forEach(pt => {
      const real = pt.value_mw;
      totalReal += real;

      const cVal = chronosMap.get(pt.time_label);
      if (cVal !== undefined) {
        chronosAbsErr += Math.abs(real - cVal);
        count++;
      }

      const bVal = baseMap.get(pt.time_label);
      if (bVal !== undefined) {
        baseAbsErr += Math.abs(real - bVal);
        baseCount++;
      }
    });

    if (totalReal === 0 || count === 0) return null;

    const chronosWape = (chronosAbsErr / totalReal) * 100;
    const chronosMae = chronosAbsErr / count;
    const baseWape = baseCount > 0 ? (baseAbsErr / totalReal) * 100 : null;

    return {
      chronosWape: chronosWape.toFixed(1),
      chronosMae: Math.round(chronosMae),
      baseWape: baseWape ? baseWape.toFixed(1) : null
    };
  }, [isLiveMode, history, forecasts]);

  return (
    <section className="chart-section" aria-label="Graphique chronologique de consommation">
      {/* Barre d'outils avec Calendrier et Sélecteur de date */}
      <div className="chart-toolbar">
        <div className="toolbar-left">
          <div className="title-with-badge">
            <h2 className="chart-title">
              {isLiveMode ? "Consommation Électrique & Prévisions Réseau" : `Consommation et Comparatif Modèles du ${formattedDate}`}
            </h2>
            <span className="live-chip">
              {isLiveMode ? "🔴 DIRECT RÉSEAU" : `📅 JOUR DU ${formattedDate}`}
            </span>
          </div>
          <span className="chart-subtitle">
            {isLiveMode
              ? "Courbe réelle observée raccordée aux prévisions des modèles à horizon 24 heures"
              : "Superposition de la consommation réelle observée et des prédictions des modèles IA et RTE D-1"
            }
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
                min="2026-08-01"
                max="2026-09-23"
                value={inputDate}
                onChange={(e) => setInputDate(e.target.value)}
                className="calendar-date-input"
                title="Sélectionner une date entre le 01/08/2026 et le 23/09/2026"
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

            {selectedDate !== "2026-09-23" && (
              <button
                className="btn-reset-date"
                onClick={() => {
                  setInputDate("2026-09-23");
                  onDateApply("2026-09-23");
                }}
                title="Revenir à la dernière date en direct"
              >
                <RotateCcw size={13} />
                <span>Direct</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Bannière de séparation visuelle Passé Réel | Futur Prévision */}
      <div className="chart-legend-banner">
        {isLiveMode ? (
          <>
            <div className="legend-chip chip-real">
              <span className="chip-dot dot-real"></span>
              <span><strong>Passé Réel (Observé) :</strong> {history.length ? `${history[0]?.time_label || ""} ➔ ${history[history.length - 1]?.time_label || ""}` : "..."}</span>
            </div>
            {forecasts?.chronos && forecasts.chronos.length > 0 && (
              <>
                <span className="legend-divider">┊</span>
                <div className="legend-chip chip-forecast">
                  <span className="chip-dot dot-chronos"></span>
                  <span><strong>Futur (Prévisions 24h) :</strong> {`${forecasts.chronos[0]?.time_label || ""} ➔ ${forecasts.chronos[forecasts.chronos.length - 1]?.time_label || ""}`}</span>
                </div>
              </>
            )}
          </>
        ) : (
          <div className="legend-historical-wrapper">
            <div className="legend-chip chip-historical">
              <span className="chip-dot dot-real"></span>
              <span>
                <strong>Journée du {formattedDate} :</strong>
              </span>
            </div>
            {dayMetrics && (
              <div className="daily-accuracy-badges">
                <span className="accuracy-badge badge-chronos" title="Erreur relative de Chronos-Bolt sur cette journée">
                  <span className="dot-accuracy dot-chronos"></span>
                  Chronos-Bolt IA : <strong>WAPE {dayMetrics.chronosWape}%</strong> (MAE {dayMetrics.chronosMae} MW)
                </span>
                {dayMetrics.baseWape && (
                  <span className="accuracy-badge badge-baseline" title="Erreur de la Baseline Naïve sur cette journée">
                    <span className="dot-accuracy dot-baseline"></span>
                    Baseline J-1 : <strong>WAPE {dayMetrics.baseWape}%</strong>
                  </span>
                )}
              </div>
            )}
          </div>
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
