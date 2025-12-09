# Fichier : connexite.py

from collections import deque, defaultdict


# Fonction qui construit un graphe biparti à partir de la matrice de transport
def build_graph_from_transport(transport):
    """
    Les sommets sont 'P0..Pn-1' pour les fournisseurs et 'C0..Cm-1' pour les clients.
    On met une arête entre Pi et Cj si transport[i][j] > 0.
    """
    n = len(transport)
    m = len(transport[0]) if n > 0 else 0

    graph = defaultdict(list)

    for i in range(n):
        for j in range(m):
            if transport[i][j] > 0:
                p_node = f"P{i}"
                c_node = f"C{j}"
                graph[p_node].append(c_node)
                graph[c_node].append(p_node)

    # On s'assure que tous les sommets existent, même s'ils sont isolés
    for i in range(n):
        graph[f"P{i}"]
    for j in range(m):
        graph[f"C{j}"]

    return graph


# Fonction qui fait un parcours en largeur (BFS) et renvoie une composante connexe
def bfs_component(graph, start, visited):
    """
    Parcours en largeur à partir de 'start' qui renvoie la liste des sommets
    de la composante connexe contenant 'start'.
    """
    queue = deque([start])
    visited.add(start)
    component = [start]

    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                component.append(neighbor)

    return component


# Fonction qui calcule toutes les composantes connexes du graphe
def connected_components(graph):
    """
    Retourne une liste de composantes connexes, chacune étant une liste de sommets.
    """
    visited = set()
    components = []

    for node in graph.keys():
        if node not in visited:
            comp = bfs_component(graph, node, visited)
            components.append(comp)

    return components


# Fonction qui teste si la proposition de transport est connexe
def is_connected_transport(transport):
    """
    Retourne (est_connexe, composantes) pour la matrice de transport donnée.
    """
    graph = build_graph_from_transport(transport)
    comps = connected_components(graph)
    return len(comps) == 1, comps


# Fonction qui affiche proprement les composantes connexes trouvées
def print_components(components):
    """
    Affiche chaque composante connexe en séparant fournisseurs (Pi) et clients (Cj).
    """
    for idx, comp in enumerate(components, start=1):
        suppliers = sorted([node for node in comp if node.startswith("P")])
        customers = sorted([node for node in comp if node.startswith("C")])
        print(f"Composante {idx}:")
        print(f"  Fournisseurs : {', '.join(suppliers) if suppliers else 'aucun'}")
        print(f"  Clients      : {', '.join(customers) if customers else 'aucun'}")
        print()
