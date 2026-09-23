import { useState, useEffect, useCallback } from "react";
import { Header } from "./components/Header";
import { KpiGrid } from "./components/KpiGrid";
import { ChartSection } from "./components/ChartSection";
import { ThermosensitivityCard } from "./components/ThermosensitivityCard";
import { BenchmarkTable } from "./components/BenchmarkTable";
import { Footer } from "./components/Footer";
import type {
  KpiData,
  ConsumptionPoint,
  ForecastsResponse,
  BenchmarkModel
} from "./types/energy";

export function App() {
  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [history, setHistory] = useState<ConsumptionPoint[]>([]);
  const [forecasts, setForecasts] = useState<ForecastsResponse | null>(null);
  const [benchmarkModels, setBenchmarkModels] = useState<BenchmarkModel[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("2026-09-23");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);

  // Fonction de chargement des données pour une date spécifique
  const loadDataForDate = useCallback(async (date: string, showLoading = true) => {
    if (showLoading) setIsLoading(true);

    try {
      // 1. URLs adaptées selon si c'est la date en direct ou une archive
      const kpiUrl = date === "2026-09-23" ? "/api/kpi" : `/api/kpi?date=${date}`;
      const histUrl = date === "2026-09-23" 
        ? "/api/consumption/history?hours=48" 
        : `/api/consumption/history?date=${date}`;
      const fcstUrl = date === "2026-09-23" 
        ? "/api/consumption/forecasts" 
        : `/api/consumption/forecasts?date=${date}`;

      const [kpiRes, histRes, fcstRes, benchRes] = await Promise.all([
        fetch(kpiUrl),
        fetch(histUrl),
        fetch(fcstUrl),
        fetch("/api/benchmark")
      ]);

      if (kpiRes.ok) {
        const kpiJson: KpiData = await kpiRes.json();
        setKpi(kpiJson);
        setLastSyncTime(kpiJson.current_time);
      }

      if (histRes.ok) {
        const histJson = await histRes.json();
        setHistory(histJson.data || []);
      }

      if (fcstRes.ok) {
        const fcstJson: ForecastsResponse = await fcstRes.json();
        setForecasts(fcstJson);
      }

      if (benchRes.ok) {
        const benchJson = await benchRes.json();
        setBenchmarkModels(benchJson.models || []);
      }

      setSelectedDate(date);
    } catch (err) {
      console.error("❌ Erreur lors du chargement des données pour la date :", err);
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, []);

  // Chargement initial
  useEffect(() => {
    loadDataForDate("2026-09-23", true);

    // Rafraîchissement automatique toutes les 60 secondes en direct
    const intervalId = setInterval(() => {
      setSelectedDate(current => {
        if (current === "2026-09-23") {
          console.log("🔄 Auto-refresh des données en direct...");
          loadDataForDate("2026-09-23", false);
        }
        return current;
      });
    }, 60000);

    return () => clearInterval(intervalId);
  }, [loadDataForDate]);

  // Clic sur "Appliquer" dans le calendrier
  const handleDateApply = (date: string) => {
    loadDataForDate(date, true);
  };

  return (
    <div className="app-container">
      {/* 1. En-tête éCO2mix */}
      <Header
        lastUpdated={lastSyncTime}
        isLoading={isLoading}
        onRefresh={() => loadDataForDate(selectedDate, true)}
      />

      {/* 2. Contenu principal du dashboard */}
      <main className="dashboard-main" id="dashboard-content">
        {/* A. Grille des KPIs calculés pour la date sélectionnée */}
        <KpiGrid data={kpi} />

        {/* B. Grand graphique interactif avec calendrier et séparation nette */}
        <ChartSection
          history={history}
          forecasts={forecasts}
          selectedDate={selectedDate}
          onDateApply={handleDateApply}
          isLoading={isLoading}
        />

        {/* C. Pédagogie Thermosensibilité & Benchmark officiel */}
        <section className="bottom-grid">
          <ThermosensitivityCard />
          <BenchmarkTable models={benchmarkModels} />
        </section>
      </main>

      {/* 3. Pied de page technique */}
      <Footer />
    </div>
  );
}

export default App;
