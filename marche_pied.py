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
    detecter_arete_ameliorante
)
from transport_problem import compute_total_cost


def rendre_connexe(
    costs: List[List[float]],
    allocation: List[List[float]],
    supplies: List[float],
    demands: List[float],
    verbose: bool = False
) -> List[Tuple[int, int]]:
    # Alors là, cette fonction rend la proposition de transport connexe en ajoutant des arêtes classées selon des coûts croissants
    # En clair, on complète le graphe avec des arêtes de coût minimal jusqu'à ce qu'il soit connexe
    
    # Pseudo-code :
    # SI le graphe est déjà connexe:
    #     RETOURNER liste vide (c'est déjà bon, on peut partir)
    # FIN SI
    # 
    # Collecter toutes les arêtes possibles (cases avec allocation == 0)
    # Trier par coût croissant (on prend les moins chères d'abord)
    # 
    # POUR chaque arête (par ordre croissant):
    #     SI le graphe est déjà connexe:
    #         ARRÊTER (on a fini)
    #     FIN SI
    #     Ajouter l'arête avec valeur epsilon (très petite, histoire de pas trop changer le coût)
    # FIN POUR
    # 
    # RETOURNER arêtes_ajoutées
    
    n = len(allocation)
    m = len(allocation[0]) if n > 0 else 0
    
    # On vérifie d'abord si c'est déjà connexe (parce que si c'est déjà bon, on peut partir)
    est_connexe, _ = is_connected_transport(allocation)
    if est_connexe:
        return []
    
    # Collecter toutes les arêtes possibles (cases avec allocation == 0) et les classer par coût croissant
    arêtes_candidates = []
    for i in range(n):
        for j in range(m):
            if allocation[i][j] == 0:  # Case non utilisée
                arêtes_candidates.append((i, j, costs[i][j]))
    
    # Trier par coût croissant (on prend les moins chères d'abord)
    arêtes_candidates.sort(key=lambda x: x[2])  # x[2] est le coût
    
    epsilon = 1e-6  # Valeur très petite pour rendre connexe sans changer significativement le coût (malin n'est ce pas ?)
    arêtes_ajoutées = []
    
    if verbose:
        print(f"  Recherche d'arêtes pour rendre connexe (parmi {len(arêtes_candidates)} candidates)...")
    
    # Ajouter les arêtes une par une par ordre de coût croissant jusqu'à ce que le graphe soit connexe
    for i, j, cout in arêtes_candidates:
        # Vérifier si le graphe est déjà connexe (on vérifie à chaque fois, au cas où)
        est_connexe, _ = is_connected_transport(allocation)
        if est_connexe:
            if verbose:
                print(f"  ✓ Graphe devenu connexe après {len(arêtes_ajoutées)} arête(s) ajoutée(s)")
            break
        
        # Ajouter cette arête (on la met avec une valeur epsilon, c'est suffisant)
        allocation[i][j] = epsilon
        arêtes_ajoutées.append((i, j))
        
        if verbose:
            print(f"  Arête ajoutée : ({i+1}, {j+1}) avec coût {cout:.2f}")
    
    # Vérification finale (histoire d'être sûr que tout est bon)
    est_connexe_final, _ = is_connected_transport(allocation)
    if not est_connexe_final and verbose:
        print(f"  ⚠ Attention : le graphe n'est toujours pas connexe après avoir ajouté {len(arêtes_ajoutées)} arête(s)")
    
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
    
    # Construction du graphe biparti (noeuds "r_i" pour lignes, "c_j" pour colonnes)
    # On exclut l'arête ajoutée pour forcer la recherche d'un chemin alternatif.
    adj: dict = {}
    
    def add_edge(node_a, node_b, cell):
        adj.setdefault(node_a, []).append((node_b, cell))
        adj.setdefault(node_b, []).append((node_a, cell))
    
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
            print(f"  Fournisseurs u : {[f'{val:.2f}' for val in u]}")
            print(f"  Clients v      : {[f'{val:.2f}' for val in v]}\n")
        
        # Étape 4 : Calculer les coûts marginaux (pour voir où on peut améliorer)
        marginals = calculer_couts_marginaux(costs, u, v)
        
        # Étape 5 : Détecter l'arête améliorante (on cherche une arête qui peut améliorer le coût)
        arete_ameliorante = detecter_arete_ameliorante(marginals, allocation)
        
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

