"""
Script principal pour tester les fonctions du problème de transport.
"""

from transport_problem import (
    read_transport_problem,
    northwest_corner_method,
    balas_hammer_method,
    compute_total_cost
)
from cyclique import (
    tester_acyclique,
    maximiser_sur_cycle
)


if __name__ == "__main__":
    # Test avec l'exemple fourni
    example_file = "example_problem.txt"
    
    print("=" * 60)
    print("Test du problème de transport")
    print("=" * 60)
    
    try:
        # 1. Lecture du fichier
        print(f"\n1. Lecture du fichier '{example_file}'...")
        costs, supplies, demands = read_transport_problem(example_file)
        
        n = len(supplies)
        m = len(demands)
        
        print(f"   ✓ Problème lu avec succès : {n} fournisseurs, {m} clients")
        print(f"   ✓ Provisions : {supplies}")
        print(f"   ✓ Commandes : {demands}")
        print(f"   ✓ Somme des provisions : {sum(supplies)}")
        print(f"   ✓ Somme des commandes : {sum(demands)}")
        
        # Afficher la matrice des coûts
        print(f"\n   Matrice des coûts ({n}x{m}):")
        for i in range(n):
            print(f"   {costs[i]}")
        
        # 2. Algorithme Nord-Ouest
        print(f"\n2. Algorithme du coin Nord-Ouest...")
        allocation_no = northwest_corner_method(supplies, demands)
        
        print(f"   ✓ Solution initiale calculée")
        print(f"   Matrice d'allocation:")
        for i in range(n):
            print(f"   {allocation_no[i]}")
        
        # Vérifier les contraintes
        print(f"\n   Vérification des contraintes:")
        for i in range(n):
            row_sum = sum(allocation_no[i])
            print(f"   Fournisseur {i+1}: alloué {row_sum:.1f}, provision {supplies[i]:.1f} {'✓' if abs(row_sum - supplies[i]) < 1e-6 else '✗'}")
        
        for j in range(m):
            col_sum = sum(allocation_no[i][j] for i in range(n))
            print(f"   Client {j+1}: reçu {col_sum:.1f}, commande {demands[j]:.1f} {'✓' if abs(col_sum - demands[j]) < 1e-6 else '✗'}")
        
        cost_no = compute_total_cost(costs, allocation_no)
        print(f"   Coût total : {cost_no:.2f}")
        
        # 2.b Test cyclique + maximisation sur cycle pour Nord-Ouest
        print(f"\n2.b Test de cyclicité (Nord-Ouest)...")
        # Faire une copie pour ne pas modifier l'original
        allocation_no_copy = [row.copy() for row in allocation_no]
        acyclique_no, cycle_no = tester_acyclique(allocation_no_copy)
        
        if acyclique_no:
            print("   ✓ Proposition Nord-Ouest acyclique")
        else:
            print(f"   ⚠ Cycle détecté : {cycle_no}")
            delta_no = maximiser_sur_cycle(allocation_no_copy, cycle_no)
            print(f"   Maximisation effectuée avec delta = {delta_no:.2f}")
            if delta_no > 1e-9:
                print("   Nouvelle matrice d'allocation (Nord-Ouest) après maximisation :")
                for i in range(n):
                    print(f"   {allocation_no_copy[i]}")
            else:
                print("   Delta = 0 : aucune modification (cas particulier mentionné dans les instructions)")
        
        # 3. Algorithme Balas-Hammer
        print(f"\n3. Algorithme de Balas-Hammer...")
        allocation_bh = balas_hammer_method(costs, supplies, demands)
        
        print(f"   ✓ Solution initiale calculée")
        print(f"   Matrice d'allocation:")
        for i in range(n):
            print(f"   {allocation_bh[i]}")
        
        # Vérifier les contraintes
        print(f"\n   Vérification des contraintes:")
        for i in range(n):
            row_sum = sum(allocation_bh[i])
            print(f"   Fournisseur {i+1}: alloué {row_sum:.1f}, provision {supplies[i]:.1f} {'✓' if abs(row_sum - supplies[i]) < 1e-6 else '✗'}")
        
        for j in range(m):
            col_sum = sum(allocation_bh[i][j] for i in range(n))
            print(f"   Client {j+1}: reçu {col_sum:.1f}, commande {demands[j]:.1f} {'✓' if abs(col_sum - demands[j]) < 1e-6 else '✗'}")
        
        cost_bh = compute_total_cost(costs, allocation_bh)
        print(f"   Coût total : {cost_bh:.2f}")
        
        # 3.b Test cyclique + maximisation sur cycle pour Balas-Hammer
        print(f"\n3.b Test de cyclicité (Balas-Hammer)...")
        # Faire une copie pour ne pas modifier l'original
        allocation_bh_copy = [row.copy() for row in allocation_bh]
        acyclique_bh, cycle_bh = tester_acyclique(allocation_bh_copy)
        
        if acyclique_bh:
            print("   ✓ Proposition Balas-Hammer acyclique")
        else:
            print(f"   ⚠ Cycle détecté : {cycle_bh}")
            delta_bh = maximiser_sur_cycle(allocation_bh_copy, cycle_bh)
            print(f"   Maximisation effectuée avec delta = {delta_bh:.2f}")
            if delta_bh > 1e-9:
                print("   Nouvelle matrice d'allocation (Balas-Hammer) après maximisation :")
                for i in range(n):
                    print(f"   {allocation_bh_copy[i]}")
            else:
                print("   Delta = 0 : aucune modification (cas particulier mentionné dans les instructions)")
        
        # 4. Comparaison
        print(f"\n4. Comparaison des solutions:")
        print(f"   Nord-Ouest : coût = {cost_no:.2f}")
        print(f"   Balas-Hammer : coût = {cost_bh:.2f}")
        if cost_bh < cost_no:
            print(f"   → Balas-Hammer donne une meilleure solution initiale (différence : {cost_no - cost_bh:.2f})")
        elif cost_no < cost_bh:
            print(f"   → Nord-Ouest donne une meilleure solution initiale (différence : {cost_bh - cost_no:.2f})")
        else:
            print(f"   → Les deux algorithmes donnent le même coût")
        
        print(f"\n{'=' * 60}")
        print("Tous les tests ont réussi !")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"✗ Erreur : {e}")
    except ValueError as e:
        print(f"✗ Erreur : {e}")
    except Exception as e:
        print(f"✗ Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()

