import { useState, useEffect, useCallback } from "react";
import { Header } from "./components/Header";
import { KpiGrid } from "./components/KpiGrid";
import { ChartSection } from "./components/ChartSection";
import { ThermosensitivityCard } from "./components/ThermosensitivityCard";
import { BenchmarkTable } from "./components/BenchmarkTable";
import { Footer } from "./components/Footer";
import { LoginModal } from "./components/LoginModal";
import { AdminPanel } from "./components/AdminPanel";
import { useAuth } from "./context/AuthContext";
import { getAuthHeaders } from "./services/auth";
import type {
  KpiData,
  ConsumptionPoint,
  ForecastsResponse,
  BenchmarkModel
} from "./types/energy";

export function App() {
  const { user } = useAuth();
  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [history, setHistory] = useState<ConsumptionPoint[]>([]);
  const [forecasts, setForecasts] = useState<ForecastsResponse | null>(null);
  const [benchmarkModels, setBenchmarkModels] = useState<BenchmarkModel[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("2026-09-27");
  const [latestAvailableDate, setLatestAvailableDate] = useState<string>("2026-09-27");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);

  // État des modals et panneaux RBAC
  const [isLoginModalOpen, setIsLoginModalOpen] = useState<boolean>(false);
  const [showAdminPanel, setShowAdminPanel] = useState<boolean>(false);

  // Fonction de chargement des données pour une date spécifique ou la date la plus récente
  const loadDataForDate = useCallback(async (dateToLoad?: string, showLoading = true) => {
    if (showLoading) setIsLoading(true);

    try {
      let targetDate = dateToLoad;

      // 1. Détecter dynamiquement la date la plus récente en base
      try {
        const statusRes = await fetch("/api/status", { headers: getAuthHeaders() });
        if (statusRes.ok) {
          const statusJson = await statusRes.json();
          if (statusJson.last_consumption_time) {
            const detected = statusJson.last_consumption_time.slice(0, 10);
            setLatestAvailableDate(detected);
            if (!targetDate) {
              targetDate = detected;
            }
          }
        }
      } catch {
        // Fallback
      }

      if (!targetDate) {
        targetDate = latestAvailableDate || "2026-09-27";
      }

      // Calcul de la date du lendemain (Demain J+1 à prédire)
      const [y, m, d] = targetDate.split("-").map(Number);
      const nextDay = new Date(Date.UTC(y, m - 1, d + 1));
      const tomorrowDate = nextDay.toISOString().slice(0, 10);

      // 2. URLs d'appels API : 48h d'historique réel jusqu'au jour J + prévisions à J+1 (demain)
      const kpiUrl = `/api/kpi?date=${targetDate}`;
      const histUrl = `/api/consumption/history?date=${targetDate}&hours=48`;
      const fcstUrl = `/api/consumption/forecasts?date=${tomorrowDate}`;

      const [kpiRes, histRes, fcstRes, benchRes] = await Promise.all([
        fetch(kpiUrl, { headers: getAuthHeaders() }),
        fetch(histUrl, { headers: getAuthHeaders() }),
        fetch(fcstUrl, { headers: getAuthHeaders() }),
        fetch("/api/benchmark", { headers: getAuthHeaders() })
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

      setSelectedDate(targetDate);
    } catch (err) {
      console.error("❌ Erreur lors du chargement des données :", err);
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, [latestAvailableDate]);

  // Chargement initial au démarrage
  useEffect(() => {
    loadDataForDate(undefined, true);

    // Rafraîchissement automatique toutes les 60 secondes
    const intervalId = setInterval(() => {
      setSelectedDate(current => {
        if (current) {
          loadDataForDate(current, false);
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
      {/* 1. En-tête éCO2mix avec authentification */}
      <Header
        lastUpdated={lastSyncTime}
        isLoading={isLoading}
        onRefresh={() => loadDataForDate(selectedDate, true)}
        onOpenLogin={() => setIsLoginModalOpen(true)}
        showAdminPanel={showAdminPanel}
        onToggleAdminPanel={() => setShowAdminPanel(prev => !prev)}
      />

      {/* 2. Modal d'authentification JWT (Connexion & Inscription) */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />

      {/* 3. Contenu principal du dashboard */}
      <main className="dashboard-main" id="dashboard-content">
        {/* Panneau RBAC MLOps & Administration */}
        {(showAdminPanel || (user && user.role === "admin")) && (
          <AdminPanel onPipelineSuccess={() => loadDataForDate(undefined, true)} />
        )}

        {/* A. Grille des KPIs calculés pour la date sélectionnée */}
        <KpiGrid data={kpi} />

        {/* B. Grand graphique interactif avec calendrier et superposition des modèles */}
        <ChartSection
          history={history}
          forecasts={forecasts}
          selectedDate={selectedDate || latestAvailableDate}
          latestDate={latestAvailableDate}
          onDateApply={handleDateApply}
          isLoading={isLoading}
        />

        {/* C. Pédagogie Thermosensibilité & Benchmark officiel */}
        <section className="bottom-grid">
          <ThermosensitivityCard />
          <BenchmarkTable models={benchmarkModels} />
        </section>
      </main>

      {/* 4. Pied de page technique */}
      <Footer />
    </div>
  );
}

export default App;
