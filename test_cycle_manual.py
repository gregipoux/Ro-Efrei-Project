from cyclique import tester_acyclique, maximiser_sur_cycle

def run_manual_test():
    print("=== Verification Manuelle de la Logique Cyclique ===")
    
    # 1. Cas Acyclique (Diagonale - comme example_cyclique.txt)
    print("\n1. Test Cas Acyclique (Diagonale):")
    matrix = [
        [150.0, 0.0, 0.0],
        [0.0, 150.0, 0.0],
        [0.0, 0.0, 150.0]
    ]
    acyclic, cycle = tester_acyclique(matrix)
    print(f"   Matrice: {matrix}")
    print(f"   Est acyclique? {acyclic} (Attendu: True)")
    if not acyclic:
        print(f"   Cycle détecté: {cycle}")

    # 2. Cas Cyclique (4 coins)
    print("\n2. Test Cas Cyclique (Carré):")
    # On crée un cycle explicite:
    # (0,0)=50  (0,1)=50
    # (1,0)=50  (1,1)=50
    matrix_cycle = [
        [50.0, 50.0, 0.0],
        [50.0, 50.0, 0.0],
        [0.0, 0.0, 150.0]
    ]
    acyclic, cycle = tester_acyclique(matrix_cycle)
    print(f"   Matrice: {matrix_cycle}")
    print(f"   Est acyclique? {acyclic} (Attendu: False)")
    
    if not acyclic:
        print(f"   Cycle détecté: {cycle}")
        
        # Test de maximisation
        print("\n   Test de Maximisation sur le cycle:")
        delta = maximiser_sur_cycle(matrix_cycle, cycle)
        print(f"   Delta calculé: {delta}")
        print("   Matrice après maximisation:")
        for row in matrix_cycle:
            print(f"   {row}")
            
        # Vérification du résultat
        # Si le cycle était (0,0)-(0,1)-(1,1)-(1,0) ou sens inverse
        # On devrait avoir transféré 50 unités
        # Une diagonale devrait être 0, l'autre 100
        zeros = 0
        hundreds = 0
        for r in range(2):
            for c in range(2):
                if matrix_cycle[r][c] == 0: zeros += 1
                if matrix_cycle[r][c] == 100: hundreds += 1
        
        if zeros == 2 and hundreds == 2:
             print("   ✓ Maximisation réussie (flux redistribué)")
        else:
             print("   ✗ Résultat inattendu")

if __name__ == "__main__":
    run_manual_test()