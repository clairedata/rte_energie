import React from "react";
import { Zap, RefreshCw } from "lucide-react";

interface HeaderProps {
  lastUpdated: string | null;
  isLoading: boolean;
  onRefresh: () => void;
}

/**
 * En-tête supérieur éCO2mix avec voyant live et bouton d'actualisation.
 */
export const Header: React.FC<HeaderProps> = ({ lastUpdated, isLoading, onRefresh }) => {
  const formattedDate = lastUpdated ? (() => {
    const dt = new Date(lastUpdated);
    return (
      dt.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) +
      " (" +
      dt.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }) +
      ")"
    );
  })() : "En attente...";

  return (
    <header className="header-container" id="main-header">
      <div className="header-left">
        <div className="logo-wrapper">
          <Zap className="logo-bolt-icon" size={28} />
          <div>
            <h1 className="logo-title">
              éCO2mix <span className="logo-badge">IA PREDICT</span>
            </h1>
            <p className="logo-subtitle">
              Réseau de Transport d'Électricité (RTE France) • Consommation & Modèles TSFM
            </p>
          </div>
        </div>
      </div>

      <div className="header-right">
        {/* Voyant vert clignotant de direct réseau */}
        <div className="live-status-pill" id="live-status-indicator">
          <span className="pulsing-dot"></span>
          <span className="status-label">DIRECT RÉSEAU RTE CONNECTÉ</span>
        </div>

        {/* Horodatage de la dernière synchronisation */}
        <div className="timestamp-box">
          <span className="time-label">Dernière mesure :</span>
          <span className="time-value" id="last-update-time">{formattedDate}</span>
        </div>

        {/* Bouton d'actualisation manuelle */}
        <button
          className="btn-refresh"
          id="btn-refresh"
          onClick={onRefresh}
          disabled={isLoading}
          title="Actualiser les données en direct"
        >
          <RefreshCw size={16} className={isLoading ? "spinning" : ""} />
          <span>{isLoading ? "Synchronisation..." : "Actualiser"}</span>
        </button>
      </div>
    </header>
  );
};
