
# Alors là, ce module lit les problèmes de transport et calcule des solutions initiales
# En résumé, on a deux méthodes : Nord-Ouest et Balas-Hammer

from typing import List, Tuple
import heapq  # Utilisé pour obtenir les k plus petits éléments efficacement

def read_transport_problem(filepath: str) -> Tuple[List[List[float]], List[float], List[float]]:
    # Alors là, cette fonction lit un fichier texte décrivant un problème de transport équilibré
    # Pour faire simple : on lit n et m, puis les coûts et provisions, puis les commandes
    # En clair, on vérifie que tout est équilibré (somme des provisions = somme des commandes)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"Le fichier '{filepath}' n'a pas été trouvé. Vérifiez que le fichier existe dans le répertoire 'test/'.")
    
    if len(lines) < 3:
        raise ValueError("Le fichier doit contenir au moins 3 lignes (n m, n lignes de coûts+provisions, 1 ligne de commandes).")
    
    # Lire n et m (le nombre de fournisseurs et de clients)
    try:
        first_line = lines[0].split()
        if len(first_line) != 2:
            raise ValueError("La première ligne doit contenir exactement deux nombres (n m).")
        n = int(first_line[0])
        m = int(first_line[1])
    except ValueError as e:
        raise ValueError(f"Erreur lors de la lecture de n et m : {e}")
    
    if n <= 0 or m <= 0:
        raise ValueError(f"n et m doivent être positifs (n={n}, m={m}).")
    
    if len(lines) != n + 2:
        raise ValueError(f"Le fichier doit contenir {n + 2} lignes (1 pour n m, {n} pour les fournisseurs, 1 pour les commandes), mais contient {len(lines)} lignes.")
    
    # Lire les coûts et provisions (on lit chaque ligne de fournisseur avec ses coûts et sa provision)
    costs: List[List[float]] = []
    supplies: List[float] = []
    
    for i in range(1, n + 1):
        try:
            values = [float(x) for x in lines[i].split()]
            if len(values) != m + 1:
                raise ValueError(f"La ligne {i+1} doit contenir {m + 1} valeurs ({m} coûts + 1 provision), mais contient {len(values)} valeurs.")
            
            row_costs = values[:m]
            supply = values[m]
            
            if supply < 0:
                raise ValueError(f"La provision du fournisseur {i} ne peut pas être négative : {supply}")
            
            costs.append(row_costs)
            supplies.append(supply)
        except ValueError as e:
            raise ValueError(f"Erreur lors de la lecture de la ligne {i+1} : {e}")
    
    # Lire les commandes (la dernière ligne contient toutes les commandes des clients)
    try:
        demand_values = [float(x) for x in lines[n + 1].split()]
        if len(demand_values) != m:
            raise ValueError(f"La dernière ligne doit contenir {m} commandes, mais contient {len(demand_values)} valeurs.")
        
        demands = demand_values
        if any(d < 0 for d in demands):
            raise ValueError("Les commandes ne peuvent pas être négatives.")
    except ValueError as e:
        raise ValueError(f"Erreur lors de la lecture des commandes : {e}")
    
    # Vérifier que le problème est équilibré (somme des provisions = somme des commandes, sinon c'est la galère)
    total_supply = sum(supplies)
    total_demand = sum(demands)
    
    if abs(total_supply - total_demand) > 1e-9:  # Tolérance pour les erreurs d'arrondi
        raise ValueError(
            f"Le problème n'est pas équilibré : "
            f"somme des provisions = {total_supply}, "
            f"somme des commandes = {total_demand}"
        )
    
    return costs, supplies, demands


def northwest_corner_method(
    supplies: List[float],
    demands: List[float]
) -> List[List[float]]:
    # Alors là, cette fonction calcule une solution initiale avec l'algorithme du coin Nord-Ouest
    # Pour faire simple : on commence en haut à gauche et on remplit case par case jusqu'à ce que tout soit satisfait
    
    # Pseudo-code :
    # allocation = matrice n x m initialisée à 0
    # remaining_supplies = copie(supplies)
    # remaining_demands = copie(demands)
    # i = 0, j = 0 (on commence en haut à gauche)
    # 
    # TANT QUE i < n ET j < m:
    #     x = min(remaining_supplies[i], remaining_demands[j])
    #     allocation[i][j] = x
    #     remaining_supplies[i] -= x
    #     remaining_demands[j] -= x
    #     
    #     SI remaining_supplies[i] == 0:
    #         i++ (on passe au fournisseur suivant)
    #     SINON SI remaining_demands[j] == 0:
    #         j++ (on passe au client suivant)
    #     FIN SI
    # FIN TANT QUE
    
    n = len(supplies)
    m = len(demands)
    
    # Initialiser la matrice d'allocation à zéro (on part de rien)
    allocation = [[0.0 for _ in range(m)] for _ in range(n)]
    
    # Copier les supplies et demands pour les modifier (on ne veut pas toucher aux originaux)
    remaining_supplies = supplies.copy()
    remaining_demands = demands.copy()
    
    # Position de départ : coin Nord-Ouest (en haut à gauche, c'est notre point de départ)
    i = 0
    j = 0
    
    # Continuer jusqu'à ce que toutes les provisions et commandes soient satisfaites (on remplit tout)
    while i < n and j < m:
        # Allouer le maximum possible à la position courante (on prend le minimum entre ce qui reste)
        allocation_amount = min(remaining_supplies[i], remaining_demands[j])
        allocation[i][j] = allocation_amount
        
        # Mettre à jour les provisions et commandes restantes (on soustrait ce qu'on a alloué)
        remaining_supplies[i] -= allocation_amount
        remaining_demands[j] -= allocation_amount
        
        # Se déplacer selon l'épuisement (si une provision ou commande est épuisée, on avance)
        if remaining_supplies[i] < 1e-9:  # Provision épuisée
            i += 1
        elif remaining_demands[j] < 1e-9:  # Commande épuisée
            j += 1
    
    return allocation


def compute_row_penalties(
    costs: List[List[float]],
    active_rows: List[bool],
    active_cols: List[bool]
) -> List[float]:
    # Alors là, cette fonction calcule la pénalité de chaque ligne active
    # Optimisation : On ne trie pas toute la liste, on cherche juste les 2 plus petits éléments
    
    n = len(costs)
    penalties = [0.0] * n
    
    # Pré-calculer les indices des colonnes actives pour éviter de parcourir active_cols à chaque ligne
    active_col_indices = [j for j, active in enumerate(active_cols) if active]
    
    if len(active_col_indices) < 2:
        # S'il y a 0 ou 1 colonne active, la pénalité est 0 pour tout le monde (car max 1 coût dispo)
        return penalties
        
    for i in range(n):
        if not active_rows[i]:
            continue
        
        # On extrait les coûts de la ligne i pour les colonnes actives
        # Optimisation possible : heapq.nsmallest est plus efficace que sorted()[:2] pour les grandes listes
        current_row_costs = costs[i]
        active_costs = [current_row_costs[j] for j in active_col_indices]
        
        if len(active_costs) >= 2:
            # Trouver les deux plus petits coûts
            smallest = heapq.nsmallest(2, active_costs)
            penalties[i] = smallest[1] - smallest[0]
        else:
            penalties[i] = 0.0
            
    return penalties


def compute_col_penalties(
    costs: List[List[float]],
    active_rows: List[bool],
    active_cols: List[bool]
) -> List[float]:
    # Cette fonction calcule la pénalité de chaque colonne active
    # Optimisation : On ne trie pas toute la liste, on cherche juste les 2 plus petits éléments
    
    n = len(costs)
    if n == 0:
        return []
    m = len(costs[0])
    penalties = [0.0] * m
    
    # Pré-calculer les indices des lignes actives
    active_row_indices = [i for i, active in enumerate(active_rows) if active]

    if len(active_row_indices) < 2:
        return penalties
    
    for j in range(m):
        if not active_cols[j]:
            continue
        
        # On extrait les coûts de la colonne j pour les lignes actives
        active_costs = [costs[i][j] for i in active_row_indices]
        
        if len(active_costs) >= 2:
            # Trouver les deux plus petits coûts
            smallest = heapq.nsmallest(2, active_costs)
            penalties[j] = smallest[1] - smallest[0]
        else:
            penalties[j] = 0.0
            
    return penalties


def balas_hammer_method(
    costs: List[List[float]],
    supplies: List[float],
    demands: List[float],
    verbose: bool = False,
    max_duration: float = None  # Ajout du paramètre de durée maximale
) -> List[List[float]]:
    """
    Calcule une solution initiale de transport avec l'algorithme de Balas-Hammer.
    Optimisé pour éviter de trier inutilement et avec une protection timeout.
    """
    import time
    start_time = time.perf_counter()

    n = len(supplies)
    m = len(demands)
    
    # Initialiser la matrice d'allocation à zéro (on part de rien)
    allocation = [[0.0 for _ in range(m)] for _ in range(n)]
    
    # Copier les supplies et demands pour les modifier (on ne veut pas toucher aux originaux)
    remaining_supplies = supplies.copy()
    remaining_demands = demands.copy()
    
    # Initialiser les listes de lignes et colonnes actives (toutes actives au début)
    active_rows = [True] * n
    active_cols = [True] * m
    
    iteration = 0
    
    # Compteurs pour savoir combien il reste d'actifs (pour éviter any())
    nb_active_rows = n
    nb_active_cols = m

    # Continuer jusqu'à ce que toutes les provisions et commandes soient satisfaites
    while nb_active_rows > 0 and nb_active_cols > 0:
        # Vérification du timeout
        if max_duration and (time.perf_counter() - start_time) > max_duration:
            if verbose:
                print("⚠️ Timeout Balas-Hammer atteint, complétion par Nord-Ouest sur le reste")
            break

        iteration += 1
        
        # Étape 1 : Calculer les pénalités
        row_penalties = compute_row_penalties(costs, active_rows, active_cols)
        col_penalties = compute_col_penalties(costs, active_rows, active_cols)
        
        # Étape 2 : Trouver la pénalité maximale
        # On cherche le max tout en gardant l'indice
        max_row_penalty = -1.0
        best_row_idx = -1
        for i in range(n):
            if active_rows[i]:
                if row_penalties[i] > max_row_penalty:
                    max_row_penalty = row_penalties[i]
                    best_row_idx = i
                # En cas d'égalité, on garde le premier trouvé (indice min)
        
        max_col_penalty = -1.0
        best_col_idx = -1
        for j in range(m):
            if active_cols[j]:
                if col_penalties[j] > max_col_penalty:
                    max_col_penalty = col_penalties[j]
                    best_col_idx = j
        
        if best_row_idx == -1 and best_col_idx == -1:
            break # Plus rien à faire

        # Étape 3 : Choisir ligne ou colonne
        target_row = -1
        target_col = -1
        
        # Priorité à la pénalité max. En cas d'égalité entre ligne et colonne, on peut privilégier ligne par ex.
        if max_row_penalty >= max_col_penalty:
            # On a choisi la ligne 'best_row_idx'
            target_row = best_row_idx
            # Trouver la colonne active avec le coût minimal dans cette ligne
            min_cost = float('inf')
            for j in range(m):
                if active_cols[j]:
                    if costs[target_row][j] < min_cost:
                        min_cost = costs[target_row][j]
                        target_col = j
        else:
            # On a choisi la colonne 'best_col_idx'
            target_col = best_col_idx
            # Trouver la ligne active avec le coût minimal dans cette colonne
            min_cost = float('inf')
            for i in range(n):
                if active_rows[i]:
                    if costs[i][target_col] < min_cost:
                        min_cost = costs[i][target_col]
                        target_row = i
        
        # Étape 4 : Allouer
        x = min(remaining_supplies[target_row], remaining_demands[target_col])
        allocation[target_row][target_col] = x
        remaining_supplies[target_row] -= x
        remaining_demands[target_col] -= x
        
        # Étape 5 : Désactiver si épuisé
        # On utilise une tolérance pour les flottants
        if remaining_supplies[target_row] < 1e-9:
            active_rows[target_row] = False
            nb_active_rows -= 1
            remaining_supplies[target_row] = 0.0 # Clean up
            
        if remaining_demands[target_col] < 1e-9:
            active_cols[target_col] = False
            nb_active_cols -= 1
            remaining_demands[target_col] = 0.0 # Clean up

    # Si on est sorti à cause du timeout ou s'il reste des éléments non alloués (cas rares d'arrondi ou autre),
    # on complète avec une logique simple (type Nord-Ouest sur les restants) pour avoir une solution réalisable.
    # Pour simplifier, on parcourt ce qui reste.
    if any(s > 1e-9 for s in remaining_supplies) and any(d > 1e-9 for d in remaining_demands):
         for i in range(n):
             if remaining_supplies[i] > 1e-9:
                 for j in range(m):
                     if remaining_demands[j] > 1e-9:
                         x = min(remaining_supplies[i], remaining_demands[j])
                         allocation[i][j] += x
                         remaining_supplies[i] -= x
                         remaining_demands[j] -= x
                         if remaining_supplies[i] < 1e-9: break

    return allocation


def compute_total_cost(
    costs: List[List[float]],
    allocation: List[List[float]]
) -> float:
    # Alors là, cette fonction calcule le coût total d'une proposition de transport
    # Pour faire simple : on fait la somme de tous les coûts × quantités transportées
    if len(costs) != len(allocation):
        raise ValueError(
            f"Le nombre de lignes ne correspond pas : "
            f"costs a {len(costs)} lignes, allocation a {len(allocation)} lignes."
        )
    
    if len(costs) == 0:
        return 0.0
    
    if len(costs[0]) != len(allocation[0]):
        raise ValueError(
            f"Le nombre de colonnes ne correspond pas : "
            f"costs a {len(costs[0])} colonnes, allocation a {len(allocation[0])} colonnes."
        )
    
    total_cost = 0.0
    for i in range(len(costs)):
        for j in range(len(costs[0])):
            total_cost += costs[i][j] * allocation[i][j]
    
    return total_cost
