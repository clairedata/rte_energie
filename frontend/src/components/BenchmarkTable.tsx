import React from "react";
import { Trophy } from "lucide-react";
import type { BenchmarkModel } from "../types/energy";

interface BenchmarkTableProps {
  models: BenchmarkModel[];
}

const frNum = new Intl.NumberFormat("fr-FR");

/**
 * Tableau comparatif officiel du benchmark des modèles IA et statistiques.
 */
export const BenchmarkTable: React.FC<BenchmarkTableProps> = ({ models }) => {
  return (
    <article className="info-card">
      <div className="info-header">
        <Trophy size={20} className="text-accent-yellow" />
        <h3 className="info-title">Benchmark Comparatif des Modèles</h3>
      </div>
      <div className="info-body">
        <div className="table-responsive">
          <table className="benchmark-table" id="benchmark-table">
            <thead>
              <tr>
                <th>Modèle</th>
                <th>Type</th>
                <th>MAE (MW)</th>
                <th>WAPE (%)</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody id="benchmark-tbody">
              {models.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-loading">Chargement du benchmark...</td>
                </tr>
              ) : (
                models.map((m) => (
                  <tr key={m.id}>
                    <td className="model-name-cell">{m.name}</td>
                    <td>{m.category}</td>
                    <td><strong>{frNum.format(m.mae_mw)}</strong></td>
                    <td><strong>{m.wape_pct.toFixed(2)} %</strong></td>
                    <td>
                      <span className={`benchmark-badge ${m.badge_class}`}>
                        {m.badge}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="benchmark-footer">
          <span>Évalué sur 96 points de test chronologique strict (24h de réserve).</span>
        </div>
      </div>
    </article>
  );
};
