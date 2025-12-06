from collections import deque
from typing import List, Tuple, Dict, Optional

def est_cycle_transport_valide(cycle: List[Tuple[int,int]]) -> bool:
    """
    Vérifie si un cycle est un cycle valide pour un problème de transport.
    Un cycle valide doit alterner entre lignes et colonnes (au moins 4 sommets).
    
    Paramètres
    ----------
    cycle : List[Tuple[int,int]]
        Liste des cases (i,j) formant le cycle.
    
    Retours
    -------
    bool
        True si le cycle est valide pour la redistribution de flux.
    """
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
        # et vice versa (sauf pour le dernier qui revient au premier)
        if idx < len(cycle) - 1:
            prev = cycle[idx - 1] if idx > 0 else cycle[-1]
            # Le précédent et le suivant doivent être dans des dimensions différentes
            if prev[0] == curr[0] and next_cell[0] == curr[0]:  # Tous dans la même ligne
                return False
            if prev[1] == curr[1] and next_cell[1] == curr[1]:  # Tous dans la même colonne
                return False
    
    return True

def tester_acyclique(allocation: List[List[float]]) -> Tuple[bool, List[Tuple[int,int]]]:
    """
    Teste si la proposition de transport (allocation) est acyclique en utilisant un parcours en largeur (BFS).
    
    Paramètres
    ----------
    allocation : List[List[float]]
        Matrice d'allocation de transport.
    
    Retours
    -------
    Tuple[bool, List[Tuple[int,int]]]
        (True, []) si acyclique, sinon (False, cycle) où cycle est la liste des cases (i,j) formant un cycle.
    
    Détails
    -------
    Utilise un parcours en largeur. Lors de la découverte des sommets, on vérifie si on retourne
    sur un sommet déjà visité et que ce sommet n'est pas le parent du sommet courant.
    Si c'est le cas, alors il existe un cycle.
    """
    n = len(allocation)
    m = len(allocation[0]) if n > 0 else 0

    # Construire liste des cellules basiques (cellules avec allocation > 0)
    cellules = [(i,j) for i in range(n) for j in range(m) if allocation[i][j] > 0]
    
    if len(cellules) == 0:
        return True, []

    # Construire liste d'adjacence pour BFS: voisins dans la même ligne ou colonne
    adj: Dict[Tuple[int,int], List[Tuple[int,int]]] = {}
    for (i,j) in cellules:
        voisins = []
        # même ligne
        for jj in range(m):
            if jj != j and allocation[i][jj] > 0:
                voisins.append((i,jj))
        # même colonne
        for ii in range(n):
            if ii != i and allocation[ii][j] > 0:
                voisins.append((ii,j))
        adj[(i,j)] = voisins

    visite = set()
    parent: Dict[Tuple[int,int], Optional[Tuple[int,int]]] = {}

    # BFS pour détecter cycle
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
                elif parent.get(u) != v:  # v est visité et n'est pas le parent de u -> cycle détecté
                    # cycle détecté: on retourne sur un sommet déjà visité qui n'est pas le parent
                    cycle = reconstruire_cycle(u, v, parent)
                    # Vérifier que c'est un cycle valide pour le transport
                    if est_cycle_transport_valide(cycle):
                        return False, cycle
                    # Sinon, continuer la recherche (ce n'est pas un cycle exploitable)
    return True, []

def reconstruire_cycle(u: Tuple[int,int], v: Tuple[int,int], parent: Dict[Tuple[int,int], Optional[Tuple[int,int]]]) -> List[Tuple[int,int]]:
    """
    Reconstruit un cycle simple passant par l'arête (u,v) en remontant les chemins vers le LCA.
    
    Paramètres
    ----------
    u : Tuple[int,int]
        Premier sommet de l'arête formant le cycle.
    v : Tuple[int,int]
        Second sommet de l'arête formant le cycle (déjà visité).
    parent : Dict[Tuple[int,int], Optional[Tuple[int,int]]]
        Dictionnaire des parents pour chaque sommet.
    
    Retours
    -------
    List[Tuple[int,int]]
        Liste des cases (i,j) formant le cycle.
    """
    # Construire le chemin de u vers la racine
    chemin_u = []
    x: Optional[Tuple[int,int]] = u
    while x is not None:
        chemin_u.append(x)
        x = parent.get(x)
    
    # Construire le chemin de v vers la racine
    chemin_v = []
    y: Optional[Tuple[int,int]] = v
    while y is not None:
        chemin_v.append(y)
        y = parent.get(y)
    
    # Trouver le LCA (Lowest Common Ancestor)
    set_v = set(chemin_v)
    lca: Optional[Tuple[int,int]] = None
    for node in chemin_u:
        if node in set_v:
            lca = node
            break
    
    if lca is None:
        # Si pas de LCA trouvé, le cycle est u -> v directement
        return [u, v]
    
    # Construire le cycle: u -> LCA -> v -> u
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

def maximiser_sur_cycle(allocation: List[List[float]], cycle: List[Tuple[int,int]]) -> float:
    """
    Maximisation du transport sur un cycle détecté.
    
    Paramètres
    ----------
    allocation : List[List[float]]
        Matrice d'allocation de transport (modifiée sur place).
    cycle : List[Tuple[int,int]]
        Liste des cases (i,j) formant le cycle.
    
    Retours
    -------
    float
        Delta appliqué (peut être 0 si aucune modification possible).
    
    Détails
    -------
    On alterne les signes + et - sur le cycle.
    Delta = minimum des valeurs dans les cases marquées -.
    On ajoute delta aux cases + et on soustrait delta aux cases -.
    Si delta = 0, aucune modification n'est effectuée (cas mentionné dans les instructions).
    """
    if not cycle or len(cycle) < 4:  # Un cycle doit avoir au moins 4 sommets
        return 0.0

    # Alterner les signes: cases paires = +, cases impaires = -
    plus_cases = []
    moins_cases = []
    for idx, (i,j) in enumerate(cycle):
        if idx % 2 == 0:
            plus_cases.append((i,j))
        else:
            moins_cases.append((i,j))

    # Delta = minimum des valeurs dans les cases marquées -
    if not moins_cases:
        return 0.0
    
    delta = min(allocation[i][j] for (i,j) in moins_cases)
    
    # Si delta = 0, aucune modification (cas mentionné dans les instructions section 2.3)
    if delta <= 1e-9:
        return 0.0

    # Appliquer delta: ajouter aux cases +, soustraire aux cases -
    for (i,j) in plus_cases:
        allocation[i][j] += delta
    for (i,j) in moins_cases:
        allocation[i][j] -= delta
        # Mettre à zéro si très proche de zéro
        if abs(allocation[i][j]) < 1e-9:
            allocation[i][j] = 0.0
    
    return delta
