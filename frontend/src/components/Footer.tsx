import React from "react";

/**
 * Pied de page technique récapitulant les briques d'infrastructure.
 */
export const Footer: React.FC = () => {
  return (
    <footer className="footer-container" id="main-footer">
      <div className="footer-left">
        <span>⚡ <strong>RTE Energy Pipeline & Inférence IA</strong></span>
        <span>•</span>
        <span>Données certifiées <strong>RTE Data API</strong> & <strong>Open-Meteo</strong></span>
        <span>•</span>
        <span>Architecture ELT : <strong>PostgreSQL + dbt Core</strong></span>
      </div>
      <div className="footer-right">
        <span className="tech-tag">React 19</span>
        <span className="tech-tag">TypeScript</span>
        <span className="tech-tag">FastAPI</span>
        <span className="tech-tag">Chronos-Bolt</span>
        <span className="tech-tag">LightGBM</span>
        <span className="tech-tag">Chart.js</span>
      </div>
    </footer>
  );
};
