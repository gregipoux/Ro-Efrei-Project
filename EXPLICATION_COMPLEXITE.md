# Explication du Système d'Analyse de Complexité

## Vue d'ensemble

Le système d'analyse de complexité dans ce projet permet de mesurer empiriquement les performances des algorithmes de résolution de problèmes de transport en fonction de la taille du problème (notée `n`).

## Objectif principal

L'objectif est de répondre à la question : **"Combien de temps prennent nos algorithmes selon la taille du problème ?"**

Pour cela, le système :
1. Génère des problèmes aléatoires de différentes tailles
2. Mesure les temps d'exécution de chaque algorithme
3. Répète ces mesures plusieurs fois pour avoir des statistiques fiables
4. Sauvegarde et visualise les résultats

## Métriques mesurées

Le système mesure **4 temps différents** pour chaque problème :

### 1. **θNO(n)** - Temps de Nord-Ouest
- **Définition** : Temps nécessaire pour calculer une solution initiale avec l'algorithme du coin Nord-Ouest
- **Complexité théorique** : O(n²) où n est la taille du problème (matrice n×n)

### 2. **θBH(n)** - Temps de Balas-Hammer
- **Définition** : Temps nécessaire pour calculer une solution initiale avec l'algorithme de Balas-Hammer
- **Complexité théorique** : O(n² log n) après optimisation (initialement O(n³))

### 3. **tNO(n)** - Temps d'optimisation avec Nord-Ouest
- **Définition** : Temps nécessaire pour optimiser une solution initiale Nord-Ouest jusqu'à l'optimum avec la méthode du marche-pied
- **Calcul** : Solution initiale NO + optimisation marche-pied

### 4. **tBH(n)** - Temps d'optimisation avec Balas-Hammer
- **Définition** : Temps nécessaire pour optimiser une solution initiale Balas-Hammer jusqu'à l'optimum avec la méthode du marche-pied
- **Calcul** : Solution initiale BH + optimisation marche-pied

### Métriques dérivées

- **Total NO** = θNO(n) + tNO(n) : Temps total pour résoudre avec Nord-Ouest
- **Total BH** = θBH(n) + tBH(n) : Temps total pour résoudre avec Balas-Hammer

## Architecture de l'implémentation

### Fichier principal : `complexite.py`

Ce fichier contient toutes les fonctions nécessaires à l'analyse de complexité.

#### Fonctions clés

##### 1. `generer_probleme_aleatoire(n, seed=None)`
```python
# Génère un problème de transport aléatoire de taille n × n
# - Matrice de coûts : valeurs aléatoires entre 1 et 100
# - Provisions et commandes : calculées pour garantir un problème équilibré
# - Utilise numpy si disponible pour accélérer les calculs
```

**Paramètres :**
- `n` : Taille du problème (matrice n×n)
- `seed` : Graine aléatoire pour reproductibilité

**Retourne :** `(costs, supplies, demands)`

##### 2. `mesurer_temps_nord_ouest(costs, supplies, demands)`
```python
# Mesure le temps d'exécution de l'algorithme Nord-Ouest
# Utilise time.perf_counter() pour une mesure précise
# Inclut le garbage collection pour libérer la mémoire
```

##### 3. `mesurer_temps_balas_hammer(costs, supplies, demands)`
```python
# Mesure le temps d'exécution de l'algorithme Balas-Hammer
# Inclut un timeout adaptatif selon la taille du problème
```

##### 4. `mesurer_temps_marche_pied_no(costs, supplies, demands)`
```python
# Mesure le temps total pour :
# 1. Calculer la solution initiale avec Nord-Ouest
# 2. Optimiser avec la méthode du marche-pied
```

##### 5. `mesurer_temps_marche_pied_bh(costs, supplies, demands)`
```python
# Mesure le temps total pour :
# 1. Calculer la solution initiale avec Balas-Hammer
# 2. Optimiser avec la méthode du marche-pied
```

##### 6. `resoudre_marche_pied_silencieux(costs, supplies, demands, allocation_initiale, max_duration)`
```python
# Version silencieuse de la méthode du marche-pied (sans affichage)
# Utilisée pour mesurer les temps sans pollution de la sortie
# Inclut des optimisations pour les grandes tailles :
# - Limitation du nombre d'itérations
# - Garbage collection fréquent
# - Timeout pour éviter les boucles infinies
```

##### 7. `executer_une_iteration_complete(n, seed)`
```python
# Exécute une itération complète pour un problème donné
# Mesure les 4 temps (θNO, θBH, tNO, tBH)
# Utilisée pour la parallélisation
# Retourne : (temps_no, temps_bh, temps_marche_pied_no, temps_marche_pied_bh)
```

##### 8. `executer_etude_complexite(...)` - Fonction principale
```python
# Fonction principale qui orchestre toute l'étude de complexité
```

**Paramètres principaux :**
- `valeurs_n` : Liste des tailles à tester (ex: [10, 40, 100, 400, 1000, 4000, 10000])
- `nb_executions` : Nombre de problèmes aléatoires à générer par taille (défaut: 100)
- `utiliser_parallele` : Activer la parallélisation (désactivé par défaut)
- `nb_processus` : Nombre de processus parallèles
- `fichier` : Nom du fichier JSON pour sauvegarder les résultats

**Processus :**
1. Pour chaque valeur de `n` :
   - Génère `nb_executions` problèmes aléatoires
   - Pour chaque problème :
     - Mesure θNO(n)
     - Mesure θBH(n)
     - Mesure tNO(n)
     - Mesure tBH(n)
   - Calcule les statistiques (moyennes, etc.)
   - Sauvegarde les résultats intermédiaires

2. Sauvegarde finale dans un fichier JSON

**Structure des résultats JSON :**
```json
{
  "10": {
    "theta_NO": [0.001, 0.002, ...],  // Liste des temps pour chaque exécution
    "theta_BH": [0.003, 0.004, ...],
    "t_NO": [0.005, 0.006, ...],
    "t_BH": [0.004, 0.005, ...],
    "theta_NO_plus_t_NO": [0.006, 0.008, ...],  // Somme θNO + tNO
    "theta_BH_plus_t_BH": [0.007, 0.009, ...]   // Somme θBH + tBH
  },
  "40": { ... },
  ...
}
```

## Optimisations implémentées

### 1. Gestion de la mémoire
- **Garbage collection fréquent** : Pour les grandes tailles (n ≥ 1000), le garbage collection est activé à chaque itération
- **Clonage intelligent** : Les données sont clonées seulement quand nécessaire pour économiser la mémoire

### 2. Timeouts adaptatifs
- **Petites tailles (n ≤ 100)** : Timeout de 10-30 secondes
- **Tailles moyennes (100 < n ≤ 1000)** : Timeout de 20-60 secondes
- **Grandes tailles (n ≥ 1000)** : Timeout de 60-300 secondes

### 3. Limitation des itérations
- **n ≥ 10000** : Maximum 50 itérations pour éviter les boucles infinies
- **n ≥ 5000** : Maximum 100 itérations
- **n ≥ 1000** : Maximum 200 itérations
- **n < 1000** : Maximum 1000 itérations

### 4. Parallélisation (optionnelle)
- **Mode séquentiel par défaut** : Conforme aux exigences "single processor"
- **Mode parallèle optionnel** : Traitement par lots avec pauses pour éviter la surchauffe
- **Adaptation automatique** : Pour n ≤ 10 ou n ≥ 1000, le mode séquentiel est forcé

## Utilisation dans le projet

### Intégration dans `main.py`

Le menu principal propose plusieurs options liées à la complexité :

#### Option 3 : Exécuter l'étude de complexité
```python
# Permet de choisir :
# - La valeur de n à tester (ou toutes les valeurs)
# - Le mode d'exécution (Silencieux, Modéré, Vénère)
# - Le nombre d'exécutions (1, 10, ou 100)
```

#### Option 4 : Analyser les résultats
```python
# Permet de :
# - Charger un fichier JSON de résultats
# - Visualiser les nuages de points
# - Analyser la complexité dans le pire des cas
# - Comparer les algorithmes
```

### Fonctions de visualisation

#### `tracer_nuages_de_points(resultats)`
- Trace 4 graphiques :
  1. Comparaison θNO vs θBH
  2. Comparaison tNO vs tBH
  3. Temps total (θNO+tNO vs θBH+tBH)
  4. Ratio (Total NO / Total BH)

#### `determiner_complexite_pire_cas(resultats)`
- Trace les courbes des maximums pour chaque métrique
- Permet d'analyser le comportement dans le pire des cas
- Compare avec les complexités théoriques (O(n²), O(n³), etc.)

#### `analyser_tous_les_resultats(dossier)`
- Analyse tous les fichiers JSON dans le dossier `complexity/`
- Génère des tableaux comparatifs détaillés
- Affiche des statistiques (moyenne, médiane, min, max, écart-type)

## Valeurs de n testées

Par défaut, le système teste les valeurs suivantes :
- **n = 10** : Petite taille (test rapide)
- **n = 40** : Taille petite-moyenne
- **n = 100** (1e2) : Taille moyenne
- **n = 410** (4.1e2) : Taille moyenne-grande
- **n = 1000** (1e3) : Grande taille
- **n = 4100** (4.1e3) : Très grande taille
- **n = 10000** (1e4) : Taille maximale (peut prendre plusieurs heures)

## Exemple d'utilisation

### Exécution d'une étude complète

```python
from complexite import executer_etude_complexite

# Exécuter l'étude pour toutes les valeurs de n avec 100 exécutions chacune
resultats = executer_etude_complexite(
    valeurs_n=[10, 40, 100, 400, 1000, 4000, 10000],
    nb_executions=100,
    sauvegarder_resultats=True,
    fichier='complexity/complexite_resultats.json'
)
```

### Analyse des résultats

```python
from complexite import charger_resultats_complexite, tracer_nuages_de_points

# Charger les résultats
resultats = charger_resultats_complexite(fichier='complexity/complexite_resultats.json')

# Visualiser les nuages de points
tracer_nuages_de_points(resultats)

# Analyser le pire des cas
determiner_complexite_pire_cas(resultats)
```

## Interprétation des résultats

### Complexité empirique

Les résultats permettent de :
1. **Vérifier la complexité théorique** : Les courbes doivent suivre les tendances théoriques (O(n²), O(n³), etc.)
2. **Comparer les algorithmes** : Voir lequel est le plus rapide selon la taille
3. **Identifier les optimisations** : Détecter si les optimisations sont efficaces

### Exemple d'interprétation

Si on observe que :
- θNO(n) suit une courbe O(n²) → Confirme la complexité théorique
- θBH(n) suit une courbe O(n² log n) → Confirme l'optimisation réussie
- tNO(n) est plus grand que tBH(n) → Balas-Hammer donne une meilleure solution initiale, donc moins d'itérations d'optimisation

## Fichiers générés

Les résultats sont sauvegardés dans le dossier `complexity/` :
- `complexite_resultats.json` : Résultats pour toutes les valeurs de n
- `complexite_resultats_n10.json` : Résultats pour n=10 uniquement
- `complexite_resultats_n40.json` : Résultats pour n=40 uniquement
- etc.

## Conclusion

Le système d'analyse de complexité permet de :
- ✅ Mesurer empiriquement les performances des algorithmes
- ✅ Valider les optimisations implémentées
- ✅ Comparer les différentes approches
- ✅ Identifier les goulots d'étranglement
- ✅ Générer des visualisations pour l'analyse

C'est un outil essentiel pour comprendre le comportement des algorithmes en pratique et valider que les optimisations théoriques fonctionnent bien en réalité.
