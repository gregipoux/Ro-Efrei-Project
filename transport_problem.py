"""
Transportation Problem Solver - Initial Solution Algorithms

This module implements functions for reading transportation problem data
and computing initial solutions using Northwest Corner and Balas-Hammer methods.
"""

from typing import List, Tuple


def read_transport_problem(filepath: str) -> Tuple[List[List[float]], List[float], List[float]]:
    """
    Lit un fichier texte décrivant un problème de transport équilibré.

    Format du fichier :
    - Ligne 1 : n m
    - Lignes 2..(n+1) : m coûts + 1 provision (Pi) par ligne
    - Ligne (n+2) : m commandes (Cj)

    Paramètres
    ----------
    filepath : str
        Chemin du fichier texte.

    Retours
    -------
    costs : List[List[float]]
        Matrice des coûts a[i][j] de taille n x m.
    supplies : List[float]
        Liste des provisions P_i de taille n.
    demands : List[float]
        Liste des demandes C_j de taille m.

    Contraintes
    -----------
    - Vérifie que la somme des supplies est égale à la somme des demands (cas équilibré).
    - En cas d'erreur de format ou de déséquilibre, lève une exception explicite.

    Raises
    ------
    FileNotFoundError
        Si le fichier n'existe pas.
    ValueError
        Si le format du fichier est incorrect ou si le problème n'est pas équilibré.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"Le fichier '{filepath}' n'a pas été trouvé.")
    
    if len(lines) < 3:
        raise ValueError("Le fichier doit contenir au moins 3 lignes (n m, n lignes de coûts+provisions, 1 ligne de commandes).")
    
    # Lire n et m
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
    
    # Lire les coûts et provisions
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
    
    # Lire les commandes
    try:
        demand_values = [float(x) for x in lines[n + 1].split()]
        if len(demand_values) != m:
            raise ValueError(f"La dernière ligne doit contenir {m} commandes, mais contient {len(demand_values)} valeurs.")
        
        demands = demand_values
        if any(d < 0 for d in demands):
            raise ValueError("Les commandes ne peuvent pas être négatives.")
    except ValueError as e:
        raise ValueError(f"Erreur lors de la lecture des commandes : {e}")
    
    # Vérifier que le problème est équilibré
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
    """
    Calcule une solution initiale de transport avec l'algorithme du coin Nord-Ouest.

    Paramètres
    ----------
    supplies : List[float]
        Provisions P_i, taille n.
    demands : List[float]
        Commandes C_j, taille m.

    Retours
    -------
    allocation : List[List[float]]
        Matrice b[i][j] de taille n x m, où b[i][j] est la quantité expédiée
        du fournisseur i vers le client j.

    Détails de l'algorithme
    -----------------------
    - On commence en (i=0, j=0).
    - À chaque étape, on alloue x = min(supply_restante_i, demand_restante_j).
    - Si supply_restante_i est épuisée, on passe au fournisseur suivant (i += 1).
    - Si demand_restante_j est épuisée, on passe au client suivant (j += 1).
    - On continue jusqu'à ce que toutes les supplies et demands soient satisfaites.
    """
    n = len(supplies)
    m = len(demands)
    
    # Initialiser la matrice d'allocation à zéro
    allocation = [[0.0 for _ in range(m)] for _ in range(n)]
    
    # Copier les supplies et demands pour les modifier
    remaining_supplies = supplies.copy()
    remaining_demands = demands.copy()
    
    # Position de départ : coin Nord-Ouest
    i = 0
    j = 0
    
    # Continuer jusqu'à ce que toutes les provisions et commandes soient satisfaites
    while i < n and j < m:
        # Allouer le maximum possible à la position courante
        allocation_amount = min(remaining_supplies[i], remaining_demands[j])
        allocation[i][j] = allocation_amount
        
        # Mettre à jour les provisions et commandes restantes
        remaining_supplies[i] -= allocation_amount
        remaining_demands[j] -= allocation_amount
        
        # Se déplacer selon l'épuisement
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
    """
    Calcule la pénalité de chaque ligne active.

    Pour chaque ligne active, on prend les coûts des colonnes actives.
    On trouve les deux plus petits coûts et la pénalité = deuxième plus petit - plus petit.
    Si une ligne n'a pas au moins deux coûts actifs, la pénalité est 0.

    Paramètres
    ----------
    costs : List[List[float]]
        Matrice des coûts de taille n x m.
    active_rows : List[bool]
        Liste indiquant quelles lignes sont encore actives.
    active_cols : List[bool]
        Liste indiquant quelles colonnes sont encore actives.

    Retours
    -------
    penalties : List[float]
        Liste des pénalités pour chaque ligne (0 si ligne inactive ou < 2 coûts actifs).
    """
    n = len(costs)
    penalties = [0.0] * n
    
    for i in range(n):
        if not active_rows[i]:
            continue
        
        # Collecter les coûts des colonnes actives pour cette ligne
        active_costs = [costs[i][j] for j in range(len(active_cols)) if active_cols[j]]
        
        # Si moins de 2 coûts actifs, pénalité = 0
        if len(active_costs) < 2:
            penalties[i] = 0.0
        else:
            # Trouver les deux plus petits coûts
            sorted_costs = sorted(active_costs)
            penalties[i] = sorted_costs[1] - sorted_costs[0]
    
    return penalties


def compute_col_penalties(
    costs: List[List[float]],
    active_rows: List[bool],
    active_cols: List[bool]
) -> List[float]:
    """
    Calcule la pénalité de chaque colonne active.

    Pour chaque colonne active, on prend les coûts des lignes actives.
    On trouve les deux plus petits coûts et la pénalité = deuxième plus petit - plus petit.
    Si une colonne n'a pas au moins deux coûts actifs, la pénalité est 0.

    Paramètres
    ----------
    costs : List[List[float]]
        Matrice des coûts de taille n x m.
    active_rows : List[bool]
        Liste indiquant quelles lignes sont encore actives.
    active_cols : List[bool]
        Liste indiquant quelles colonnes sont encore actives.

    Retours
    -------
    penalties : List[float]
        Liste des pénalités pour chaque colonne (0 si colonne inactive ou < 2 coûts actifs).
    """
    m = len(active_cols)
    penalties = [0.0] * m
    
    for j in range(m):
        if not active_cols[j]:
            continue
        
        # Collecter les coûts des lignes actives pour cette colonne
        active_costs = [costs[i][j] for i in range(len(active_rows)) if active_rows[i]]
        
        # Si moins de 2 coûts actifs, pénalité = 0
        if len(active_costs) < 2:
            penalties[j] = 0.0
        else:
            # Trouver les deux plus petits coûts
            sorted_costs = sorted(active_costs)
            penalties[j] = sorted_costs[1] - sorted_costs[0]
    
    return penalties


def balas_hammer_method(
    costs: List[List[float]],
    supplies: List[float],
    demands: List[float]
) -> List[List[float]]:
    """
    Calcule une solution initiale de transport avec l'algorithme de Balas-Hammer.

    Paramètres
    ----------
    costs : List[List[float]]
        Matrice des coûts a[i][j] de taille n x m.
    supplies : List[float]
        Provisions P_i.
    demands : List[float]
        Commandes C_j.

    Retours
    -------
    allocation : List[List[float]]
        Matrice b[i][j] de taille n x m.

    Esquisse de l'algorithme
    ------------------------
    Tant qu'il reste des supplies et des demands à satisfaire :
        1. Calculer les pénalités de chaque ligne active.
        2. Calculer les pénalités de chaque colonne active.
        3. Trouver la pénalité maximale parmi lignes et colonnes.
           - En cas d'égalité, choisir la ligne/colonne avec l'indice le plus petit.
        4. Dans cette ligne (ou colonne) choisie, repérer la cellule au coût minimal
           parmi les colonnes (ou lignes) encore actives.
        5. Allouer b[i][j] = min(supply_restante_i, demand_restante_j) dans cette cellule.
        6. Si la supply i est épuisée, marquer la ligne i comme inactive.
           Si la demande j est épuisée, marquer la colonne j comme inactive.
    """
    n = len(supplies)
    m = len(demands)
    
    # Initialiser la matrice d'allocation à zéro
    allocation = [[0.0 for _ in range(m)] for _ in range(n)]
    
    # Copier les supplies et demands pour les modifier
    remaining_supplies = supplies.copy()
    remaining_demands = demands.copy()
    
    # Initialiser les listes de lignes et colonnes actives
    active_rows = [True] * n
    active_cols = [True] * m
    
    # Continuer jusqu'à ce que toutes les provisions et commandes soient satisfaites
    while any(active_rows) and any(active_cols):
        # 1. Calculer les pénalités
        row_penalties = compute_row_penalties(costs, active_rows, active_cols)
        col_penalties = compute_col_penalties(costs, active_rows, active_cols)
        
        # 2. Trouver la pénalité maximale
        max_row_penalty = max(row_penalties) if any(row_penalties) else -1
        max_col_penalty = max(col_penalties) if any(col_penalties) else -1
        
        # 3. Choisir ligne ou colonne selon la pénalité maximale
        # En cas d'égalité, préférer les lignes, puis le plus petit indice
        is_row = False
        chosen_index = -1
        
        if max_row_penalty > max_col_penalty:
            is_row = True
            # Trouver l'indice de la première ligne avec pénalité maximale
            chosen_index = row_penalties.index(max_row_penalty)
        elif max_col_penalty > max_row_penalty:
            is_row = False
            # Trouver l'indice de la première colonne avec pénalité maximale
            chosen_index = col_penalties.index(max_col_penalty)
        else:
            # Égalité : préférer les lignes
            if max_row_penalty >= 0:
                is_row = True
                chosen_index = row_penalties.index(max_row_penalty)
            elif max_col_penalty >= 0:
                is_row = False
                chosen_index = col_penalties.index(max_col_penalty)
            else:
                # Toutes les pénalités sont 0 ou négatives, choisir arbitrairement
                # Trouver la première ligne ou colonne active
                for i in range(n):
                    if active_rows[i]:
                        is_row = True
                        chosen_index = i
                        break
                if chosen_index == -1:
                    for j in range(m):
                        if active_cols[j]:
                            is_row = False
                            chosen_index = j
                            break
        
        # 4. Trouver la cellule au coût minimal dans la ligne/colonne choisie
        best_i = -1
        best_j = -1
        best_cost = float('inf')
        
        if is_row:
            i = chosen_index
            for j in range(m):
                if active_cols[j] and costs[i][j] < best_cost:
                    best_cost = costs[i][j]
                    best_i = i
                    best_j = j
        else:
            j = chosen_index
            for i in range(n):
                if active_rows[i] and costs[i][j] < best_cost:
                    best_cost = costs[i][j]
                    best_i = i
                    best_j = j
        
        # 5. Allouer dans cette cellule
        allocation_amount = min(remaining_supplies[best_i], remaining_demands[best_j])
        allocation[best_i][best_j] = allocation_amount
        
        # 6. Mettre à jour les provisions et commandes restantes
        remaining_supplies[best_i] -= allocation_amount
        remaining_demands[best_j] -= allocation_amount
        
        # Désactiver la ligne ou colonne si épuisée
        if remaining_supplies[best_i] < 1e-9:
            active_rows[best_i] = False
        if remaining_demands[best_j] < 1e-9:
            active_cols[best_j] = False
    
    return allocation


def compute_total_cost(
    costs: List[List[float]],
    allocation: List[List[float]]
) -> float:
    """
    Calcule le coût total d'une proposition de transport.

    Paramètres
    ----------
    costs : List[List[float]]
        Matrice des coûts unitaires a[i][j].
    allocation : List[List[float]]
        Matrice des quantités transportées b[i][j].

    Retours
    -------
    total_cost : float
        Somme de a[i][j] * b[i][j] sur tous les i, j.

    Contraintes
    -----------
    - Vérifie que costs et allocation ont les mêmes dimensions.

    Raises
    ------
    ValueError
        Si les dimensions des matrices ne correspondent pas.
    """
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

