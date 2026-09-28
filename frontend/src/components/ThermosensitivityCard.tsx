import React from "react";
import { Lightbulb } from "lucide-react";

/**
 * Volet pédagogique éCO2mix expliquant l'impact de la thermosensibilité en France.
 */
export const ThermosensitivityCard: React.FC = () => {
  return (
    <article className="info-card">
      <div className="info-header">
        <Lightbulb size={20} className="text-accent-yellow" />
        <h3 className="info-title">Comprendre l'Effet Thermosensible (éCO2mix)</h3>
      </div>
      <div className="info-body">
        <p className="info-paragraph">
          En France, le chauffage électrique résidentiel et tertiaire rend le système électrique 
          <strong> hautement thermo-sensible</strong> en période fraîche ou hivernale.
        </p>
        <div className="thermo-fact-box">
          <div className="fact-number">~2 400 MW</div>
          <div className="fact-label">
            d'appel supplémentaire par degré perdu en dessous de 15°C (soit plus de deux réacteurs nucléaires d'1 GW).
          </div>
        </div>
        <p className="info-paragraph">
          Le modèle Foundation <strong>Amazon Chronos-Bolt</strong> spécialisé sur la France 
          anticipe ces variations avec une précision remarquable (WAPE &lt; 10%), évitant les sur-coûts 
          d'activation des centrales thermiques de pointe.
        </p>
      </div>
    </article>
  );
};
