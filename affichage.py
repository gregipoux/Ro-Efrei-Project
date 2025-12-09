# Fichier : affichage.py

# Fonction qui formate un tableau en chaîne de caractères avec colonnes alignées
def format_table(headers, rows, title=None):
    # On calcule la largeur maximale de chaque colonne
    cols = list(zip(headers, *rows))  # regroupe les colonnes
    col_widths = [max(len(str(cell)) for cell in col) for col in cols]

    # Fonction interne pour formater une ligne
    def format_row(row):
        return " | ".join(str(cell).rjust(width) for cell, width in zip(row, col_widths))

    lines = []
    if title:
        lines.append(title)
        lines.append("-" * len(title))

    # Ligne d'en-têtes
    lines.append(format_row(headers))
    # Séparateur
    lines.append("-" * (sum(col_widths) + 3 * (len(col_widths) - 1)))

    # Lignes de données
    for row in rows:
        lines.append(format_row(row))

    return "\n".join(lines)


# Fonction qui affiche la matrice des coûts de transport
def print_cost_matrix(costs, row_labels, col_labels):
    headers = [""] + col_labels
    rows = []
    for label, row in zip(row_labels, costs):
        rows.append([label] + row)

    table_str = format_table(headers, rows, title="Matrice des coûts")
    print(table_str)


# Fonction qui affiche la matrice de la proposition de transport
def print_transport_matrix(transport, row_labels, col_labels):
    headers = [""] + col_labels
    rows = []
    for label, row in zip(row_labels, transport):
        rows.append([label] + row)

    table_str = format_table(headers, rows, title="Proposition de transport")
    print(table_str)


# Fonction qui affiche les potentiels des sommets (fournisseurs et clients)
def print_potentials(u, v, row_labels, col_labels):
    headers = ["Sommet", "Type", "Potentiel"]
    rows = []

    for label, val in zip(row_labels, u):
        rows.append([label, "Fournisseur", val])
    for label, val in zip(col_labels, v):
        rows.append([label, "Client", val])

    table_str = format_table(headers, rows, title="Potentiels")
    print(table_str)


# Fonction qui affiche la table des coûts marginaux
def print_marginal_costs(marginals, row_labels, col_labels):
    headers = [""] + col_labels
    rows = []
    for label, row in zip(row_labels, marginals):
        rows.append([label] + row)

    table_str = format_table(headers, rows, title="Coûts marginaux")
    print(table_str)
