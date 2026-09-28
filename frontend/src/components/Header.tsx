import React from "react";
import { Zap, RefreshCw, LogIn, LogOut, ShieldAlert } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { RoleBadge } from "./RoleBadge";

interface HeaderProps {
  lastUpdated: string | null;
  isLoading: boolean;
  onRefresh: () => void;
  onOpenLogin: () => void;
  showAdminPanel: boolean;
  onToggleAdminPanel: () => void;
}

/**
 * En-tête compact et optimisé éCO2mix avec authentification JWT, statut et actualisation.
 */
export const Header: React.FC<HeaderProps> = ({
  lastUpdated,
  isLoading,
  onRefresh,
  onOpenLogin,
  showAdminPanel,
  onToggleAdminPanel
}) => {
  const { user, isAuthenticated, logout } = useAuth();

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
    <header className="header-container compact-header" id="main-header">
      {/* 1. Logo & Titre Compact */}
      <div className="header-left">
        <div className="logo-wrapper">
          <div className="logo-icon-box">
            <Zap className="logo-bolt-icon" size={20} />
          </div>
          <div>
            <div className="logo-title-row">
              <h1 className="logo-title">
                éCO2mix <span className="logo-badge">IA PREDICT</span>
              </h1>
              <span className="logo-tagline">• RTE France</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Statut Réseau, Horodatage et Actions Utilisateur */}
      <div className="header-right">
        {/* Indicateur de direct réseau compact */}
        <div className="live-status-pill compact-pill" id="live-status-indicator">
          <span className="pulsing-dot"></span>
          <span className="status-label">DIRECT RÉSEAU</span>
        </div>

        {/* Horodatage compact */}
        <div className="timestamp-box compact-timestamp">
          <span className="time-label">Dernière mesure :</span>
          <span className="time-value" id="last-update-time">{formattedDate}</span>
        </div>

        {/* Bouton d'actualisation */}
        <button
          className="btn-refresh compact-btn"
          id="btn-refresh"
          onClick={onRefresh}
          disabled={isLoading}
          title="Actualiser les données"
        >
          <RefreshCw size={14} className={isLoading ? "spinning" : ""} />
          <span>{isLoading ? "Sync..." : "Actualiser"}</span>
        </button>

        {/* Authentification & Profil */}
        <div className="header-auth-section">
          {isAuthenticated && user ? (
            <div className="user-profile-menu">
              <div className="user-profile-info">
                <span className="user-full-name">{user.full_name || user.email.split("@")[0]}</span>
                <RoleBadge role={user.role} />
              </div>

              {/* Accès Panneau Admin / Analyste */}
              {(user.role === "admin" || user.role === "analyst") && (
                <button
                  className={`btn-toggle-admin compact-btn ${showAdminPanel ? "active" : ""}`}
                  onClick={onToggleAdminPanel}
                  title="Ouvrir le panneau RBAC & MLOps"
                >
                  <ShieldAlert size={14} />
                  <span>{user.role === "admin" ? "Admin" : "Analyste"}</span>
                </button>
              )}

              {/* Bouton Déconnexion */}
              <button
                className="btn-auth-logout compact-btn"
                onClick={logout}
                title="Déconnexion"
              >
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <button
              className="btn-auth-login compact-btn"
              onClick={onOpenLogin}
              title="Connexion / Inscription"
            >
              <LogIn size={14} />
              <span>Connexion</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
