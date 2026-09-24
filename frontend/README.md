# 🌐 Front-End éCO2mix : Dashboard Énergétique & Inférence IA (React 19)

Application Web moderne et réactive dédiée au suivi en temps réel de la consommation électrique française et à la restitution des prévisions issues des modèles d'Intelligence Artificielle (**Amazon Chronos-Bolt**).

Inspiré du portail officiel **éCO2mix de RTE France** et des écrans de supervision des centres de conduite du réseau, ce dashboard offre une expérience immersive en **Dark Mode Technologique** à haute performance.

---

## ⚡ Fonctionnalités Clés

- ⏱️ **Synchronisation Quart-Horaire Intelligente :** Auto-refresh automatique cadencé à 15 minutes (`900 000 ms`), aligné rigoureusement sur le cycle réel de transmission des télémesures de RTE France.
- 🏷️ **Horodatage Précis du Dernier Relevé :** La carte principale KPI affiche dynamiquement `Relevé de [heure]` (ex: `Relevé de 23h45`) pour dissiper toute confusion entre puissance instantanée, pic journalier et moyenne.
- 🎯 **Métriques d'Erreur Journalières Dynamiques à la Volée :** Dès qu'une date historique est sélectionnée dans le calendrier, l'application compare point par point la réalité observée aux prédictions et affiche instantanément au-dessus de la courbe les badges de précision :
  - **Chronos-Bolt IA :** WAPE (ex: `7.2 %`) et MAE (ex: `412 MW`)
  - **Baseline J-1 :** WAPE (ex: `12.8 %`)
- 📈 **Master Timeline Multi-Séries (Chart.js) :**
  - Consommation réelle observée (Courbe Cyan éCO2mix `#00f0ff`)
  - Prévision IA Championne Chronos-Bolt Small (Courbe Ambre `#ff9f1c`)
  - Fuseau d'incertitude probabiliste à 80% (Quantiles $q_{10} - q_{90}$)
  - Modèle de référence saisonnier (Baseline J-1 `#ef4444`)
  - Prévisions officielles de référence RTE J et RTE J-1
  - Filtres interactifs par bouton-pill pour masquer/afficher chaque courbe.
- 🌡️ **Indicateur de Thermosensibilité & Météo :** Suivi en direct de la température nationale et rappel du coefficient d'impact thermique (~2 400 MW par °C en hiver sous 15°C).
- 🏆 **Tableau de Benchmark Standardisé :** Synthèse comparative des performances globales du modèle IA face aux modèles de référence sur le jeu de test sanctuarisé.

---

## 🛠️ Stack Technologique

- **Framework :** [React 19](https://react.dev/)
- **Langage :** [TypeScript 5](https://www.typescriptlang.org/) (Typage strict `energy.ts`)
- **Build Tool & Bundler :** [Vite 6](https://vitejs.dev/) avec Hot Module Replacement (HMR) ultra-rapide
- **Graphiques & Visualisations :** [Chart.js 4](https://www.chartjs.org/) & [react-chartjs-2](https://react-chartjs-2.js.org/)
- **Iconographie :** [Lucide React](https://lucide.dev/) (icônes vectorielles légères et modernes)
- **Styling :** Vanilla CSS 3 modulaire avec tokens HSL/RGB, animations néon, glassmorphism et mise en page responsive CSS Grid / Flexbox.

---

## 📁 Architecture des Fichiers

```text
frontend/
├── index.html              # Point d'entrée HTML5 avec polices modernes et méta-données
├── package.json            # Dépendances React 19, Vite, Chart.js, Lucide
├── tsconfig.json           # Configuration TypeScript stricte
├── vite.config.ts          # Proxy de développement /api -> http://localhost:8000
└── src/
    ├── main.tsx            # Point de montage DOM React
    ├── App.tsx             # Composant racine : gestion d'état, appels REST, polling 15m
    ├── index.css           # Design System Vanilla CSS (Dark Mode éCO2mix & Néon)
    ├── types/
    │   └── energy.ts       # Interfaces TypeScript (KpiData, ForecastPoint, BenchmarkRow)
    └── components/
        ├── Header.tsx                 # En-tête avec Live Pulse, sélecteur de date et bouton refresh
        ├── KpiGrid.tsx                # Grille des 4 indicateurs clés
        ├── KpiCard.tsx                # Composant unitaire carte KPI avec badge dynamique
        ├── ChartSection.tsx           # Master Timeline Chart.js avec calcul dynamique WAPE/MAE
        ├── BenchmarkTable.tsx         # Tableau officiel du benchmark modèle
        └── ThermosensitivityCard.tsx # Encadré pédagogique sur la sensibilité thermique
```

---

## 🚀 Commandes de Développement & Production

### 1. Installation des dépendances
```bash
npm install
```

### 2. Lancement en mode développement (avec HMR)
```bash
npm run dev
```
*Le serveur de développement démarre sur [http://localhost:5173](http://localhost:5173). Le fichier `vite.config.ts` redirige automatiquement les requêtes `/api/*` vers le backend FastAPI (`http://localhost:8000`).*

### 3. Compilation pour la production
```bash
npm run build
```
*Génère le dossier `dist/` minifié et optimisé, directement distribué par le serveur FastAPI en mode unifié.*

### 4. Prévisualisation locale du bundle de production
```bash
npm run preview
```
