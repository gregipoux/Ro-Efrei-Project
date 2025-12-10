# Alors là, ce fichier contient toutes les fonctions d'affichage pour les tableaux du problème de transport
# En clair, l'alignement des colonnes est crucial : toute table avec des colonnes qui se décalent sera très lourdement sanctionnée
# Pour faire simple : on formate tous les nombres avec le même nombre de décimales pour garantir un alignement parfait

# Fonction qui formate un tableau en chaîne de caractères avec colonnes alignées
def format_table(headers, rows, title=None, decimal_places=2):
    # Cette fonction formate un tableau avec colonnes parfaitement alignées
    # En clair, on formate tous les nombres avec le même nombre de décimales pour garantir l'alignement
    
    # Fonction pour formater une cellule (nombre ou texte, on s'adapte)
    def format_cell(cell):
        # Si c'est un nombre, on le formate avec le bon nombre de décimales
        if isinstance(cell, (int, float)):
            return f"{cell:.{decimal_places}f}"
        return str(cell)
    
    # Formater toutes les cellules (on formate TOUT pour être sûr)
    formatted_rows = [[format_cell(cell) for cell in row] for row in rows]
    formatted_headers = [format_cell(cell) for cell in headers]
    
    # On calcule la largeur maximale de chaque colonne (on inclut les en-têtes dans le calcul)
    all_rows = [formatted_headers] + formatted_rows
    cols = list(zip(*all_rows))  # Transposer pour avoir les colonnes (c'est pratique)
    col_widths = [max(len(str(cell)) for cell in col) for col in cols]

    # Fonction interne pour formater une ligne (on aligne tout à droite)
    def format_row(row):
        return " | ".join(str(cell).rjust(width) for cell, width in zip(row, col_widths))

    lines = []
    if title:
        lines.append(title)
        lines.append("-" * len(title))

    # Ligne d'en-têtes
    lines.append(format_row(formatted_headers))
    # Séparateur (on met un séparateur pour que ce soit joli)
    lines.append("-" * (sum(col_widths) + 3 * (len(col_widths) - 1)))

    # Lignes de données (on affiche toutes les lignes)
    for row in formatted_rows:
        lines.append(format_row(row))

    return "\n".join(lines)


# Fonction qui affiche la matrice des coûts de transport
def print_cost_matrix(costs, row_labels, col_labels):
    # Alors là, on affiche la matrice des coûts de transport (c'est notre point de départ)
    headers = [""] + col_labels
    rows = []
    for label, row in zip(row_labels, costs):
        rows.append([label] + row)

    table_str = format_table(headers, rows, title="Matrice des coûts")
    print(table_str)


# Fonction qui affiche la matrice de la proposition de transport
def print_transport_matrix(transport, row_labels, col_labels):
    # En clair, on affiche la matrice de la proposition de transport (pour voir ce qu'on a trouvé)
    headers = [""] + col_labels
    rows = []
    for label, row in zip(row_labels, transport):
        rows.append([label] + row)

    table_str = format_table(headers, rows, title="Proposition de transport")
    print(table_str)


# Fonction qui affiche les potentiels des sommets (fournisseurs et clients)
def print_potentials(u, v, row_labels, col_labels):
    # on affiche les potentiels des sommets (fournisseurs et clients, c'est pour voir les valeurs)
    headers = ["Sommet", "Type", "Potentiel"]
    rows = []

    for label, val in zip(row_labels, u):
        rows.append([label, "Fournisseur", val])
    for label, val in zip(col_labels, v):
        rows.append([label, "Client", val])

    table_str = format_table(headers, rows, title="Potentiels")
    print(table_str)


# Fonction qui affiche la table des coûts potentiels
def print_potential_costs(couts_potentiels, row_labels, col_labels):
    # on affiche la table des coûts potentiels (u_i + v_j pour toutes les cases)
    headers = [""] + col_labels
    rows = []
    for label, row in zip(row_labels, couts_potentiels):
        rows.append([label] + row)

    table_str = format_table(headers, rows, title="Table des coûts potentiels")
    print(table_str)


# Fonction qui affiche la table des coûts marginaux
def print_marginal_costs(marginals, row_labels, col_labels):
    # En clair, on affiche la table des coûts marginaux (c_ij - (u_i + v_j) pour toutes les cases)
    headers = [""] + col_labels
    rows = []
    for label, row in zip(row_labels, marginals):
        rows.append([label] + row)

    table_str = format_table(headers, rows, title="Table des coûts marginaux")
    print(table_str)
