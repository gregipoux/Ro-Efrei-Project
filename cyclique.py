from collections import deque
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

def est_cycle_transport_valide(cycle: List[Tuple[int,int]]) -> bool:
    # Alors là, cette fonction vérifie si un cycle est un cycle valide pour un problème de transport
    # En clair, un cycle valide doit alterner entre lignes et colonnes (au moins 4 sommets, c'est la règle)
    
    if len(cycle) < 4:
        return False
    
    # Vérifier l'alternance ligne/colonne
    for idx in range(len(cycle)):
        curr = cycle[idx]
        next_cell = cycle[(idx + 1) % len(cycle)]
        
        # Deux cellules consécutives doivent être dans la même ligne OU la même colonne
        same_row = curr[0] == next_cell[0]
        same_col = curr[1] == next_cell[1]
        
        if not (same_row or same_col):
            return False
        
        # Vérifier l'alternance: si on est dans une ligne, le suivant doit être dans une colonne différente
        # et vice versa
        if idx < len(cycle) - 1:
            prev = cycle[idx - 1] if idx > 0 else cycle[-1]
            # Le précédent et le suivant doivent être dans des dimensions différentes
            if prev[0] == curr[0] and next_cell[0] == curr[0]:  # Tous dans la même ligne (pas bon)
                return False
            if prev[1] == curr[1] and next_cell[1] == curr[1]:  # Tous dans la même colonne (pas bon non plus)
                return False
    
    return True

def tester_acyclique(allocation: List[List[float]]) -> Tuple[bool, List[Tuple[int,int]]]:
    # Alors là, cette fonction teste si la proposition de transport est acyclique en utilisant un parcours en largeur (BFS)
    # En résumé, on construit un graphe d'adjacence et on cherche des cycles avec un BFS
    # Si on retourne sur un sommet déjà visité qui n'est pas le parent, c'est qu'il y a un cycle
    # OPTIMISÉ : Utilise des sets et des structures de données plus efficaces pour les grandes tailles
    
    # Pseudo-code :
    # cellules = toutes les cases (i,j) avec allocation[i][j] > 0
    # Construire graphe d'adjacence (voisins dans la même ligne ou colonne)
    # BFS pour détecter cycle
    # Si cycle détecté : reconstruire le cycle et retourner (False, cycle)
    # Sinon : retourner (True, [])
    
    n = len(allocation)
    m = len(allocation[0]) if n > 0 else 0

    # OPTIMISATION : Construire les listes de cellules actives par ligne et colonne pour éviter O(n²) complet
    # Construire liste des cellules basiques (cellules avec allocation > 0, c'est notre point de départ)
    cellules = []
    # Pré-calculer les cellules actives par ligne et colonne pour accélérer la construction du graphe
    cellules_par_ligne: Dict[int, List[Tuple[int,int]]] = {}
    cellules_par_colonne: Dict[int, List[Tuple[int,int]]] = {}
    
    for i in range(n):
        for j in range(m):
            if allocation[i][j] > 0:
                cell = (i, j)
                cellules.append(cell)
                if i not in cellules_par_ligne:
                    cellules_par_ligne[i] = []
                cellules_par_ligne[i].append(cell)
                if j not in cellules_par_colonne:
                    cellules_par_colonne[j] = []
                cellules_par_colonne[j].append(cell)
    
    if len(cellules) == 0:
        return True, []

    # OPTIMISATION : Construire liste d'adjacence plus efficacement en utilisant les pré-calculs
    # Construire liste d'adjacence pour BFS: voisins dans la même ligne ou colonne (on trouve les voisins)
    adj: Dict[Tuple[int,int], List[Tuple[int,int]]] = {}
    for (i,j) in cellules:
        voisins = []
        # même ligne (on utilise la liste pré-calculée)
        if i in cellules_par_ligne:
            for cell in cellules_par_ligne[i]:
                if cell[1] != j:  # Exclure la cellule elle-même
                    voisins.append(cell)
        # même colonne (on utilise la liste pré-calculée)
        if j in cellules_par_colonne:
            for cell in cellules_par_colonne[j]:
                if cell[0] != i:  # Exclure la cellule elle-même
                    voisins.append(cell)
        adj[(i,j)] = voisins

    visite = set()
    parent: Dict[Tuple[int,int], Optional[Tuple[int,int]]] = {}

    # BFS pour détecter cycle (on explore en largeur et on cherche des cycles)
    for start in cellules:
        if start in visite:
            continue
        visite.add(start)
        parent[start] = None
        queue = deque([start])

        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if v not in visite:
                    visite.add(v)
                    parent[v] = u
                    queue.append(v)
                elif parent.get(u) != v:  # v est visité et n'est pas le parent de u -> cycle détecté !
                    # cycle détecté: on retourne sur un sommet déjà visité qui n'est pas le parent (c'est un cycle !)
                    cycle = reconstruire_cycle(u, v, parent)
                    # Vérifier que c'est un cycle valide pour le transport (on vérifie que c'est exploitable)
                    if est_cycle_transport_valide(cycle):
                        return False, cycle
                    # Sinon, continuer la recherche (ce n'est pas un cycle exploitable, on continue)
    return True, []

def reconstruire_cycle(u: Tuple[int,int], v: Tuple[int,int], parent: Dict[Tuple[int,int], Optional[Tuple[int,int]]]) -> List[Tuple[int,int]]:
    # Alors là, cette fonction reconstruit un cycle simple passant par l'arête (u,v) en remontant les chemins vers le LCA
    # En clair, on remonte les chemins de u et v vers la racine, on trouve leur ancêtre commun (LCA), et on construit le cycle
    
    # Construire le chemin de u vers la racine (on remonte en suivant les parents)
    chemin_u = []
    x: Optional[Tuple[int,int]] = u
    while x is not None:
        chemin_u.append(x)
        x = parent.get(x)
    
    # Construire le chemin de v vers la racine (on remonte en suivant les parents aussi)
    chemin_v = []
    y: Optional[Tuple[int,int]] = v
    while y is not None:
        chemin_v.append(y)
        y = parent.get(y)
    
    # Trouver le LCA (Lowest Common Ancestor, l'ancêtre commun le plus proche)
    set_v = set(chemin_v)
    lca: Optional[Tuple[int,int]] = None
    for node in chemin_u:
        if node in set_v:
            lca = node
            break
    
    if lca is None:
        # Si pas de LCA trouvé, le cycle est u -> v directement
        return [u, v]
    
    # Construire le cycle: u -> LCA -> v -> u (cycle = on fait le tour complet)
    cycle = []
    x = u
    while x != lca:
        cycle.append(x)
        x = parent.get(x)
        if x is None:
            break
    cycle.append(lca)
    
    temp = []
    y = v
    while y != lca:
        temp.append(y)
        y = parent.get(y)
        if y is None:
            break
    temp.reverse()
    cycle.extend(temp)
    
    return cycle

def maximiser_sur_cycle(allocation: List[List[float]], cycle: List[Tuple[int,int]], verbose: bool = False) -> float:
    # Alors là, cette fonction maximise le transport sur un cycle détecté
    # En résumé, on alterne les signes + et - sur le cycle, on calcule delta (minimum des cases -), puis on applique delta
    # Si delta = 0, aucune modification n'est effectuée (c'est un cas particulier)
    
    # Pseudo-code :
    # Alterner les signes : cases paires = +, cases impaires = -
    # Delta = minimum des valeurs dans les cases marquées -
    # Appliquer delta : ajouter aux cases +, soustraire aux cases -
    # Si une case devient 0, on la supprime (arête supprimée)
    
    if not cycle or len(cycle) < 4:  # Un cycle doit avoir au moins 4 sommets (c'est la règle)
        return 0.0

    # Alterner les signes: cases paires = +, cases impaires = - (on alterne pour optimiser)
    plus_cases = []
    moins_cases = []
    for idx, (i,j) in enumerate(cycle):
        if idx % 2 == 0:
            plus_cases.append((i,j))
        else:
            moins_cases.append((i,j))

    if verbose:
        print("\n>>> Conditions pour la maximisation sur le cycle <<<")
        print("Cases marquées + (où on ajoute delta) :")
        for (i, j) in plus_cases:
            valeur_avant = allocation[i][j]
            print(f"  Case ({i+1}, {j+1}) = P{i+1} -> C{j+1} : valeur actuelle = {valeur_avant:.2f}")
        print("Cases marquées - (où on soustrait delta) :")
        for (i, j) in moins_cases:
            valeur_avant = allocation[i][j]
            print(f"  Case ({i+1}, {j+1}) = P{i+1} -> C{j+1} : valeur actuelle = {valeur_avant:.2f}")

    # Delta = minimum des valeurs dans les cases marquées - (on prend le minimum pour ne pas rendre négatif)
    if not moins_cases:
        return 0.0
    
    delta = min(allocation[i][j] for (i,j) in moins_cases)
    
    if verbose:
        print(f"\nDelta calculé = min(valeurs des cases -) = {delta:.6f}")
    
    # Si delta = 0, aucune modification (cas mentionné dans les instructions section 2.3, c'est un cas particulier)
    if delta <= 1e-9:
        if verbose:
            print("⚠ Delta = 0 : aucune modification possible")
        return 0.0

    # Appliquer delta: ajouter aux cases +, soustraire aux cases - (on optimise le flux)
    aretes_supprimees = []
    for (i,j) in plus_cases:
        valeur_avant = allocation[i][j]
        allocation[i][j] += delta
        if verbose:
            print(f"  Case ({i+1}, {j+1}) = P{i+1} -> C{j+1} : {valeur_avant:.2f} -> {allocation[i][j]:.2f} (+{delta:.2f})")
    
    for (i,j) in moins_cases:
        valeur_avant = allocation[i][j]
        allocation[i][j] -= delta
        # Mettre à zéro si très proche de zéro (on nettoie les valeurs trop petites)
        if abs(allocation[i][j]) < 1e-9:
            allocation[i][j] = 0.0
            aretes_supprimees.append((i, j))
        
        if verbose:
            if allocation[i][j] == 0.0:
                print(f"  Case ({i+1}, {j+1}) = P{i+1} -> C{j+1} : {valeur_avant:.2f} -> 0.00 (-{delta:.2f}) [SUPPRIMÉE]")
            else:
                print(f"  Case ({i+1}, {j+1}) = P{i+1} -> C{j+1} : {valeur_avant:.2f} -> {allocation[i][j]:.2f} (-{delta:.2f})")
    
    if verbose and aretes_supprimees:
        print(f"\n>>> Arête(s) supprimée(s) à l'issue de la maximisation <<<")
        for (i, j) in aretes_supprimees:
            print(f"  Arête ({i+1}, {j+1}) = P{i+1} -> C{j+1} (mise à zéro)")
    elif verbose:
        print("\n>>> Aucune arête supprimée (toutes les cases - restent > 0) <<<")
    
    return delta
