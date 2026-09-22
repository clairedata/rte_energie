# 🎓 Cours Complet : De l'Initiation aux LLMs et Foundation Models pour les Séries Temporelles Énergétiques

Bienvenue dans ce cours conçu pour vous expliquer, **de zéro et sans jargon obscur**, comment les modèles de fondation (Time Series Foundation Models - TSFM / "LLMs pour séries temporelles") fonctionnent, comment on les entraîne, et comment ils se comparent aux algorithmes de Machine Learning comme LightGBM.

---

## 📋 Table des Matières

1. [Introduction : Des mots aux chiffres, qu'est-ce qu'un TSFM ?](#1-introduction--des-mots-aux-chiffres-quest-ce-quun-tsfm-)
2. [Comment un LLM comprend-il une série temporelle ?](#2-comment-un-llm-comprend-il-une-série-temporelle-)
3. [Les 3 grandes manières d'utiliser un Foundation Model](#3-les-3-grandes-manières-dutiliser-un-foundation-model)
4. [Le Fine-Tuning (Entraînement adapté) : Comment ça marche ?](#4-le-fine-tuning-entraînement-adapté--comment-ça-marche-)
5. [Le match : Foundation Model (Chronos) vs Machine Learning (LightGBM)](#5-le-match--foundation-model-chronos-vs-machine-learning-lightgbm)
6. [Comment mesurer la qualité d'un modèle ? (Les Métriques)](#6-comment-mesurer-la-qualité-dun-modèle--les-métriques)
7. [Glossaire du Data Scientist débutant](#7-glossaire-du-data-scientist-débutant)

---

## 1. Introduction : Des mots aux chiffres, qu'est-ce qu'un TSFM ?

### Qu'est-ce qu'un LLM classique (ex: ChatGPT) ?
Un LLM (*Large Language Model*) est un réseau de neurones géant entraîné sur des milliards de phrases. Son unique métier est de prédire :  
👉 **"Quel est le mot le plus logique après les mots précédents ?"**

> *Exemple :* "Le chat mange une..." ➡️ le modèle prédit *"souris"* (90%) ou *"croquette"* (9%).

### Qu'est-ce qu'un Time Series Foundation Model (ex: Amazon Chronos-Bolt) ?
Une série temporelle (comme notre consommation électrique RTE) fonctionne exactement de la même manière qu'une phrase :
- Dans une phrase, on a une suite de mots : `[Mot 1, Mot 2, Mot 3, ...]`
- Dans l'énergie, on a une suite de consommations : `[5 200 MW, 5 350 MW, 5 500 MW, ...]`

Un **TSFM** est donc un modèle de fondation qui a été pré-entraîné sur des millions de courbes du monde entier (finance, trafic autoroutier, météo, consommation électrique mondiale). Son métier est de prédire :  
👉 **"Quelle sera la consommation future la plus logique après les consommations passées ?"**

---

## 2. Comment un LLM comprend-il une série temporelle ?

C'est la question que tout le monde se pose : **comment un Transformer (conçu pour du texte) peut-il lire des mégawatts (MW) ?**

### Étape 1 : La Tokenisation (Découpage en jetons)
Dans ChatGPT, chaque mot est transformé en un numéro appelé **Token**.  
Pour les séries temporelles, Amazon Chronos utilise une astuce géniale :

```text
Valeurs réelles (MW) :   [4120.5 MW,  4550.0 MW,  5890.2 MW]
                                      │
                                (Normalisation &
                                  Discrétisation)
                                      │
                                      ▼
Jetons (Tokens)       :   [ Token 42,  Token 51,   Token 88 ]
```

1. **Normalisation :** Le modèle divise les valeurs par la moyenne pour ramener les chiffres à une échelle standard (entre -1 et +1 ou 0 et 1).
2. **Discrétisation (Quantization) :** Il découpe l'espace des valeurs en cases (par exemple 4 096 cases). Chaque valeur de mégawatts tombe dans une case qui a son propre numéro de Token !

### Étape 2 : Le mécanisme d'Attention (Self-Attention)
Le secret des architectures Transformers réside dans **l'Attention**.  
Quand le modèle doit prédire la consommation de ce soir à 19h00 :
- Il ne regarde pas seulement ce qui s'est passé à 18h45.
- Il pose son "attention" sur :
  - La valeur d'**hier à 19h00** (cycle de 24h).
  - La valeur d'**il y a 7 jours à 19h00** (cycle hebdomadaire).
  - La tendance générale des dernières heures.

```
       [Hier 19h00] ─── (Forte attention 85%) ───┐
                                                  ▼
[Aujourd'hui 18h45] ─── (Moyenne attention 40%) ──► [PRÉDICTION Aujourd'hui 19h00]
                                                  ▲
 [Il y a 7j 19h00]  ─── (Forte attention 75%) ───┘
```

---

## 3. Les 3 grandes manières d'utiliser un Foundation Model

| Mode | En quoi ça consiste ? | Exemple concret dans notre projet |
| :--- | :--- | :--- |
| **1. Zero-Shot** ⭐ | On utilise le modèle pré-entraîné **tel quel**, sans lui faire faire le moindre calcul d'apprentissage sur nos données. | C'est ce que fait `chronos_predict.py` : il a atteint **8.87 % de WAPE** dès la première seconde ! |
| **2. In-Context Learning** | On injecte un historique plus ou moins long dans le "contexte" (les 288 ou 512 derniers points) pour qu'il s'adapte au vol. | On fournit à Chronos les 3 derniers jours pour prédire les 24h suivantes. |
| **3. Fine-Tuning** 🏋️ | On prend les poids du modèle pré-entraîné et on lance une descente de gradient pour **ré-ajuster ses neurones spécifiquement aux particularités du réseau français RTE**. | C'est ce que prépare le fichier `chronos_finetune.py`. |

---

## 4. Le Fine-Tuning (Entraînement adapté) : Comment ça marche ?

Le Fine-Tuning consiste à "spécialiser" un modèle généraliste.

> 💡 **L'analogie du médecin :**  
> - Le modèle pré-entraîné est comme un médecin généraliste : il connaît l'anatomie générale du monde entier.
> - Le Fine-Tuning, c'est lui faire faire une spécialisation de 6 mois sur le réseau électrique français pour qu'il connaisse par cœur les habitudes des Français (le pic de midi, l'effet du 20h à la télévision, les jours fériés français).

### Le pipeline d'entraînement pas à pas :

#### 1. Découpage en fenêtres glissantes (*Sliding Windows*)
Pour entraîner un modèle, on ne lui donne pas toute l'année d'un bloc. On fait glisser une fenêtre sur l'historique :

```text
Historique complet : [------------------------------------------------------------]

Exemple 1 :          [Contexte X : 512 points] ➡️ [Cible Y : 64 points à prédire]
Exemple 2 :             [Contexte X : 512 points] ➡️ [Cible Y : 64 points à prédire]
Exemple 3 :                [Contexte X : 512 points] ➡️ [Cible Y : 64 points à prédire]
```

- **X (Contexte) :** Ce que le modèle a le droit de regarder (les 512 quarts d'heure passés = 5,3 jours).
- **Y (Cible) :** Ce qu'il doit deviner (les 64 quarts d'heure futurs = 16 heures).

#### 2. La règle absolue : La sanctuarisation du Test (Pas de fuite temporelle)
> [!CAUTION]
> En séries temporelles, il est **formellement interdit de mélanger (shuffle) les lignes au hasard**.  
> Si vous mélangez les données, le modèle va s'entraîner en connaissant déjà le futur : il aura des scores parfaits à l'entraînement mais sera incapable de prédire demain dans la vraie vie (*Data Leakage*).

Le découpage doit **toujours** être chronologique :
```
[=========== ENTRAÎNEMENT (Train) : 95% ===========] [=== TEST SANCTUARISÉ : 5% ===]
(Le modèle apprend ici)                                (Le modèle ne le voit JAMAIS)
```

#### 3. La boucle d'apprentissage (Gradient Descent)
1. Le modèle reçoit `X` et fait une prédiction `Y_pred`.
2. On compare `Y_pred` avec la réalité `Y_true` grâce à une **Loss Function** (Fonction de perte).
3. L'algorithme calcule l'erreur et modifie légèrement les poids des neurones (via l'optimiseur **AdamW**) pour réduire l'erreur la prochaine fois.
4. On répète cela sur plusieurs **Epochs** (passages complets sur les données).

---

## 5. Le match : Foundation Model (Chronos) vs Machine Learning (LightGBM)

C'est l'une des questions les plus posées en entretien technique : *"Pourquoi utiliser LightGBM si on a des Transformers/LLMs ?"*

| Critère | Amazon Chronos-Bolt (TSFM) | LightGBM (Gradient Boosting) |
| :--- | :--- | :--- |
| **Type d'architecture** | Réseau de neurones profond (Transformer) | Forêt d'arbres de décision séquentiels |
| **Variables d'entrée** | **Univarié** (principalement la consommation passée) | **Multivarié** (Consommation + Température + Vent + Calendrier) |
| **Temps d'entraînement** | Moyen à lourd (plusieurs minutes à heures sur GPU) | **Ultra-rapide** (quelques secondes sur CPU) |
| **Besoin de données** | Fonctionne même avec très peu de données (grâce au Zero-Shot) | A besoin de suffisamment d'historique pour apprendre chaque règle |
| **Interprétabilité** | Boîte noire (difficile d'expliquer pourquoi tel neurone a réagi) | **Très transparent** : donne le pourcentage d'importance de chaque variable (*Feature Importance*) |
| **Cas d'usage idéal** | Signal fortement régulier et cyclique sans covariables complexes | Quand on a beaucoup de variables externes (météo locale, prix du gaz, jours fériés) |

---

## 6. Comment mesurer la qualité d'un modèle ? (Les Métriques)

Pour savoir si un modèle est bon ou mauvais, nous utilisons **4 métriques officielles** :

### 1. MAE (Mean Absolute Error - Erreur Moyenne Absolue)
- **Ce que c'est :** La moyenne des écarts entre la prédiction et la réalité, exprimée dans la même unité (**Mégawatts - MW**).
- **Exemple :** Si MAE = 500 MW, cela signifie qu'en moyenne, à n'importe quelle heure, notre modèle se trompe de 500 MW (en plus ou en moins).

### 2. RMSE (Root Mean Squared Error - Racine de l'Erreur Quadratique Moyenne)
- **Ce que c'est :** On élève les erreurs au carré avant d'en faire la moyenne, puis on prend la racine.
- **Pourquoi c'est important ?** Le carré pénalise très lourdement les **grosses erreurs**. Un modèle qui fait une seule erreur de 5 000 MW aura une très mauvaise RMSE, même si le reste de ses prédictions est correct.

### 3. MAPE (Mean Absolute Percentage Error - Pourcentage d'erreur relatif)
- **Ce que c'est :** L'erreur exprimée en pourcentage par rapport à la valeur réelle.
- **Exemple :** `|Réel - Prédiction| / Réel * 100`. Si la conso est de 10 000 MW et qu'on prédit 9 000 MW, le MAPE est de 10 %.

### 4. WAPE (Weighted Absolute Percentage Error - Erreur Pondérée) ⭐
- **La métrique reine des industriels (RTE, EDF, Amazon) :**  
  $\text{WAPE} = \frac{\sum |\text{Erreurs}|}{\sum \text{Réel}} \times 100$
- **Pourquoi le WAPE est meilleur que le MAPE ?**  
  Le MAPE explose si la consommation est très faible (creux de la nuit). Le WAPE, lui, pondère l'erreur sur le volume total consommé de la journée.
- **Repère :**
  - WAPE > 15 % : Modèle basique / insuffisant.
  - WAPE entre 8 % et 12 % : **Standard industriel de haute qualité**.
  - WAPE < 8 % : Modèle d'excellence.

---

## 7. Glossaire du Data Scientist débutant

- **Zero-Shot :** Utiliser une IA directement sans lui faire faire d'entraînement sur vos données locales.
- **Fine-Tuning :** Entraîner à nouveau un modèle pré-existant sur vos données spécifiques pour le rendre expert de votre domaine.
- **Overfitting (Sur-apprentissage) :** Le modèle a "appris par cœur" vos données d'entraînement au lieu de comprendre les règles générales. Résultat : 100% de réussite sur le passé, mais catastrophique sur le futur !
- **Epoch :** Un cycle complet où le modèle a vu l'intégralité du jeu d'entraînement une fois.
- **Batch Size :** Le nombre d'exemples que le modèle regarde en même temps avant de mettre à jour ses paramètres.
- **Learning Rate (Taux d'apprentissage) :** La vitesse à laquelle le modèle modifie ses neurones à chaque erreur (généralement très petit : `0.0001`).
- **Feature Store :** Une table ou base centralisée (comme notre table dbt `fct_energy_features`) qui prépare et stocke toutes les colonnes utiles pour nourrir les algorithmes d'IA.

---

*Document rédigé pour le projet RTE Energy Pipeline.*