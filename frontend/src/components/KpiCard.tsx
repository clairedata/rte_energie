import React from "react";

interface KpiCardProps {
  id: string;
  icon: React.ReactNode;
  title: string;
  tag?: string;
  value: string | number;
  unit: string;
  subContent?: React.ReactNode;
  isPrimary?: boolean;
  valueColorClass?: string;
}

/**
 * Composant de carte KPI éCO2mix unifié et réutilisable.
 */
export const KpiCard: React.FC<KpiCardProps> = ({
  id,
  icon,
  title,
  tag,
  value,
  unit,
  subContent,
  isPrimary = false,
  valueColorClass = ""
}) => {
  return (
    <article
      className={`kpi-card ${isPrimary ? "kpi-card-primary" : ""}`}
      id={id}
    >
      <div className="kpi-header">
        <div className="kpi-icon-wrapper">{icon}</div>
        <span className="kpi-title">{title}</span>
        {tag && <span className="kpi-tag">{tag}</span>}
      </div>

      <div className="kpi-body">
        <div className="kpi-value-row">
          <span className={`kpi-number ${valueColorClass}`}>{value}</span>
          <span className="kpi-unit">{unit}</span>
        </div>
        {subContent}
      </div>
    </article>
  );
};
