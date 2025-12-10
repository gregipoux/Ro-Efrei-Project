# Alors là, ce fichier contient les fonctions pour calculer les potentiels et les coûts marginaux
# En résumé, pour une proposition de transport, on calcule les potentiels u_i (fournisseurs) et v_j (clients)
# tels que pour chaque arête basique (case avec allocation > 0), on ait : u_i + v_j = c_ij
# Une fois qu'on a les potentiels, on peut calculer les coûts marginaux pour voir si on peut améliorer la solution

from collections import deque
from typing import List, Tuple, Optional


def calculer_potentiels(costs: List[List[float]], allocation: List[List[float]]) -> Tuple[List[float], List[float]]:
    # Alors là, cette fonction calcule les potentiels u_i (fournisseurs) et v_j (clients) pour une proposition de transport
    # En résumé, on résout le système d'équations u_i + v_j = c_ij pour toutes les arêtes basiques
    # Pour faire simple : on fixe arbitrairement u_0 = 0, puis on propage les valeurs avec un parcours en largeur (BFS)
    
    # Pseudo-code :
    # u = [None, None, ..., None]  (n éléments)
    # v = [None, None, ..., None]  (m éléments)
    # aretes_basiques = toutes les cases (i,j) avec allocation[i][j] > 0
    # Fixer arbitrairement u[0] = 0
    # Parcours en largeur pour propager les potentiels
    # Mettre à zéro les potentiels non calculés (graphe non connexe)
    
    n = len(allocation)
    m = len(allocation[0]) if n > 0 else 0
    
    # Initialiser les potentiels à None (non calculés, on va les calculer après)
    u = [None] * n  # Potentiels des fournisseurs
    v = [None] * m  # Potentiels des clients
    
    # Trouver toutes les arêtes basiques (cases avec allocation > 0, c'est notre point de départ)
    aretes_basiques = []
    for i in range(n):
        for j in range(m):
            if allocation[i][j] > 0:
                aretes_basiques.append((i, j))
    
    # Si aucune arête basique, on retourne des potentiels à zéro (pas de calcul à faire)
    if not aretes_basiques:
        return [0.0] * n, [0.0] * m
    
    # On fixe arbitrairement u[0] = 0 pour commencer
    # En clair, seules les différences de potentiels comptent pour les coûts marginaux, donc on peut fixer u[0] = 0
    u[0] = 0.0
    
    # On va utiliser un parcours en largeur pour propager les potentiels (on part du fournisseur 0 et on propage)
    queue = deque()
    
    # On ajoute toutes les arêtes basiques partant du fournisseur 0 (on peut calculer v[j] car on connaît u[0])
    for i, j in aretes_basiques:
        if i == 0 and u[0] is not None:
            # On peut calculer v[j] car on connaît u[0] et c[0][j]
            v[j] = costs[0][j] - u[0]
            queue.append(('client', j))
    
    # Parcours en largeur pour propager les potentiels (on explore tous les voisins)
    while queue:
        node_type, index = queue.popleft()
        
        if node_type == 'client':
            # On est sur un client j, on peut calculer les u[i] des fournisseurs connectés
            j = index
            for i, j_edge in aretes_basiques:
                if j_edge == j and u[i] is None:
                    # On connaît v[j] et c[i][j], donc u[i] = c[i][j] - v[j]
                    u[i] = costs[i][j] - v[j]
                    queue.append(('fournisseur', i))
        
        elif node_type == 'fournisseur':
            # On est sur un fournisseur i, on peut calculer les v[j] des clients connectés
            i = index
            for i_edge, j in aretes_basiques:
                if i_edge == i and v[j] is None:
                    # On connaît u[i] et c[i][j], donc v[j] = c[i][j] - u[i]
                    v[j] = costs[i][j] - u[i]
                    queue.append(('client', j))
    
    # Si certains potentiels n'ont pas été calculés (graphe non connexe par exemple), on les met à zéro par défaut
    for i in range(n):
        if u[i] is None:
            u[i] = 0.0
    for j in range(m):
        if v[j] is None:
            v[j] = 0.0
    
    return u, v


def calculer_couts_potentiels(u: List[float], v: List[float]) -> List[List[float]]:
    # Alors là, cette fonction calcule la table des coûts potentiels : u_i + v_j pour toutes les paires (i,j)
    # En clair, le coût potentiel représente ce que "devrait" coûter le transport de i vers j si on respecte les potentiels
    # On compare ensuite avec le coût réel pour trouver les arêtes améliorantes
    
    n = len(u)
    m = len(v)
    
    couts_potentiels = []
    for i in range(n):
        row = []
        for j in range(m):
            # Le coût potentiel est simplement la somme des potentiels
            row.append(u[i] + v[j])
        couts_potentiels.append(row)
    
    return couts_potentiels


def calculer_couts_marginaux(costs: List[List[float]], u: List[float], v: List[float]) -> List[List[float]]:
    # Alors là, cette fonction calcule la table des coûts marginaux : c_ij - (u_i + v_j) pour toutes les cases
    # En résumé, le coût marginal représente le "gain" (ou la perte) qu'on aurait en ajoutant l'arête (i,j)
    # Si le coût marginal est négatif, on peut améliorer la solution en utilisant cette arête (c'est d'ailleurs notre objectif)
    
    n = len(costs)
    m = len(costs[0]) if n > 0 else 0
    
    marginals = []
    for i in range(n):
        row = []
        for j in range(m):
            # Coût marginal = coût réel - coût potentiel (si négatif, on peut améliorer en ajoutant cette arête)
            marginal = costs[i][j] - (u[i] + v[j])
            row.append(marginal)
        marginals.append(row)
    
    return marginals


def detecter_arete_ameliorante(
    marginals: List[List[float]], 
    allocation: List[List[float]]
) -> Optional[Tuple[int, int, float]]:
    # Alors là, cette fonction détecte l'arête améliorante, c'est-à-dire la case avec le coût marginal le plus négatif
    # En clair, on cherche parmi les cases non-basiques (allocation = 0) celle qui a le coût marginal le plus négatif
    # Si toutes les cases non-basiques ont un coût marginal >= 0, alors la solution est optimale (on a fini !)
    
    n = len(marginals)
    m = len(marginals[0]) if n > 0 else 0
    
    meilleur_i = None
    meilleur_j = None
    meilleur_marginal = 0.0  # On cherche le plus négatif (c'est notre objectif)
    
    # On parcourt toutes les cases non-basiques (allocation = 0, on ne regarde que celles-là)
    for i in range(n):
        for j in range(m):
            # On ne regarde que les cases non-basiques (celles qui ne sont pas encore utilisées)
            if allocation[i][j] == 0:
                marginal = marginals[i][j]
                # Si ce coût marginal est plus négatif que le meilleur trouvé jusqu'ici
                if marginal < meilleur_marginal:
                    meilleur_marginal = marginal
                    meilleur_i = i
                    meilleur_j = j
    
    # Si on a trouvé une arête avec coût marginal négatif, c'est une arête améliorante
    if meilleur_i is not None and meilleur_marginal < 0:
        return (meilleur_i, meilleur_j, meilleur_marginal)
    
    # Sinon, la solution est optimale (tous les coûts marginaux >= 0, on a fini)
    return None

