"""
Script de benchmark pour mesurer le temps d'une opération élémentaire
et le temps total pour compter les opérations élémentaires.
"""

import time
import statistics
from typing import List, Tuple, Dict

def mesurer_temps_operation_elementaire(nb_iterations: int = 1000000) -> Dict[str, float]:
    """
    Mesure le temps moyen d'une opération élémentaire.
    
    Args:
        nb_iterations: Nombre d'itérations pour obtenir une moyenne fiable
    
    Returns:
        Dictionnaire avec les temps moyens pour chaque type d'opération
    """
    resultats = {}
    
    # 1. Addition de deux nombres
    a, b = 1.0, 2.0
    start = time.perf_counter()
    for _ in range(nb_iterations):
        _ = a + b
    end = time.perf_counter()
    temps_addition = (end - start) / nb_iterations
    resultats['addition'] = temps_addition
    
    # 2. Soustraction
    start = time.perf_counter()
    for _ in range(nb_iterations):
        _ = a - b
    end = time.perf_counter()
    temps_soustraction = (end - start) / nb_iterations
    resultats['soustraction'] = temps_soustraction
    
    # 3. Multiplication
    start = time.perf_counter()
    for _ in range(nb_iterations):
        _ = a * b
    end = time.perf_counter()
    temps_multiplication = (end - start) / nb_iterations
    resultats['multiplication'] = temps_multiplication
    
    # 4. Division
    start = time.perf_counter()
    for _ in range(nb_iterations):
        _ = a / b
    end = time.perf_counter()
    temps_division = (end - start) / nb_iterations
    resultats['division'] = temps_division
    
    # 5. Comparaison (<)
    start = time.perf_counter()
    for _ in range(nb_iterations):
        _ = a < b
    end = time.perf_counter()
    temps_comparaison = (end - start) / nb_iterations
    resultats['comparaison'] = temps_comparaison
    
    # 6. Accès à un élément de liste
    liste = [1.0] * 100
    start = time.perf_counter()
    for _ in range(nb_iterations):
        _ = liste[50]
    end = time.perf_counter()
    temps_acces_liste = (end - start) / nb_iterations
    resultats['acces_liste'] = temps_acces_liste
    
    # 7. Affectation
    start = time.perf_counter()
    for _ in range(nb_iterations):
        c = a
    end = time.perf_counter()
    temps_affectation = (end - start) / nb_iterations
    resultats['affectation'] = temps_affectation
    
    # 8. min() de deux nombres
    start = time.perf_counter()
    for _ in range(nb_iterations):
        _ = min(a, b)
    end = time.perf_counter()
    temps_min = (end - start) / nb_iterations
    resultats['min'] = temps_min
    
    return resultats


def mesurer_temps_comptage_operations(
    costs: List[List[float]],
    supplies: List[float],
    demands: List[float]
) -> Tuple[float, int]:
    """
    Mesure le temps total pour compter les opérations élémentaires
    dans l'algorithme Nord-Ouest.
    
    Args:
        costs: Matrice des coûts
        supplies: Liste des provisions
        demands: Liste des commandes
    
    Returns:
        Tuple (temps_total, nombre_operations)
    """
    from transport_problem import northwest_corner_method
    
    # Compteurs d'opérations élémentaires
    nb_additions = 0
    nb_soustractions = 0
    nb_comparaisons = 0
    nb_affectations = 0
    nb_acces_memoire = 0
    nb_min = 0
    
    n = len(supplies)
    m = len(demands)
    
    # Mesurer le temps de comptage
    start = time.perf_counter()
    
    # Simuler l'algorithme Nord-Ouest avec comptage
    allocation = [[0.0 for _ in range(m)] for _ in range(n)]
    nb_affectations += n * m  # Initialisation de la matrice
    
    remaining_supplies = supplies.copy()
    remaining_demands = demands.copy()
    nb_affectations += n + m  # Copie des listes
    
    i = 0
    j = 0
    nb_affectations += 2
    
    while i < n and j < m:
        nb_comparaisons += 2  # i < n et j < m
        
        # allocation_amount = min(remaining_supplies[i], remaining_demands[j])
        nb_acces_memoire += 2  # Accès à remaining_supplies[i] et remaining_demands[j]
        nb_min += 1
        nb_affectations += 1
        allocation_amount = min(remaining_supplies[i], remaining_demands[j])
        
        # allocation[i][j] = allocation_amount
        nb_acces_memoire += 1  # Accès à allocation[i][j]
        nb_affectations += 1
        allocation[i][j] = allocation_amount
        
        # remaining_supplies[i] -= allocation_amount
        nb_acces_memoire += 1
        nb_soustractions += 1
        nb_affectations += 1
        remaining_supplies[i] -= allocation_amount
        
        # remaining_demands[j] -= allocation_amount
        nb_acces_memoire += 1
        nb_soustractions += 1
        nb_affectations += 1
        remaining_demands[j] -= allocation_amount
        
        # Comparaisons pour les conditions
        nb_acces_memoire += 1
        nb_comparaisons += 1
        if remaining_supplies[i] < 1e-9:
            nb_affectations += 1
            i += 1
        else:
            nb_acces_memoire += 1
            nb_comparaisons += 1
            if remaining_demands[j] < 1e-9:
                nb_affectations += 1
                j += 1
    
    end = time.perf_counter()
    temps_total = end - start
    
    nombre_operations = (
        nb_additions + nb_soustractions + nb_comparaisons + 
        nb_affectations + nb_acces_memoire + nb_min
    )
    
    return temps_total, nombre_operations


def benchmark_complet():
    """
    Exécute un benchmark complet et affiche les résultats.
    """
    print("=" * 70)
    print("BENCHMARK DES OPÉRATIONS ÉLÉMENTAIRES")
    print("=" * 70)
    
    # 1. Mesurer le temps d'une opération élémentaire
    print("\n1. Mesure du temps d'une opération élémentaire...")
    print("   (1 000 000 itérations pour obtenir une moyenne fiable)")
    
    resultats_ops = mesurer_temps_operation_elementaire(nb_iterations=1000000)
    
    print("\n   Résultats (temps moyen par opération en secondes):")
    for operation, temps in resultats_ops.items():
        temps_ns = temps * 1e9  # Convertir en nanosecondes
        print(f"   - {operation:15s}: {temps:.2e} s ({temps_ns:.2f} ns)")
    
    # Trouver l'opération la plus rapide (référence)
    operation_la_plus_rapide = min(resultats_ops.items(), key=lambda x: x[1])
    print(f"\n   -> Opération la plus rapide: {operation_la_plus_rapide[0]} "
          f"({operation_la_plus_rapide[1]:.2e} s)")
    
    # 2. Mesurer le temps total pour compter les opérations
    print("\n" + "=" * 70)
    print("2. Mesure du temps total pour compter les opérations élémentaires")
    print("=" * 70)
    
    # Tester avec différentes tailles de problème
    tailles = [10, 50, 100, 500]
    
    print("\n   Résultats pour différentes tailles de problème (n × n):")
    print(f"   {'Taille':<10} {'Temps comptage (s)':<20} {'Nb opérations':<15} {'Temps/op (ns)':<15}")
    print("   " + "-" * 60)
    
    for taille in tailles:
        # Générer un problème aléatoire
        from complexite import generer_probleme_aleatoire
        costs, supplies, demands = generer_probleme_aleatoire(taille, seed=42)
        
        # Mesurer plusieurs fois pour obtenir une moyenne
        temps_mesures = []
        nb_ops_mesures = []
        
        for _ in range(10):  # 10 mesures pour moyenne
            temps, nb_ops = mesurer_temps_comptage_operations(costs, supplies, demands)
            temps_mesures.append(temps)
            nb_ops_mesures.append(nb_ops)
        
        temps_moyen = statistics.mean(temps_mesures)
        nb_ops_moyen = int(statistics.mean(nb_ops_mesures))
        temps_par_op_ns = (temps_moyen / nb_ops_moyen) * 1e9 if nb_ops_moyen > 0 else 0
        
        print(f"   {taille:<10} {temps_moyen:<20.6e} {nb_ops_moyen:<15} {temps_par_op_ns:<15.2f}")
    
    # 3. Comparaison avec le temps d'exécution réel
    print("\n" + "=" * 70)
    print("3. Comparaison: temps de comptage vs temps d'exécution réel")
    print("=" * 70)
    
    from transport_problem import northwest_corner_method
    
    taille_test = 100
    costs, supplies, demands = generer_probleme_aleatoire(taille_test, seed=42)
    
    # Temps d'exécution réel
    start = time.perf_counter()
    allocation = northwest_corner_method(supplies, demands)
    temps_execution_reel = time.perf_counter() - start
    
    # Temps de comptage
    temps_comptage, nb_ops = mesurer_temps_comptage_operations(costs, supplies, demands)
    
    print(f"\n   Taille du problème: {taille_test} × {taille_test}")
    print(f"   Temps d'exécution réel: {temps_execution_reel:.6e} s")
    print(f"   Temps de comptage: {temps_comptage:.6e} s")
    print(f"   Nombre d'opérations comptées: {nb_ops}")
    print(f"   Ratio (comptage/execution): {temps_comptage/temps_execution_reel:.2f}x")
    
    print("\n" + "=" * 70)
    print("BENCHMARK TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    benchmark_complet()


