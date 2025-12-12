
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
    max_duration: float = None
) -> List[List[float]]:
    """
    Calcule une solution initiale avec l'algorithme de Balas-Hammer.
    OPTIMISÉ : Utilise des listes triées pré-calculées pour éviter la complexité O(n^3).
    Complexité ramenée à environ O(n^2 log n) pour le tri initial, puis O(n^2) pour l'exécution.
    """
    import time
    start_time = time.perf_counter()

    n = len(supplies)
    m = len(demands)
    
    allocation = [[0.0 for _ in range(m)] for _ in range(n)]
    remaining_supplies = supplies.copy()
    remaining_demands = demands.copy()
    
    # Indicateurs d'activité
    active_rows = [True] * n
    active_cols = [True] * m
    nb_active_rows = n
    nb_active_cols = m
    
    # Pour les très grands problèmes, on évite le tri complet si possible ou on le fait intelligemment
    # Mais le tri complet est la meilleure garantie de performance algorithmique ici.
    
    if verbose:
        print(f"  Prétraitement Balas-Hammer (tri des coûts)...")

    # Pré-calculer les indices triés pour chaque ligne et colonne
    # sorted_rows[i] contient les indices de colonnes j triés par cost[i][j]
    # sorted_cols[j] contient les indices de lignes i triés par cost[i][j]
    
    # Optimisation : Si n est très grand, le tri peut prendre du temps.
    # On vérifie le timeout pendant le tri
    
    try:
        sorted_rows = []
        for i in range(n):
            if max_duration and (time.perf_counter() - start_time) > max_duration:
                raise TimeoutError("Timeout pendant le tri des lignes")
            # On trie les indices des colonnes selon le coût
            sorted_rows.append(sorted(range(m), key=lambda j: costs[i][j]))
            
        sorted_cols = []
        for j in range(m):
            if max_duration and (time.perf_counter() - start_time) > max_duration:
                raise TimeoutError("Timeout pendant le tri des colonnes")
            # On trie les indices des lignes selon le coût
            sorted_cols.append(sorted(range(n), key=lambda i: costs[i][j]))
    except TimeoutError:
        if verbose:
            print("⚠️ Timeout pendant le pré-calcul, bascule vers Nord-Ouest")
        # On complète avec une méthode rapide (Nord-Ouest adapté aux restes)
        for i in range(n):
            if remaining_supplies[i] > 1e-9:
                for j in range(m):
                    if remaining_demands[j] > 1e-9:
                        qty = min(remaining_supplies[i], remaining_demands[j])
                        allocation[i][j] += qty
                        remaining_supplies[i] -= qty
                        remaining_demands[j] -= qty
                        if remaining_supplies[i] < 1e-9: break
        return allocation

    # Pointeurs pour savoir où on en est dans les listes triées
    # ptr_rows[i] indique l'index dans sorted_rows[i] du prochain élément potentiellement valide
    ptr_rows = [0] * n
    ptr_cols = [0] * m
    
    # OPTIMISATION : Cache des pénalités pour éviter de recalculer à chaque itération
    # On ne recalcule que lorsque nécessaire (quand une colonne/ligne devient inactive)
    row_penalties_cache = [None] * n  # None signifie "non calculé"
    col_penalties_cache = [None] * m
    penalty_cache_valid = False  # Flag pour savoir si le cache est valide
    
    # Fonction helper pour trouver les 2 plus petits coûts valides d'une ligne
    def get_row_penalty(i, force_recalc=False):
        # Si le cache est valide et qu'on n'a pas besoin de recalculer, utiliser le cache
        if not force_recalc and row_penalties_cache[i] is not None:
            return row_penalties_cache[i]
        
        # Trouver le 1er min
        idx1 = -1
        cost1 = float('inf')
        
        # Avancer le pointeur jusqu'à trouver une colonne active
        k = ptr_rows[i]
        while k < m:
            col_idx = sorted_rows[i][k]
            if active_cols[col_idx]:
                idx1 = col_idx
                cost1 = costs[i][col_idx]
                ptr_rows[i] = k # Mise à jour du pointeur pour la prochaine fois
                break
            k += 1
            
        if idx1 == -1:
            penalty = 0.0
            row_penalties_cache[i] = penalty
            return penalty
        
        # Trouver le 2ème min (on continue à partir de k+1)
        idx2 = -1
        cost2 = float('inf')
        k2 = k + 1
        while k2 < m:
            col_idx = sorted_rows[i][k2]
            if active_cols[col_idx]:
                idx2 = col_idx
                cost2 = costs[i][col_idx]
                break
            k2 += 1
            
        if idx2 == -1:
            penalty = 0.0  # Un seul élément restant, pénalité = 0 (standard)
        else:
            penalty = cost2 - cost1
        
        # Mettre en cache
        row_penalties_cache[i] = penalty
        return penalty

    # Fonction helper pour trouver les 2 plus petits coûts valides d'une colonne
    def get_col_penalty(j, force_recalc=False):
        # Si le cache est valide et qu'on n'a pas besoin de recalculer, utiliser le cache
        if not force_recalc and col_penalties_cache[j] is not None:
            return col_penalties_cache[j]
        
        # Trouver le 1er min
        idx1 = -1
        cost1 = float('inf')
        
        k = ptr_cols[j]
        while k < n:
            row_idx = sorted_cols[j][k]
            if active_rows[row_idx]:
                idx1 = row_idx
                cost1 = costs[row_idx][j]
                ptr_cols[j] = k
                break
            k += 1
            
        if idx1 == -1:
            penalty = 0.0
            col_penalties_cache[j] = penalty
            return penalty
        
        idx2 = -1
        cost2 = float('inf')
        k2 = k + 1
        while k2 < n:
            row_idx = sorted_cols[j][k2]
            if active_rows[row_idx]:
                idx2 = row_idx
                cost2 = costs[row_idx][j]
                break
            k2 += 1
            
        if idx2 == -1:
            penalty = 0.0
        else:
            penalty = cost2 - cost1
        
        # Mettre en cache
        col_penalties_cache[j] = penalty
        return penalty
    
    # Initialiser le cache des pénalités (calcul initial)
    for i in range(n):
        if active_rows[i]:
            get_row_penalty(i)
    for j in range(m):
        if active_cols[j]:
            get_col_penalty(j)

    # Boucle principale
    while nb_active_rows > 0 and nb_active_cols > 0:
        if max_duration and (time.perf_counter() - start_time) > max_duration:
            if verbose: print("⚠️ Timeout Balas-Hammer atteint")
            break

        # OPTIMISATION : On utilise le cache des pénalités au lieu de tout recalculer
        # On ne recalcule que si nécessaire (lorsqu'une ligne/colonne devient inactive)
        
        best_penalty = -1.0
        target_type = None # 'row' ou 'col'
        target_idx = -1
        
        # Scanner lignes (utiliser le cache)
        for i in range(n):
            if active_rows[i]:
                p = get_row_penalty(i)
                if p > best_penalty:
                    best_penalty = p
                    target_type = 'row'
                    target_idx = i
                elif p == best_penalty and target_type is None:
                    # En cas d'égalité, prendre le premier
                    target_type = 'row'
                    target_idx = i
        
        # Scanner colonnes (utiliser le cache)
        for j in range(m):
            if active_cols[j]:
                p = get_col_penalty(j)
                if p > best_penalty:
                    best_penalty = p
                    target_type = 'col'
                    target_idx = j
        
        if target_idx == -1: break
        
        # Trouver la meilleure case pour l'élément choisi
        r, c = -1, -1
        if target_type == 'row':
            r = target_idx
            # Trouver la colonne active avec le coût min (c'est le 1er élément valide de la liste triée)
            # get_row_penalty a mis à jour ptr_rows[r], donc on regarde là
            col_idx = sorted_rows[r][ptr_rows[r]]
            # Vérification de sécurité (normalement ptr pointe sur actif)
            if not active_cols[col_idx]:
                # On doit chercher (ne devrait pas arriver si get_row_penalty appelé juste avant)
                k = ptr_rows[r]
                while k < m:
                    if active_cols[sorted_rows[r][k]]:
                        col_idx = sorted_rows[r][k]
                        ptr_rows[r] = k
                        break
                    k += 1
            c = col_idx
        else:
            c = target_idx
            # Trouver la ligne active avec coût min
            row_idx = sorted_cols[c][ptr_cols[c]]
            if not active_rows[row_idx]:
                k = ptr_cols[c]
                while k < n:
                    if active_rows[sorted_cols[c][k]]:
                        row_idx = sorted_cols[c][k]
                        ptr_cols[c] = k
                        break
                    k += 1
            r = row_idx
            
        # Allouer
        qty = min(remaining_supplies[r], remaining_demands[c])
        allocation[r][c] = qty
        remaining_supplies[r] -= qty
        remaining_demands[c] -= qty
        
        # Mettre à jour statuts et invalider le cache des pénalités affectées
        if remaining_supplies[r] < 1e-9:
            active_rows[r] = False
            nb_active_rows -= 1
            # Invalider le cache de cette ligne
            row_penalties_cache[r] = None
            # Invalider les caches des colonnes (car elles peuvent être affectées)
            for j in range(m):
                if active_cols[j]:
                    col_penalties_cache[j] = None
        
        if remaining_demands[c] < 1e-9:
            active_cols[c] = False
            nb_active_cols -= 1
            # Invalider le cache de cette colonne
            col_penalties_cache[c] = None
            # Invalider les caches des lignes (car elles peuvent être affectées)
            for i in range(n):
                if active_rows[i]:
                    row_penalties_cache[i] = None
            
    # Complétion finale si nécessaire
    if any(s > 1e-9 for s in remaining_supplies) and any(d > 1e-9 for d in remaining_demands):
        for i in range(n):
            if remaining_supplies[i] > 1e-9:
                for j in range(m):
                    if remaining_demands[j] > 1e-9:
                        qty = min(remaining_supplies[i], remaining_demands[j])
                        allocation[i][j] += qty
                        remaining_supplies[i] -= qty
                        remaining_demands[j] -= qty
    
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
