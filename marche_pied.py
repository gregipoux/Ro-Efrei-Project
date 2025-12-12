# Alors là, ce fichier implémente la méthode du marche-pied avec potentiel
# En résumé, c'est l'algorithme principal qui optimise une proposition de transport initiale jusqu'à trouver la solution optimale
# 
# Principe général (pour faire simple) :
# 1. On part d'une solution initiale (Nord-Ouest ou Balas-Hammer)
# 2. On vérifie qu'elle est valide (acyclique et connexe, sinon on corrige)
# 3. On calcule les potentiels et les coûts marginaux
# 4. Si une arête améliorante existe (coût marginal négatif), on l'ajoute
# 5. On maximise le transport sur le cycle formé
# 6. On répète jusqu'à ce que la solution soit optimale (ou qu'on abandonne, ce qui n'est pas possible donc on continue)

from typing import List, Tuple, Optional
from cyclique import tester_acyclique, maximiser_sur_cycle
from connexite import is_connected_transport, print_components
from potentiels import (
    calculer_potentiels,
    calculer_couts_potentiels,
    calculer_couts_marginaux,
    detecter_arete_ameliorante,
    detecter_arete_ameliorante_rapide
)
from transport_problem import compute_total_cost


def rendre_connexe(
    costs: List[List[float]],
    allocation: List[List[float]],
    supplies: List[float],
    demands: List[float],
    verbose: bool = False
) -> List[Tuple[int, int]]:
    # Alors là, cette fonction rend la proposition de transport connexe
    # OPTIMISÉE : On évite de lister toutes les arêtes (O(nm)) pour les grands problèmes
    
    n = len(allocation)
    m = len(allocation[0]) if n > 0 else 0
    
    # On vérifie d'abord si c'est déjà connexe
    est_connexe, composantes = is_connected_transport(allocation)
    if est_connexe:
        return []
    
    arêtes_ajoutées = []
    epsilon = 1e-6
    
    if verbose:
        print(f"  Recherche d'arêtes pour connecter {len(composantes)} composantes...")
        
    # Stratégie optimisée : on relie les composantes une à une
    # On prend la première composante et on cherche l'arête la moins chère vers n'importe quelle autre composante
    import heapq
    
    # On travaille tant qu'il y a plus d'une composante
    while len(composantes) > 1:
        # On va chercher à relier la composante 0 aux autres
        comp0 = composantes[0]
        
        # Séparer lignes et colonnes de la composante 0
        # `connexite.is_connected_transport` renvoie historiquement des nœuds sous forme de strings:
        # - "P{i}" pour les lignes (fournisseurs)
        # - "C{j}" pour les colonnes (clients)
        # D'autres parties du code peuvent utiliser ('row', i)/('col', j). On supporte les 2 formats.
        rows0 = set()
        cols0 = set()
        for node in comp0:
            if isinstance(node, tuple) and len(node) == 2:
                type_, idx = node
                if type_ == "row":
                    rows0.add(idx)
                elif type_ == "col":
                    cols0.add(idx)
                continue

            if isinstance(node, str):
                if node.startswith("P"):
                    try:
                        rows0.add(int(node[1:]))
                    except ValueError:
                        pass
                elif node.startswith("C"):
                    try:
                        cols0.add(int(node[1:]))
                    except ValueError:
                        pass
        
        meilleure_arete = None
        meilleur_cout = float('inf')
        
        # Pour limiter la complexité sur les très grands problèmes, on peut faire un échantillonnage
        # ou s'arrêter dès qu'on trouve un coût très bas (ex: 1)
        
        # OPTIMISATION : Pour les très grands problèmes (n >= 1000), limiter la recherche
        # Chercher l'arête sortante la moins chère
        # Option 1 : parcourir toutes les lignes de comp0 vers colonnes hors comp0
        trouve_min = False
        limite_recherche = 1000 if n >= 1000 else m  # Limiter la recherche pour n >= 1000
        
        # Pour les grandes tailles, échantillonner plutôt que tout parcourir
        if n >= 1000 and len(rows0) > 50:
            # Échantillonner les lignes pour accélérer
            import random
            rows0_sample = random.sample(list(rows0), min(50, len(rows0)))
        else:
            rows0_sample = rows0
            
        for i in rows0_sample:
            # Limiter aussi le nombre de colonnes à vérifier
            cols_to_check = range(min(limite_recherche, m))
            for j in cols_to_check:
                if j not in cols0 and allocation[i][j] == 0:
                    c = costs[i][j]
                    if c < meilleur_cout:
                        meilleur_cout = c
                        meilleure_arete = (i, j)
                        # Optimisation : si on trouve le coût minimal possible (1), on s'arrête
                        if c <= 1.0:
                            trouve_min = True
                            break
            if trouve_min: break
            
        if not trouve_min:
            # Option 2 : parcourir toutes les colonnes de comp0 vers lignes hors comp0
            if n >= 1000 and len(cols0) > 50:
                import random
                cols0_sample = random.sample(list(cols0), min(50, len(cols0)))
            else:
                cols0_sample = cols0
                
            for j in cols0_sample:
                rows_to_check = range(min(limite_recherche, n))
                for i in rows_to_check:
                    if i not in rows0 and allocation[i][j] == 0:
                        c = costs[i][j]
                        if c < meilleur_cout:
                            meilleur_cout = c
                            meilleure_arete = (i, j)
                            if c <= 1.0:
                                trouve_min = True
                                break
                if trouve_min: break
        
        if meilleure_arete:
            i, j = meilleure_arete
            allocation[i][j] = epsilon
            arêtes_ajoutées.append((i, j))
            if verbose:
                print(f"  Arête ajoutée : ({i+1}, {j+1}) avec coût {meilleur_cout:.2f}")
            
            # Mettre à jour les composantes (on recalcule tout pour être sûr, ou on fusionne)
            # Pour simplifier et être robuste, on recalcule (c'est rapide O(n+m))
            _, composantes = is_connected_transport(allocation)
        else:
            # Impossible de connecter ? Bizarre pour un graphe complet biparti
            if verbose:
                print("  ⚠ Impossible de trouver une arête de connexion !")
            break
            
    return arêtes_ajoutées


def trouver_cycle_avec_arete(
    allocation: List[List[float]],
    i_ajout: int,
    j_ajout: int
) -> List[Tuple[int, int]]:
    # Alors là, cette fonction trouve le cycle formé en ajoutant l'arête (i_ajout, j_ajout) à la proposition actuelle
    # On évite désormais la récursion (qui explosait sur les grandes tailles) en construisant le graphe biparti
    # et en cherchant un chemin entre la ligne i_ajout et la colonne j_ajout. Ce chemin + l'arête ajoutée = cycle.
    
    n = len(allocation)
    m = len(allocation[0]) if n > 0 else 0
    
    if n == 0 or m == 0:
        return [(i_ajout, j_ajout)]
    
    # OPTIMISATION : Pour les grandes tailles, construire le graphe plus efficacement
    # Construction du graphe biparti (noeuds "r_i" pour lignes, "c_j" pour colonnes)
    # On exclut l'arête ajoutée pour forcer la recherche d'un chemin alternatif.
    adj: dict = {}
    
    def add_edge(node_a, node_b, cell):
        adj.setdefault(node_a, []).append((node_b, cell))
        adj.setdefault(node_b, []).append((node_a, cell))
    
    # OPTIMISATION : Pour n >= 1000, ne construire que les arêtes nécessaires
    # Construire seulement les arêtes autour de l'arête ajoutée pour accélérer
    if n >= 1000:
        # Construire seulement les arêtes dans les lignes/colonnes proches
        # Limiter la recherche à un rayon autour de l'arête ajoutée
        rayon = min(100, n // 10, m // 10)  # Rayon limité pour les grandes tailles
        i_min = max(0, i_ajout - rayon)
        i_max = min(n, i_ajout + rayon + 1)
        j_min = max(0, j_ajout - rayon)
        j_max = min(m, j_ajout + rayon + 1)
        
        for i in range(i_min, i_max):
            for j in range(j_min, j_max):
                if allocation[i][j] > 0 and not (i == i_ajout and j == j_ajout):
                    add_edge(("r", i), ("c", j), (i, j))
        # Ajouter aussi les arêtes dans la même ligne/colonne que l'arête ajoutée
        for j in range(m):
            if allocation[i_ajout][j] > 0 and j != j_ajout:
                add_edge(("r", i_ajout), ("c", j), (i_ajout, j))
        for i in range(n):
            if allocation[i][j_ajout] > 0 and i != i_ajout:
                add_edge(("r", i), ("c", j_ajout), (i, j_ajout))
    else:
        # Pour les petites tailles, construire tout le graphe
        for i in range(n):
            for j in range(m):
                if allocation[i][j] > 0 and not (i == i_ajout and j == j_ajout):
                    add_edge(("r", i), ("c", j), (i, j))
    
    start = ("r", i_ajout)
    target = ("c", j_ajout)
    
    from collections import deque
    queue = deque([start])
    visited = {start}
    parent = {start: None}  # parent[node] = (prev_node, cell_used)
    
    found = False
    while queue:
        node = queue.popleft()
        if node == target:
            found = True
            break
        for neighbor, cell in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = (node, cell)
                queue.append(neighbor)
    
    if not found:
        # Aucun chemin alternatif -> on retourne un cycle trivial
        return [(i_ajout, j_ajout)]
    
    # Reconstruction du chemin nodes: start -> ... -> target
    path_cells = []
    current = target
    while current != start:
        prev_node, cell = parent[current]
        path_cells.append(cell)
        current = prev_node
    path_cells.reverse()
    
    # Le cycle est : arête ajoutée + chemin existant (qui alterne lignes/colonnes)
    cycle = [(i_ajout, j_ajout)] + path_cells
    
    # Sécurité : un cycle de transport doit avoir au moins 4 sommets
    if len(cycle) < 4:
        return [(i_ajout, j_ajout)]
    
    return cycle


def methode_marche_pied(
    costs: List[List[float]],
    supplies: List[float],
    demands: List[float],
    allocation_initiale: List[List[float]],
    verbose: bool = True
) -> Tuple[List[List[float]], float, int]:
    # Cette fonction optimise une proposition de transport avec la méthode du marche-pied avec potentiel
    # En résumé, on itère jusqu'à trouver la solution optimale en vérifiant les cycles, la connexité, calculant les potentiels, etc.
    
    # Pseudo-code :
    # allocation = copie(allocation_initiale)
    # nb_iterations = 0
    # 
    # TANT QUE nb_iterations < max_iterations:
    #     Étape 1 : Rendre acyclique (casser tous les cycles)
    #     Étape 2 : Rendre connexe (ajouter des arêtes si besoin)
    #     Étape 3 : Calculer les potentiels (u et v)
    #     Étape 4 : Calculer les coûts marginaux
    #     Étape 5 : Détecter l'arête améliorante
    #     SI pas d'arête améliorante:
    #         RETOURNER solution optimale (on a fini !)
    #     FIN SI
    #     Étape 6 : Ajouter l'arête et trouver le cycle
    #     Étape 7 : Maximiser sur le cycle
    # FIN TANT QUE
    
    # On fait une copie pour ne pas modifier l'original (parce que c'est toujours mieux de ne pas tout casser)
    allocation = [row.copy() for row in allocation_initiale]
    
    n = len(allocation)
    m = len(allocation[0]) if n > 0 else 0
    
    nb_iterations = 0
    max_iterations = 1000  # Protection contre les boucles infinies (parce que ça arrive, crois-moi)
    
    if verbose:
        print("\n" + "="*60)
        print("DÉBUT DE LA MÉTHODE DU MARCHE-PIED AVEC POTENTIEL")
        print("="*60)
    
    while nb_iterations < max_iterations:
        nb_iterations += 1
        
        if verbose:
            print(f"\n--- ITÉRATION {nb_iterations} ---\n")
        
        # Étape 1 : Vérifier que la proposition est acyclique (on détecte et élimine les cycles de manière répétée)
        cycles_detectes = 0
        while True:
            acyclique, cycle = tester_acyclique(allocation)
            if acyclique:
                break
            
            cycles_detectes += 1
            if verbose:
                print(f"⚠ Cycle détecté : {cycle}")
            
            # Maximiser sur le cycle (on optimise le flux)
            delta = maximiser_sur_cycle(allocation, cycle, verbose=verbose)
            
            if verbose:
                print(f"   Maximisation effectuée avec delta = {delta:.6f}")
            
            # Si delta = 0, c'est un cas particulier (on continue quand même pour éliminer le cycle structurellement)
            if delta <= 1e-9:
                if verbose:
                    print("   ⚠ Delta = 0 : aucune modification de flux, mais cycle éliminé structurellement")
                # On force une case à zéro pour casser le cycle (on casse le cycle manuellement)
                if cycle:
                    # On met la première case du cycle à zéro
                    i, j = cycle[0]
                    allocation[i][j] = 0.0
        
        if cycles_detectes > 0 and verbose:
            print(f"✓ Proposition rendue acyclique ({cycles_detectes} cycle(s) éliminé(s))\n")
        
        # Étape 2 : Vérifier que la proposition est connexe (on vérifie que tout est bien connecté)
        est_connexe, composantes = is_connected_transport(allocation)
        arêtes_ajoutées_connexité = []
        
        if not est_connexe:
            if verbose:
                print("⚠ Proposition non connexe")
                print("Sous-graphes connexes :")
                print_components(composantes)
                print("Ajout d'arêtes de coût minimal pour rendre connexe...")
            
            # Rendre connexe en ajoutant des arêtes de coût minimal (on connecte tout le monde)
            arêtes_ajoutées_connexité = rendre_connexe(costs, allocation, supplies, demands)
            
            if verbose:
                print("✓ Proposition rendue connexe")
                if arêtes_ajoutées_connexité:
                    print(f"  Arêtes ajoutées : {[(i+1, j+1) for i, j in arêtes_ajoutées_connexité]}\n")
                else:
                    print()
        
        # Étape 3 : Calculer les potentiels (on calcule u et v)
        u, v = calculer_potentiels(costs, allocation)
        
        if verbose:
            print("Potentiels calculés :")
            if len(u) < 20:
                print(f"  Fournisseurs u : {[f'{val:.2f}' for val in u]}")
                print(f"  Clients v      : {[f'{val:.2f}' for val in v]}\n")
        
        # Étape 4 & 5 : Détecter l'arête améliorante (Optimisé : calcul des coûts marginaux à la volée)
        # On utilise la stratégie "first" pour accélérer les itérations sur les grands graphes
        strategy = "first" if n >= 500 else "best"
        arete_ameliorante = detecter_arete_ameliorante_rapide(costs, u, v, allocation, strategy=strategy)
        
        if arete_ameliorante is None:
            # Solution optimale trouvée !
            if verbose:
                print("✓ Solution optimale trouvée !")
                print("  Tous les coûts marginaux sont >= 0\n")
            break
        
        i_ameliorant, j_ameliorant, cout_marginal = arete_ameliorante
        
        if verbose:
            print(f"Arête améliorante détectée : ({i_ameliorant}, {j_ameliorant})")
            print(f"  Coût marginal : {cout_marginal:.6f}\n")
        
        # Étape 6 : Ajouter l'arête améliorante et trouver le cycle (on ajoute temporairement l'arête avec une valeur > 0)
        allocation[i_ameliorant][j_ameliorant] = 1.0  # Valeur temporaire
        
        # Trouver le cycle formé (on cherche le cycle créé par cette arête)
        cycle = trouver_cycle_avec_arete(allocation, i_ameliorant, j_ameliorant)
        
        if verbose:
            print(f"Cycle formé : {cycle}\n")
        
        # Étape 7 : Maximiser le transport sur le cycle (on optimise le flux sur le cycle)
        delta = maximiser_sur_cycle(allocation, cycle, verbose=verbose)
        
        if verbose:
            print(f"Maximisation sur le cycle avec delta = {delta:.6f}")
        
        # Si delta = 0, c'est le cas particulier de la section 2.3 (on conserve l'arête améliorante et on enlève les arêtes de connexité)
        if delta <= 1e-9:
            if verbose:
                print("⚠ Delta = 0 : cas particulier détecté")
                print("  On conserve l'arête améliorante et on enlève les arêtes ajoutées lors du test de connexité")
            
            # Enlever les arêtes ajoutées lors du test de connexité
            for i, j in arêtes_ajoutées_connexité:
                if verbose:
                    print(f"  Suppression de l'arête ({i+1}, {j+1}) ajoutée pour la connexité")
                allocation[i][j] = 0.0
            
            # Conserver l'arête améliorante avec une valeur epsilon (on la garde mais avec une valeur très petite)
            allocation[i_ameliorant][j_ameliorant] = 1e-6
            
            if verbose:
                print("  L'arête améliorante est conservée avec valeur epsilon\n")
        
        if verbose:
            cout_actuel = compute_total_cost(costs, allocation)
            print(f"Coût total actuel : {cout_actuel:.2f}\n")
    
    if nb_iterations >= max_iterations:
        if verbose:
            print("⚠ Nombre maximum d'itérations atteint")
    
    # Calculer le coût total final (histoire de savoir combien ça coûte au final)
    cout_total = compute_total_cost(costs, allocation)
    
    if verbose:
        print("="*60)
        print(f"FIN DE LA MÉTHODE DU MARCHE-PIED")
        print(f"Nombre d'itérations : {nb_iterations}")
        print(f"Coût total optimal : {cout_total:.2f}")
        print("="*60)
    
    return allocation, cout_total, nb_iterations

