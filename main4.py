# Fichier : main4.py

from affichage import (
    print_cost_matrix,
    print_transport_matrix,
    print_potentials,
    print_marginal_costs,
)
from connexite import is_connected_transport, print_components


def exemple_demo():
    # Exemple de données fictives pour tester l'affichage et la connexité
    costs = [
        [30, 20, 20],
        [10, 50, 20],
        [50, 40, 30],
    ]
    transport = [
        [10, 20, 0],
        [0, 30, 20],
        [40, 0, 10],
    ]
    row_labels = ["P1", "P2", "P3"]
    col_labels = ["C1", "C2", "C3"]

    # Affichage des tableaux
    print_cost_matrix(costs, row_labels, col_labels)
    print()
    print_transport_matrix(transport, row_labels, col_labels)
    print()

    # Test de connexité
    est_connexe, comps = is_connected_transport(transport)
    if est_connexe:
        print("La proposition de transport est connexe.\n")
    else:
        print("La proposition de transport est NON connexe.\n")
        print("Sous-graphes connexes :")
        print_components(comps)


if __name__ == "__main__":
    exemple_demo()


# Check de l'affichage des fonctions potentielles et coûts marginaux
# from affichage import (
#     print_cost_matrix,
#     print_transport_matrix,
#     print_potentials,
#     print_marginal_costs,
# )


# def test_affichage():
#     # -------- Matrice des coûts --------
#     costs = [
#         [3, 12, 7],
#         [8, 5,  9],
#         [4, 11, 6],
#     ]
#     row_labels = ["P1", "P2", "P3"]
#     col_labels = ["C1", "C2", "C3"]

#     print("\n===== TEST MATRICE DES COÛTS =====\n")
#     print_cost_matrix(costs, row_labels, col_labels)

#     # -------- Proposition de transport --------
#     transport = [
#         [5,  10, 0],
#         [0,  15, 5],
#         [20,  0, 5],
#     ]

#     print("\n===== TEST PROPOSITION DE TRANSPORT =====\n")
#     print_transport_matrix(transport, row_labels, col_labels)

#     # -------- Potentiels (valeurs factices) --------
#     u = [0, 7, 3]     # potentiels fournisseurs
#     v = [2, 4, -1]    # potentiels clients

#     print("\n===== TEST POTENTIELS =====\n")
#     print_potentials(u, v, row_labels, col_labels)

#     # -------- Coûts marginaux (valeurs factices) --------
#     marginals = [
#         [1, -2,  5],
#         [4,  0, -3],
#         [-1, 7,  2],
#     ]

#     print("\n===== TEST COÛTS MARGINAUX =====\n")
#     print_marginal_costs(marginals, row_labels, col_labels)


# if __name__ == "__main__":
#     test_affichage()
