# Alors là, ce fichier contient toutes les fonctions pour l'étude de la complexité des algorithmes
# En résumé, on génère des problèmes aléatoires, on mesure les temps d'exécution, et on trace des graphiques
# Pour faire simple : on veut savoir combien de temps prennent nos algorithmes selon la taille du problème

import random
import time
import os
import sys
import gc  # Garbage collection pour libérer la mémoire entre les itérations
from typing import List, Tuple, Dict
import json
from multiprocessing import Pool, cpu_count
from functools import partial
import traceback

# Import matplotlib for plotting
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from transport_problem import (
    northwest_corner_method,
    balas_hammer_method,
    compute_total_cost
)
from marche_pied import rendre_connexe, trouver_cycle_avec_arete
from cyclique import tester_acyclique, maximiser_sur_cycle
from connexite import is_connected_transport
from potentiels import (
    calculer_potentiels,
    calculer_couts_marginaux,
    detecter_arete_ameliorante
)


def calculer_nb_processus_optimal(nb_processus_desire: int = None) -> int:
    """
    Calcule le nombre optimal de processus à utiliser pour éviter la surchauffe.
    
    Args:
        nb_processus_desire: Nombre de processus souhaité (None pour auto)
    
    Returns:
        Nombre de processus recommandé
    """
    nb_cores = cpu_count()
    
    if nb_processus_desire is not None and nb_processus_desire > 0:
        # Respecter le choix de l'utilisateur mais limiter au maximum disponible
        return min(nb_processus_desire, nb_cores)
    
    # Par défaut : laisser au moins 1-2 cœurs libres
    if nb_cores <= 2:
        return 1
    elif nb_cores <= 4:
        return nb_cores - 1
    else:
        # Pour les systèmes avec beaucoup de cœurs, laisser 2 cœurs libres
        return max(1, nb_cores - 2)


def generer_probleme_aleatoire(n: int, seed: int = None) -> Tuple[List[List[float]], List[float], List[float]]:
    # Alors là, cette fonction génère un problème de transport aléatoire de taille n × n
    # En résumé, on génère les coûts ai,j entre 1 et 100, puis on génère une matrice temp pour calculer les provisions et commandes
    # Pour faire simple : on veut un problème équilibré (somme provisions = somme commandes)
    # Optimisé : on utilise numpy si disponible pour accélérer les calculs
    
    # Pseudo-code :
    # SI seed est fourni:
    #     Initialiser le générateur aléatoire avec seed (pour reproductibilité)
    # FIN SI
    # 
    # Générer matrice des coûts : pour chaque (i,j), ai,j = nombre aléatoire entre 1 et 100
    # Générer matrice temp : pour chaque (i,j), tempi,j = nombre aléatoire entre 1 et 100
    # 
    # Calculer provisions : Pi = somme des tempi,j sur j (pour chaque ligne)
    # Calculer commandes : Cj = somme des tempi,j sur i (pour chaque colonne)
    # 
    # RETOURNER (costs, supplies, demands)
    
    # Essayer d'utiliser numpy pour accélérer (mais on garde la compatibilité sans numpy)
    
    if seed is not None:
        random.seed(seed)
    
    try:
        import numpy as np
        
        # Générer les coûts et la matrice temporaire en une fois avec numpy
        costs = np.random.randint(1, 101, size=(n, n)).astype(float).tolist()
        temp_matrix = np.random.randint(1, 101, size=(n, n)).astype(float)
        
        # Calculer les sommes (provisions et commandes)
        supplies = np.sum(temp_matrix, axis=1).tolist()
        demands = np.sum(temp_matrix, axis=0).tolist()
        
        return costs, supplies, demands
        
    except ImportError:
        # Fallback si numpy n'est pas installé
        costs = [[float(random.randint(1, 100)) for _ in range(n)] for _ in range(n)]
        
        # Pour garantir un problème équilibré, on génère une matrice aléatoire temporaire
        # et on calcule les sommes lignes/colonnes
        temp_matrix = [[float(random.randint(1, 100)) for _ in range(n)] for _ in range(n)]
        
        supplies = [sum(row) for row in temp_matrix]
        demands = [sum(temp_matrix[i][j] for i in range(n)) for j in range(n)]
    
    return costs, supplies, demands


def resoudre_marche_pied_silencieux(
    costs: List[List[float]],
    supplies: List[float],
    demands: List[float],
    allocation_initiale: List[List[float]],
    max_duration: float = 30.0
) -> Tuple[List[List[float]], int]:
    # Alors là, cette fonction résout le problème avec la méthode du marche-pied, mais sans afficher quoi que ce soit
    # En résumé, c'est la même chose que dans main.py mais sans les print, pour pouvoir mesurer les temps proprement
    # Pour faire simple : on optimise jusqu'à trouver la solution optimale, et on compte les itérations
    
    # Pseudo-code :
    # allocation = copie(allocation_initiale)
    # nb_iterations = 0
    # 
    # TANT QUE nb_iterations < max_iterations:
    #     Étape 1 : Rendre acyclique (casser tous les cycles de manière répétée)
    #     Étape 2 : Rendre connexe (ajouter des arêtes si besoin)
    #     Étape 3 : Calculer les potentiels
    #     Étape 4 : Calculer les coûts marginaux
    #     Étape 5 : Détecter l'arête améliorante
    #     SI pas d'arête améliorante:
    #         RETOURNER solution optimale (on a fini !)
    #     FIN SI
    #     Étape 6 : Ajouter l'arête et trouver le cycle
    #     Étape 7 : Maximiser sur le cycle
    # FIN TANT QUE
    
    allocation = [row.copy() for row in allocation_initiale]
    nb_iterations = 0
    # OPTIMISATION : Réduire le nombre max d'itérations pour les très grandes tailles
    n = len(costs)
    if n >= 10000:
        max_iterations = 50  # Limiter drastiquement pour n=10000
    elif n >= 5000:
        max_iterations = 100
    elif n >= 1000:
        max_iterations = 200
    else:
        max_iterations = 1000  # Protection contre les boucles infinies
    max_cycles_elimination = 50 if n >= 1000 else 100  # Réduire pour les grandes tailles
    debut_boucle = time.perf_counter()
    debut_global = debut_boucle
    # Pour les grandes valeurs de n, faire un garbage collection plus fréquent
    gc_frequency = 1 if n >= 1000 else 10  # GC à chaque itération pour n>=1000, sinon toutes les 10 itérations
    
    while nb_iterations < max_iterations:
        nb_iterations += 1
        
        # Protection globale : on arrête si on dépasse la durée maximale autorisée
        if time.perf_counter() - debut_global > max_duration:
            break
        
        # Protection contre les boucles trop longues (plus de 30 secondes pour une itération)
        if nb_iterations > 1:
            temps_boucle = time.perf_counter() - debut_boucle
            if temps_boucle > max_duration:
                break
        
        # Garbage collection périodique pour les grandes valeurs de n
        if n >= 1000 and nb_iterations % gc_frequency == 0:
            gc.collect()
        
        # Étape 1 : Détecter et éliminer les cycles de manière répétée
        cycles_elimines = 0
        while cycles_elimines < max_cycles_elimination:
            if time.perf_counter() - debut_global > max_duration:
                break
            try:
                result_acyclique = tester_acyclique(allocation)
                if not isinstance(result_acyclique, tuple) or len(result_acyclique) != 2:
                    raise ValueError(f"tester_acyclique a retourné un résultat inattendu: {type(result_acyclique)}, attendu: Tuple[bool, List[Tuple[int, int]]]")
                acyclique, cycle = result_acyclique
            except ValueError as e:
                print(f"  ! Erreur dans tester_acyclique: {e}", file=sys.stderr, flush=True)
                raise
            if acyclique:
                break
            
            cycles_elimines += 1
            delta = maximiser_sur_cycle(allocation, cycle, verbose=False)
            
            if delta <= 1e-9:
                # Cas particulier : delta = 0, on casse le cycle structurellement
                if cycle:
                    i, j = cycle[0]
                    allocation[i][j] = 0.0
                # Forcer la sortie après avoir cassé le cycle
                break
        
        if cycles_elimines >= max_cycles_elimination:
            # Trop de cycles, on arrête pour éviter une boucle infinie
            break
        
        # Étape 2 : Vérifier la connexité
        try:
            result_connexite = is_connected_transport(allocation)
            if not isinstance(result_connexite, tuple) or len(result_connexite) != 2:
                raise ValueError(f"is_connected_transport a retourné un résultat inattendu: {type(result_connexite)}, attendu: Tuple[bool, List]")
            est_connexe, _ = result_connexite
        except ValueError as e:
            print(f"  ! Erreur dans is_connected_transport: {e}", file=sys.stderr, flush=True)
            raise
        arêtes_ajoutées_connexité = []
        
        if not est_connexe:
            # Rendre connexe en ajoutant des arêtes de coût minimal
            arêtes_ajoutées_connexité = rendre_connexe(costs, allocation, supplies, demands, verbose=False)
            
            # Vérifier à nouveau les cycles après connexité
            cycles_elimines_apres = 0
            while cycles_elimines_apres < max_cycles_elimination:
                if time.perf_counter() - debut_global > max_duration:
                    break
                try:
                    result_acyclique = tester_acyclique(allocation)
                    if not isinstance(result_acyclique, tuple) or len(result_acyclique) != 2:
                        raise ValueError(f"tester_acyclique a retourné un résultat inattendu: {type(result_acyclique)}, attendu: Tuple[bool, List[Tuple[int, int]]]")
                    acyclique, cycle = result_acyclique
                except ValueError as e:
                    print(f"  ! Erreur dans tester_acyclique (après connexité): {e}", file=sys.stderr, flush=True)
                    raise
                if acyclique:
                    break
                
                cycles_elimines_apres += 1
                delta = maximiser_sur_cycle(allocation, cycle, verbose=False)
                
                if delta <= 1e-9:
                    if cycle:
                        i, j = cycle[0]
                        allocation[i][j] = 0.0
                    # Forcer la sortie après avoir cassé le cycle
                    break
            
            if cycles_elimines_apres >= max_cycles_elimination:
                # Trop de cycles, on arrête pour éviter une boucle infinie
                break
        
        # Étape 3 : Calculer les potentiels
        try:
            result_potentiels = calculer_potentiels(costs, allocation)
            if not isinstance(result_potentiels, tuple) or len(result_potentiels) != 2:
                raise ValueError(f"calculer_potentiels a retourné un résultat inattendu: {type(result_potentiels)}, attendu: Tuple[List[float], List[float]]")
            u, v = result_potentiels
        except ValueError as e:
            print(f"  ! Erreur dans calculer_potentiels: {e}", file=sys.stderr, flush=True)
            raise
        
        # Étape 4 & 5 : Détecter l'arête améliorante (Optimisé)
        # Utiliser la stratégie "first" pour les grands problèmes (toujours pour n >= 1000)
        strategy = "first" if len(costs) >= 1000 else ("first" if len(costs) >= 500 else "best")
        
        # On utilise la version rapide qui n'alloue pas la matrice des marginaux
        from potentiels import detecter_arete_ameliorante_rapide
        arete_ameliorante = detecter_arete_ameliorante_rapide(costs, u, v, allocation, strategy=strategy)
        
        if arete_ameliorante is None:
            # Solution optimale trouvée !
            break
        
        # Vérifier que l'arête améliorante est bien un tuple de 3 éléments
        if not isinstance(arete_ameliorante, tuple) or len(arete_ameliorante) != 3:
            raise ValueError(f"detecter_arete_ameliorante_rapide a retourné un résultat inattendu: {type(arete_ameliorante)}, attendu: Tuple[int, int, float] ou None")
        
        i_ameliorant, j_ameliorant, _ = arete_ameliorante
        
        # Étape 6 : Ajouter l'arête améliorante et trouver le cycle
        allocation[i_ameliorant][j_ameliorant] = 1.0
        cycle = trouver_cycle_avec_arete(allocation, i_ameliorant, j_ameliorant)
        
        # Étape 7 : Maximiser le transport sur le cycle
        delta = maximiser_sur_cycle(allocation, cycle, verbose=False)
        
        if delta <= 1e-9:
            # Cas particulier : delta = 0
            for i, j in arêtes_ajoutées_connexité:
                allocation[i][j] = 0.0
            allocation[i_ameliorant][j_ameliorant] = 1e-6
    
    # Garbage collection final avant de retourner (important pour N=10000)
    gc.collect()
    
    return allocation, nb_iterations


def mesurer_temps_nord_ouest(costs: List[List[float]], supplies: List[float], demands: List[float]) -> Tuple[float, float]:
    # Alors là, cette fonction mesure le temps d'exécution de l'algorithme Nord-Ouest
    # et calcule le coût de la solution trouvée
    
    # Garbage collection avant mesure pour libérer la mémoire (important pour N=10000)
    gc.collect()
    
    start_time = time.perf_counter()
    allocation = northwest_corner_method(supplies, demands)
    end_time = time.perf_counter()
    
    # Vérifier que northwest_corner_method retourne bien une allocation
    if not isinstance(allocation, list):
        raise ValueError(f"northwest_corner_method a retourné un type inattendu: {type(allocation)}, attendu: List[List[float]]")
    
    # Calculer le coût de la solution initiale
    cout_initial = compute_total_cost(costs, allocation)
    
    # Garbage collection après mesure
    gc.collect()
    
    return end_time - start_time, cout_initial


def mesurer_temps_balas_hammer(costs: List[List[float]], supplies: List[float], demands: List[float]) -> Tuple[float, float]:
    # Alors là, cette fonction mesure le temps d'exécution de l'algorithme Balas-Hammer
    # et calcule le coût de la solution trouvée
    
    # Garbage collection avant mesure pour libérer la mémoire
    gc.collect()
    
    # Déterminer une durée max adaptée à la taille
    n = len(costs)
    # Timeout plus long pour les très grandes valeurs (N=10000 peut prendre plusieurs minutes)
    max_duration = 300.0 if n >= 5000 else 60.0 if n >= 1000 else 10.0 if n >= 500 else 20.0 if n >= 200 else 30.0
    
    start_time = time.perf_counter()
    allocation = balas_hammer_method(costs, supplies, demands, verbose=False, max_duration=max_duration)
    end_time = time.perf_counter()
    
    # Vérifier que balas_hammer_method retourne bien une allocation
    if not isinstance(allocation, list):
        raise ValueError(f"balas_hammer_method a retourné un type inattendu: {type(allocation)}, attendu: List[List[float]]")
    
    # Calculer le coût de la solution initiale
    cout_initial = compute_total_cost(costs, allocation)
    
    # Garbage collection après mesure
    gc.collect()
    
    return end_time - start_time, cout_initial


def mesurer_temps_marche_pied_no(
    costs: List[List[float]],
    supplies: List[float],
    demands: List[float]
) -> Tuple[float, float]:
    # Alors là, cette fonction mesure le temps d'exécution de la méthode du marche-pied avec solution initiale Nord-Ouest
    # et calcule le coût final de la solution optimisée
    
    try:
        # Calculer la solution initiale avec Nord-Ouest
        allocation_initiale = northwest_corner_method(supplies, demands)
        
        # Déterminer une durée max adaptée à la taille
        n = len(costs)
        # Timeout plus long pour les très grandes valeurs (N=10000 peut prendre plusieurs minutes)
        max_duration = 300.0 if n >= 5000 else 60.0 if n >= 1000 else 10.0 if n >= 500 else 20.0 if n >= 200 else 30.0
        
        # Garbage collection avant mesure pour libérer la mémoire
        gc.collect()
        
        # Mesurer le temps du marche-pied avec garde de durée
        start_time = time.perf_counter()
        result = resoudre_marche_pied_silencieux(costs, supplies, demands, allocation_initiale, max_duration=max_duration)
        end_time = time.perf_counter()
        
        # Vérifier que le résultat est correct (allocation, nb_iterations)
        if not isinstance(result, tuple) or len(result) != 2:
            raise ValueError(f"resoudre_marche_pied_silencieux a retourné un résultat inattendu: {type(result)}, attendu: Tuple[List[List[float]], int]")
        
        allocation_finale, _ = result
        cout_final = compute_total_cost(costs, allocation_finale)
        
        # Garbage collection après mesure
        gc.collect()
        
        return end_time - start_time, cout_final
    except Exception as e:
        # En cas d'erreur, afficher plus de détails pour le débogage
        import traceback
        print(f"  ! Erreur détaillée dans mesurer_temps_marche_pied_no: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        raise


def mesurer_temps_marche_pied_bh(
    costs: List[List[float]],
    supplies: List[float],
    demands: List[float]
) -> Tuple[float, float]:
    # Alors là, cette fonction mesure le temps d'exécution de la méthode du marche-pied avec solution initiale Balas-Hammer
    # et calcule le coût final de la solution optimisée
    
    try:
        # Déterminer une durée max adaptée à la taille
        n = len(costs)
        # Timeout plus long pour les très grandes valeurs (N=10000 peut prendre plusieurs minutes)
        max_duration = 300.0 if n >= 5000 else 60.0 if n >= 1000 else 10.0 if n >= 500 else 20.0 if n >= 200 else 30.0
        
        # Garbage collection avant mesure pour libérer la mémoire
        gc.collect()
        
        # Calculer la solution initiale avec Balas-Hammer
        allocation_initiale = balas_hammer_method(costs, supplies, demands, verbose=False, max_duration=max_duration)
        
        # Vérifier que balas_hammer_method retourne bien une allocation (liste de listes)
        if not isinstance(allocation_initiale, list):
            raise ValueError(f"balas_hammer_method a retourné un type inattendu: {type(allocation_initiale)}, attendu: List[List[float]]")
        
        # Garbage collection après Balas-Hammer
        gc.collect()
        
        # Mesurer le temps du marche-pied avec garde de durée
        start_time = time.perf_counter()
        result = resoudre_marche_pied_silencieux(costs, supplies, demands, allocation_initiale, max_duration=max_duration)
        end_time = time.perf_counter()
        
        # Vérifier que le résultat est correct (allocation, nb_iterations)
        if not isinstance(result, tuple) or len(result) != 2:
            raise ValueError(f"resoudre_marche_pied_silencieux a retourné un résultat inattendu: {type(result)}, attendu: Tuple[List[List[float]], int]")
        
        allocation_finale, _ = result
        cout_final = compute_total_cost(costs, allocation_finale)
        
        # Garbage collection après mesure
        gc.collect()
        
        return end_time - start_time, cout_final
    except Exception as e:
        # En cas d'erreur, afficher plus de détails pour le débogage
        import traceback
        print(f"  ! Erreur détaillée dans mesurer_temps_marche_pied_bh: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        raise


def executer_une_iteration_complete(n: int, seed: int) -> Tuple[float, float, float, float, float, float, float, float]:
    # Alors là, cette fonction exécute une itération complète : génère un problème et mesure tous les temps
    # En résumé, c'est une fonction helper pour la parallélisation
    # Pour faire simple : on fait tout en une fois pour pouvoir paralléliser facilement
    
    import os
    pid = os.getpid()
    
    try:
        # Générer un problème aléatoire
        costs, supplies, demands = generer_probleme_aleatoire(n, seed=seed)

        # OPTIMISATION : Pour les grandes tailles (n >= 1000), éviter de cloner plusieurs fois
        # Chaque mesure modifie potentiellement les listes en place.
        # On clone donc les données de base pour isoler chaque mesure.
        # Pour n >= 1000, on clone seulement quand nécessaire pour économiser la mémoire
        def clones():
            return (
                [row.copy() for row in costs],
                supplies.copy(),
                demands.copy(),
            )
        
        # OPTIMISATION : Pour n >= 1000, réutiliser les clones quand possible
        # Mesurer tous les temps avec gestion d'erreur individuelle
        
        # Init NO
        try:
            c, s, d = clones()
            temps_no, cout_no = mesurer_temps_nord_ouest(c, s, d)
            del c, s, d
            gc.collect()
        except Exception as e:
            print(f"[PID {pid}] ! Erreur dans mesurer_temps_nord_ouest (n={n}, seed={seed}): {e}", file=sys.stderr, flush=True)
            temps_no = 0.0
            cout_no = 0.0
        
        # Init BH
        try:
            c, s, d = clones()
            temps_bh, cout_bh = mesurer_temps_balas_hammer(c, s, d)
            del c, s, d
            gc.collect()
        except Exception as e:
            print(f"[PID {pid}] ! Erreur dans mesurer_temps_balas_hammer (n={n}, seed={seed}): {e}", file=sys.stderr, flush=True)
            temps_bh = 0.0
            cout_bh = 0.0
        
        # MP sur NO
        try:
            c, s, d = clones()
            temps_mp_no, cout_fin_no = mesurer_temps_marche_pied_no(c, s, d)
            del c, s, d
            gc.collect()
        except Exception as e:
            print(f"[PID {pid}] ! Erreur dans mesurer_temps_marche_pied_no (n={n}, seed={seed}): {e}", file=sys.stderr, flush=True)
            temps_mp_no = 0.0
            cout_fin_no = 0.0
        
        # MP sur BH
        try:
            c, s, d = clones()
            temps_mp_bh, cout_fin_bh = mesurer_temps_marche_pied_bh(c, s, d)
            del c, s, d
            gc.collect()
        except Exception as e:
            print(f"[PID {pid}] ! Erreur dans mesurer_temps_marche_pied_bh (n={n}, seed={seed}): {e}", file=sys.stderr, flush=True)
            temps_mp_bh = 0.0
            cout_fin_bh = 0.0
        
        print(f"[PID {pid}] Terminé (n={n}, seed={seed}): NO={temps_no:.6f}, BH={temps_bh:.6f}, MP_NO={temps_mp_no:.6f}, MP_BH={temps_mp_bh:.6f}", file=sys.stderr, flush=True)
        return temps_no, temps_bh, temps_mp_no, temps_mp_bh, cout_no, cout_bh, cout_fin_no, cout_fin_bh
    except Exception as e:
        # En cas d'erreur, retourner des valeurs par défaut pour éviter de bloquer tout le processus
        print(f"[PID {pid}] ! Erreur dans l'exécution (n={n}, seed={seed}): {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


def executer_etude_complexite(
    valeurs_n: List[int] = None,
    nb_executions: int = 100,
    sauvegarder_resultats: bool = True,
    utiliser_parallele: bool = False,  # DÉSACTIVÉ PAR DÉFAUT pour respecter la contrainte "single processor"
    nb_processus: int = None,
    taille_lot: int = 10,
    pause_entre_lots: float = 0.1,
    fichier: str = 'complexite_resultats.json'
) -> Dict:
    # Alors là, cette fonction exécute toute l'étude de complexité
    # En résumé, pour chaque valeur de n, on génère 100 problèmes aléatoires et on mesure les temps
    # Pour faire simple : on veut voir comment les algorithmes se comportent selon la taille
    # 
    # OPTIMISATION : Traitement par lots avec pauses pour éviter la surchauffe du CPU
    
    if valeurs_n is None:
        valeurs_n = [10, 40, 102, 400, 1000, 4000, 10000]
    
    # OPTIMISATION : Pour n=10000, réduire le nombre d'exécutions par défaut si non spécifié
    # pour éviter que le programme ne plante
    if 10000 in valeurs_n and nb_executions > 10:
        print(f"  ! Pour n=10000, le nombre d'exécutions est limité à 10 pour éviter les problèmes de mémoire")
        print(f"  ! Utilisez le paramètre nb_executions pour modifier ce comportement")
        sys.stdout.flush()
        # Ne pas modifier nb_executions ici, mais avertir l'utilisateur
    
    # Déterminer le nombre de processus à utiliser (OPTIMISATION : laisser au moins 1-2 cœurs libres)
    nb_processus = calculer_nb_processus_optimal(nb_processus)
    
    resultats = {}
    
    # Compteurs globaux pour l'estimation du temps
    total_executions_global = sum(nb_executions for _ in valeurs_n)
    execution_globale_actuelle = 0
    temps_debut_global = time.perf_counter()
    
    print(f"\n======================================================================")
    print(f"ÉTUDE DE LA COMPLEXITÉ")
    print(f"======================================================================")
    print(f"Valeurs de n à tester : {valeurs_n}")
    print(f"Nombre d'exécutions par valeur de n : {nb_executions}")
    print(f"Total : {total_executions_global} exécutions")
    print(f"Mode parallèle : {'OUI' if utiliser_parallele else 'NON'} (utilisant {nb_processus if utiliser_parallele else 1}/{cpu_count()} processus)")
    if not utiliser_parallele:
        print(f"  ! Mode séquentiel (single processor) : conforme aux exigences du projet")
        print(f"  ! Garbage collection activé pour optimiser l'utilisation mémoire (N=10000)")
    if utiliser_parallele:
        print(f"  ! Optimisation : {max(0, cpu_count() - nb_processus)} cœur(s) laissé(s) libre(s) pour éviter la surchauffe")
        print(f"  ! Traitement par lots de {taille_lot} avec pause de {pause_entre_lots}s entre les lots")
    print(f"\n! Attention : Cette opération peut prendre beaucoup de temps !")
    print(f"======================================================================\n")
    sys.stdout.flush()
    
    for idx_n, n in enumerate(valeurs_n):
        print(f"\n>>> Traitement de n = {n} ({idx_n + 1}/{len(valeurs_n)}) <<<")
        print(f"Génération de {nb_executions} problème(s) aléatoire(s)...")
        sys.stdout.flush()
        
        temps_debut_n = time.perf_counter()
        
        print(f"  ! Démarrage du traitement pour n={n}...")
        sys.stdout.flush()
        
        theta_NO = []
        theta_BH = []
        t_NO = []
        t_BH = []
        couts_init_NO = []
        couts_init_BH = []
        couts_fin_NO = []
        couts_fin_BH = []
        
        # Pour les petites valeurs de n, utiliser le mode séquentiel pour éviter les blocages
        utiliser_parallele_effectif = utiliser_parallele
        nb_processus_effectif = nb_processus
        
        if n <= 10:
            # Pour n <= 10, utiliser le mode séquentiel pour éviter les blocages
            utiliser_parallele_effectif = False
            print(f"  ! Mode séquentiel forcé pour n={n} (petite taille)")
            sys.stdout.flush()
        elif n >= 1000:
            # Pour n >= 1000, utiliser le mode séquentiel pour éviter la saturation mémoire (N=10000 -> 800Mo par matrice !)
            # Sur Windows, multiprocessing 'spawn' copie tout, ce qui tue la RAM.
            utiliser_parallele_effectif = False
            print(f"  ! Mode séquentiel forcé pour n={n} (grande taille) pour éviter saturation mémoire")
            sys.stdout.flush()
        elif n <= 100 and nb_executions <= 5:
            # Pour les petits problèmes, utiliser moins de processus
            nb_processus_effectif = min(4, nb_processus)
        elif n <= 400 and nb_executions <= 10:
            # Pour les problèmes moyens, utiliser un nombre modéré
            nb_processus_effectif = min(8, nb_processus)
        
        # Gérer le cas où nb_executions = 1 avec parallélisation (utiliser quand même le pool)
        if utiliser_parallele_effectif:
            # Version parallélisée avec traitement par lots pour éviter la surchauffe
            # On crée une liste de seeds pour chaque exécution
            seeds = list(range(nb_executions))
            
            print(f"  ! Initialisation du pool de {nb_processus_effectif} processus (sur {nb_processus} disponibles)...")
            sys.stdout.flush()
            
            # Utiliser multiprocessing pour paralléliser les exécutions
            with Pool(processes=nb_processus_effectif) as pool:
                # Créer une fonction partielle avec n fixé
                fonction_iteration = partial(executer_une_iteration_complete, n)
                
                # OPTIMISATION : Traitement par lots avec pauses pour éviter la surchauffe
                resultats_iterations = []
                nb_lots = (nb_executions + taille_lot - 1) // taille_lot  # Arrondi supérieur
                
                print(f"  ! Traitement en {nb_lots} lot(s)...")
                sys.stdout.flush()
                
                for lot_num in range(nb_lots):
                    debut_lot = lot_num * taille_lot
                    fin_lot = min(debut_lot + taille_lot, nb_executions)
                    seeds_lot = seeds[debut_lot:fin_lot]
                    temps_debut_lot = time.perf_counter()
                    
                    print(f"  ! Démarrage du lot {lot_num + 1}/{nb_lots} ({len(seeds_lot)} exécution(s))...")
                    sys.stdout.flush()
                    
                    # Exécuter le lot en parallèle avec suivi de progression
                    # Utiliser map_async pour pouvoir surveiller la progression
                    resultat_async = pool.map_async(fonction_iteration, seeds_lot)
                    
                    # Calculer un timeout raisonnable basé sur n (plus n est grand, plus on attend)
                    # Estimation : pour n=10, ~0.1s par exécution, pour n=10000, ~300s par exécution
                    # Timeout plus court pour les petites valeurs de n
                    if n <= 10:
                        timeout_estime = 5 * len(seeds_lot)  # 5s par exécution pour n=10
                    elif n <= 100:
                        timeout_estime = 30 * len(seeds_lot)  # 30s par exécution pour n=100
                    else:
                        timeout_estime = max(60, n * n * 0.003 * len(seeds_lot))  # Timeout adaptatif
                    timeout_max = 3600  # Maximum 1 heure par lot
                    timeout_final = min(timeout_estime, timeout_max)
                    print(f"  ! Timeout configuré : {timeout_final:.0f}s pour n={n} ({len(seeds_lot)} exécution(s))")
                    sys.stdout.flush()
                    
                    # Attendre avec heartbeat toutes les 30 secondes
                    dernier_heartbeat = time.perf_counter()
                    temps_attente = 0.0
                    timeout_atteint = False
                    resultats_lot = None
                    
                    while not resultat_async.ready():
                        time.sleep(0.5)  # Vérifier toutes les 0.5 secondes
                        temps_actuel = time.perf_counter()
                        temps_attente = temps_actuel - temps_debut_lot
                        
                        # Vérifier le timeout
                        if temps_attente > timeout_final:
                            print(f"  ! Timeout atteint pour le lot {lot_num + 1}/{nb_lots} (>{timeout_final:.0f}s)")
                            print(f"  ! Tentative d'annulation des tâches...")
                            sys.stdout.flush()
                            
                            # Essayer d'annuler les tâches si possible
                            try:
                                resultat_async.cancel()
                            except:
                                pass
                            
                            # Attendre un peu pour voir si les tâches se terminent
                            time.sleep(2)
                            
                            if not resultat_async.ready():
                                print(f"  ! Les processus sont bloqués, passage au lot suivant avec valeurs par défaut...")
                                sys.stdout.flush()
                                # Remplir avec des valeurs par défaut pour ne pas bloquer
                                resultats_lot = [(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0) for _ in seeds_lot]
                                timeout_atteint = True
                                print(f"  ! Lot {lot_num + 1} ignoré à cause du timeout")
                                sys.stdout.flush()
                                break  # Sortir de la boucle d'attente
                            else:
                                # Les tâches se sont terminées entre-temps
                                print(f"  Les tâches se sont terminées après l'annonce du timeout")
                                sys.stdout.flush()
                                break
                        
                        # Heartbeat toutes les 30 secondes
                        if temps_actuel - dernier_heartbeat >= 30.0:
                            print(f"  ! Programme actif... (lot {lot_num + 1}/{nb_lots} en cours depuis {temps_attente:.1f}s)")
                            sys.stdout.flush()
                            dernier_heartbeat = temps_actuel
                    
                    # Récupérer les résultats avec un timeout raisonnable (seulement si on n'a pas déjà eu un timeout)
                    if not timeout_atteint:
                        try:
                            # Timeout plus long pour permettre aux calculs de se terminer
                            resultats_lot = resultat_async.get(timeout=300)  # 5 minutes max pour récupérer
                        except Exception as e:
                            print(f"  ! Erreur lors de la récupération des résultats du lot {lot_num + 1}: {e}")
                            sys.stdout.flush()
                            # Réessayer une fois avec un timeout plus long
                            try:
                                resultats_lot = resultat_async.get(timeout=600)  # 10 minutes
                            except Exception as e2:
                                print(f"  ! Échec définitif pour le lot {lot_num + 1}: {e2}")
                                sys.stdout.flush()
                                # Remplir avec des valeurs par défaut pour ne pas bloquer
                                resultats_lot = [(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0) for _ in seeds_lot]
                    
                    resultats_iterations.extend(resultats_lot)
                    
                    temps_fin_lot = time.perf_counter()
                    temps_lot = temps_fin_lot - temps_debut_lot
                    
                    print(f"  Lot {lot_num + 1}/{nb_lots} terminé en {temps_lot:.2f}s")
                    sys.stdout.flush()
                    
                    # Mise à jour de la progression globale
                    execution_globale_actuelle += len(seeds_lot)
                    executions_restantes_global = total_executions_global - execution_globale_actuelle
                    
                    # Calculer le temps écoulé et estimer le temps restant
                    temps_ecoule_total = time.perf_counter() - temps_debut_n
                    if fin_lot > 0:
                        temps_moyen_par_execution = temps_ecoule_total / fin_lot
                        executions_restantes_n = nb_executions - fin_lot
                        temps_restant_n = temps_moyen_par_execution * executions_restantes_n
                        
                        # Estimation pour les autres valeurs de n (approximative)
                        executions_restantes_autres_n = sum(
                            nb_executions for i, n_autre in enumerate(valeurs_n) 
                            if i > idx_n
                        )
                        temps_restant_autres_n = temps_moyen_par_execution * executions_restantes_autres_n * 1.2  # Facteur de sécurité
                        temps_restant_total = temps_restant_n + temps_restant_autres_n
                        
                        heures_restantes = int(temps_restant_total // 3600)
                        minutes_restantes = int((temps_restant_total % 3600) // 60)
                        secondes_restantes = int(temps_restant_total % 60)
                        
                        # Afficher les logs détaillés (à chaque lot)
                        progression_n = (fin_lot / nb_executions) * 100
                        progression_globale = (execution_globale_actuelle / total_executions_global) * 100
                        
                        print(f"\n  ! Progression pour n={n}: {fin_lot}/{nb_executions} ({progression_n:.1f}%)")
                        print(f"  Progression globale: {execution_globale_actuelle}/{total_executions_global} ({progression_globale:.1f}%)")
                        print(f"  Temps écoulé pour n={n}: {temps_ecoule_total:.1f}s")
                        print(f"  Temps restant estimé: {heures_restantes}h {minutes_restantes}min {secondes_restantes}s")
                        print(f"  Calculs restants: {executions_restantes_global} exécutions")
                        print(f"  Dernier lot traité en {temps_lot:.2f}s ({len(seeds_lot)} exécutions)")
                        print(f"  Lot {lot_num + 1}/{nb_lots} terminé")
                    
                    # OPTIMISATION : Garbage collection après chaque lot pour libérer la mémoire
                    # Particulièrement important pour N=10000 où les matrices sont très grandes
                    gc.collect()
                    
                    # Pause entre les lots pour permettre au CPU de se refroidir
                    if lot_num < nb_lots - 1:  # Pas de pause après le dernier lot
                        time.sleep(pause_entre_lots)
            
            # Séparer les résultats
            theta_NO = [r[0] for r in resultats_iterations]
            theta_BH = [r[1] for r in resultats_iterations]
            t_NO = [r[2] for r in resultats_iterations]
            t_BH = [r[3] for r in resultats_iterations]
            couts_init_NO = [r[4] for r in resultats_iterations]
            couts_init_BH = [r[5] for r in resultats_iterations]
            couts_fin_NO = [r[6] for r in resultats_iterations]
            couts_fin_BH = [r[7] for r in resultats_iterations]
            
            # OPTIMISATION : Garbage collection après avoir traité tous les lots
            gc.collect()
        else:
            # Version séquentielle (pour comparaison ou si parallélisation désactivée)
            print(f"  ! Mode séquentiel activé...")
            sys.stdout.flush()
            
            theta_NO = []
            theta_BH = []
            t_NO = []
            t_BH = []
            couts_init_NO = []
            couts_init_BH = []
            couts_fin_NO = []
            couts_fin_BH = []
            
            dernier_heartbeat = time.perf_counter()
            
            for execution in range(nb_executions):
                temps_debut_exec = time.perf_counter()
                
                print(f"  ! Exécution {execution + 1}/{nb_executions} en cours...")
                sys.stdout.flush()
                
                # Générer un problème aléatoire (on utilise execution comme seed pour reproductibilité)
                costs, supplies, demands = generer_probleme_aleatoire(n, seed=execution)
                
                # Mesurer theta_NO(n)
                print(f"    → Mesure θNO(n)...")
                sys.stdout.flush()
                temps_no, cout_no = mesurer_temps_nord_ouest(costs, supplies, demands)
                theta_NO.append(temps_no)
                couts_init_NO.append(cout_no)
                
                # Mesurer theta_BH(n)
                print(f"    → Mesure θBH(n)...")
                sys.stdout.flush()
                temps_bh, cout_bh = mesurer_temps_balas_hammer(costs, supplies, demands)
                theta_BH.append(temps_bh)
                couts_init_BH.append(cout_bh)
                
                # Mesurer t_NO(n)
                print(f"    → Mesure tNO(n) (marche-pied avec NO)...")
                sys.stdout.flush()
                temps_marche_pied_no, cout_fin_no = mesurer_temps_marche_pied_no(costs, supplies, demands)
                t_NO.append(temps_marche_pied_no)
                couts_fin_NO.append(cout_fin_no)
                
                # Mesurer t_BH(n)
                print(f"    → Mesure tBH(n) (marche-pied avec BH)...")
                sys.stdout.flush()
                temps_marche_pied_bh, cout_fin_bh = mesurer_temps_marche_pied_bh(costs, supplies, demands)
                t_BH.append(temps_marche_pied_bh)
                couts_fin_BH.append(cout_fin_bh)
                
                temps_fin_exec = time.perf_counter()
                temps_exec = temps_fin_exec - temps_debut_exec
                
                # OPTIMISATION : Garbage collection après chaque exécution pour libérer la mémoire
                # Particulièrement important pour N=10000 où les matrices sont très grandes
                gc.collect()
                
                # Heartbeat toutes les 30 secondes
                temps_actuel = time.perf_counter()
                # Calculer le temps écoulé depuis le début du traitement de cette valeur de n
                temps_ecoule_total = temps_actuel - temps_debut_n
                if temps_actuel - dernier_heartbeat >= 30.0:
                    print(f"  ! Programme actif... (exécution {execution + 1}/{nb_executions}, {temps_ecoule_total:.1f}s écoulées)")
                    sys.stdout.flush()
                    dernier_heartbeat = temps_actuel
        
        temps_fin_n = time.perf_counter()
        temps_total_n = temps_fin_n - temps_debut_n
        
        # Calculer les moyennes
        moyenne_theta_NO = sum(theta_NO) / len(theta_NO) if theta_NO else 0
        moyenne_theta_BH = sum(theta_BH) / len(theta_BH) if theta_BH else 0
        moyenne_t_NO = sum(t_NO) / len(t_NO) if t_NO else 0
        moyenne_t_BH = sum(t_BH) / len(t_BH) if t_BH else 0
        
        resultats[n] = {
            'theta_NO': theta_NO,
            'theta_BH': theta_BH,
            't_NO': t_NO,
            't_BH': t_BH,
            'cout_init_NO': couts_init_NO,
            'cout_init_BH': couts_init_BH,
            'cout_final_NO': couts_fin_NO,
            'cout_final_BH': couts_fin_BH,
            'theta_NO_plus_t_NO': [a+b for a,b in zip(theta_NO, t_NO)],
            'theta_BH_plus_t_BH': [a+b for a,b in zip(theta_BH, t_BH)]
        }
        
        print(f"\n  Terminé pour n={n} ({nb_executions} exécutions)")
        print(f"  Temps total: {int(temps_total_n // 3600)}h {int((temps_total_n % 3600) // 60)}min {int(temps_total_n % 60)}s ({temps_total_n:.2f}s)")
        
        # Estimation du temps restant global
        if idx_n < len(valeurs_n) - 1:
            temps_ecoule_global = time.perf_counter() - temps_debut_global
            pourcentage_fait = (execution_globale_actuelle / total_executions_global)
            if pourcentage_fait > 0:
                temps_total_estime = temps_ecoule_global / pourcentage_fait
                temps_restant_estime = temps_total_estime - temps_ecoule_global
                h_rest = int(temps_restant_estime // 3600)
                m_rest = int((temps_restant_estime % 3600) // 60)
                s_rest = int(temps_restant_estime % 60)
                print(f"  ⏳ Temps restant estimé (toutes valeurs): {h_rest}h {m_rest}min {s_rest}s")
        
        print(f"  Temps moyen θNO(n) : {moyenne_theta_NO:.6f} s")
        print(f"  Temps moyen θBH(n) : {moyenne_theta_BH:.6f} s")
        print(f"  Temps moyen tNO(n) : {moyenne_t_NO:.6f} s")
        print(f"  Temps moyen tBH(n) : {moyenne_t_BH:.6f} s")
        sys.stdout.flush()
        
        # Sauvegarder les résultats intermédiaires (on ne sait jamais, si ça plante)
        if sauvegarder_resultats:
            # Créer le dossier si nécessaire
            dossier = os.path.dirname(fichier)
            if dossier and not os.path.exists(dossier):
                os.makedirs(dossier, exist_ok=True)
            charger_resultats_complexite(resultats, fichier)
        
        # OPTIMISATION : Garbage collection après chaque valeur de n pour libérer la mémoire
        # Particulièrement important pour N=10000 où les matrices sont très grandes
        gc.collect()
    
    if sauvegarder_resultats:
        # Créer le dossier si nécessaire
        dossier = os.path.dirname(fichier)
        if dossier and not os.path.exists(dossier):
            os.makedirs(dossier, exist_ok=True)
        charger_resultats_complexite(resultats, fichier)
        print(f"\nRésultats sauvegardés dans '{fichier}'")
    
    # Dernier garbage collection avant de retourner
    gc.collect()
    
    return resultats

def charger_resultats_complexite(nouveaux_resultats: Dict = None, fichier: str = 'complexite_resultats.json') -> Dict:
    """
    Charge les résultats existants et les met à jour avec les nouveaux résultats.
    """
    resultats = {}
    if os.path.exists(fichier):
        try:
            with open(fichier, 'r') as f:
                resultats = json.load(f)
        except json.JSONDecodeError:
            pass
    
    if nouveaux_resultats:
        # Mettre à jour avec les nouveaux résultats
        resultats.update(nouveaux_resultats)
        
        # Sauvegarder
        with open(fichier, 'w') as f:
            json.dump(resultats, f, indent=4)
        
    return resultats

def tracer_nuages_de_points(resultats: Dict):
    """
    Trace les nuages de points des temps d'exécution en fonction de n.
    """
    if not MATPLOTLIB_AVAILABLE:
        print("! Matplotlib n'est pas installé. Impossible de tracer les graphiques.")
        return

    # Préparation des données
    valeurs_n = sorted([int(k) for k in resultats.keys()])
    
    plt.figure(figsize=(15, 10))
    
    # 1. Nord-Ouest vs Balas-Hammer (Initial)
    plt.subplot(2, 2, 1)
    for n in valeurs_n:
        data = resultats[str(n)]
        plt.scatter([n]*len(data['theta_NO']), data['theta_NO'], c='blue', alpha=0.5, s=10)
        plt.scatter([n]*len(data['theta_BH']), data['theta_BH'], c='red', alpha=0.5, s=10)
    plt.plot(valeurs_n, [sum(resultats[str(n)]['theta_NO'])/len(resultats[str(n)]['theta_NO']) for n in valeurs_n], 'b-', label='Nord-Ouest')
    plt.plot(valeurs_n, [sum(resultats[str(n)]['theta_BH'])/len(resultats[str(n)]['theta_BH']) for n in valeurs_n], 'r-', label='Balas-Hammer')
    plt.xlabel('Taille n')
    plt.ylabel('Temps (s)')
    plt.title('Comparaison Algorithmes Initiaux')
    plt.legend()
    plt.grid(True)
    
    # 2. Marche-Pied (NO) vs Marche-Pied (BH)
    plt.subplot(2, 2, 2)
    for n in valeurs_n:
        data = resultats[str(n)]
        plt.scatter([n]*len(data['t_NO']), data['t_NO'], c='green', alpha=0.5, s=10)
        plt.scatter([n]*len(data['t_BH']), data['t_BH'], c='orange', alpha=0.5, s=10)
    plt.plot(valeurs_n, [sum(resultats[str(n)]['t_NO'])/len(resultats[str(n)]['t_NO']) for n in valeurs_n], 'g-', label='Marche-Pied (NO)')
    plt.plot(valeurs_n, [sum(resultats[str(n)]['t_BH'])/len(resultats[str(n)]['t_BH']) for n in valeurs_n], color='orange', linestyle='-', label='Marche-Pied (BH)')
    plt.xlabel('Taille n')
    plt.ylabel('Temps (s)')
    plt.title('Comparaison Optimisation Marche-Pied')
    plt.legend()
    plt.grid(True)
    
    # 3. Total (Initial + Optimisation)
    plt.subplot(2, 2, 3)
    for n in valeurs_n:
        data = resultats[str(n)]
        total_no = data['theta_NO_plus_t_NO']
        total_bh = data['theta_BH_plus_t_BH']
        plt.scatter([n]*len(total_no), total_no, c='purple', alpha=0.5, s=10)
        plt.scatter([n]*len(total_bh), total_bh, c='brown', alpha=0.5, s=10)
    plt.plot(valeurs_n, [sum(resultats[str(n)]['theta_NO_plus_t_NO'])/len(resultats[str(n)]['theta_NO_plus_t_NO']) for n in valeurs_n], color='purple', linestyle='-', label='Total (NO)')
    plt.plot(valeurs_n, [sum(resultats[str(n)]['theta_BH_plus_t_BH'])/len(resultats[str(n)]['theta_BH_plus_t_BH']) for n in valeurs_n], color='brown', linestyle='-', label='Total (BH)')
    plt.xlabel('Taille n')
    plt.ylabel('Temps (s)')
    plt.title('Temps Total de Résolution')
    plt.legend()
    plt.grid(True)
    
    # 4. Ratio Total NO / Total BH
    plt.subplot(2, 2, 4)
    max_ratios = []
    for n in valeurs_n:
        data = resultats[str(n)]
        total_no = data['theta_NO_plus_t_NO']
        total_bh = data['theta_BH_plus_t_BH']
        # Calculer le ratio pour chaque exécution
        # Eviter la division par zéro (ajouter epsilon)
        ratios = [(no + 1e-9) / (bh + 1e-9) for no, bh in zip(total_no, total_bh)]
        plt.scatter([n]*len(ratios), ratios, c='magenta', alpha=0.5, s=10)
        max_ratios.append(max(ratios) if ratios else 0)
    
    # Tracer la courbe du max (enveloppe supérieure)
    plt.plot(valeurs_n, max_ratios, 'k--', linewidth=2, label='Max Ratio')
    plt.xlabel('Taille n')
    plt.ylabel('Ratio NO/BH')
    plt.title('Ratio (tNO + θNO) / (tBH + θBH)')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()

def determiner_complexite_pire_cas(resultats: Dict):
    """
    Analyse la complexité dans le pire des cas en traçant les courbes max.
    """
    if not MATPLOTLIB_AVAILABLE:
        print("! Matplotlib n'est pas installé. Impossible de tracer les graphiques.")
        return

    valeurs_n = sorted([int(k) for k in resultats.keys()])
    
    # Récupérer les maximums
    max_no = [max(resultats[str(n)]['theta_NO']) for n in valeurs_n]
    max_bh = [max(resultats[str(n)]['theta_BH']) for n in valeurs_n]
    max_mp_no = [max(resultats[str(n)]['t_NO']) for n in valeurs_n]
    max_mp_bh = [max(resultats[str(n)]['t_BH']) for n in valeurs_n]
    max_total_no = [max(resultats[str(n)]['theta_NO_plus_t_NO']) for n in valeurs_n]
    max_total_bh = [max(resultats[str(n)]['theta_BH_plus_t_BH']) for n in valeurs_n]
    
    plt.figure(figsize=(15, 10))
    
    # Analyse NO (théorique O(nm) -> O(n^2))
    plt.subplot(2, 3, 1)
    plt.plot(valeurs_n, max_no, 'bo-', label='Max NO')
    # Courbe théorique ajustée (sommaire)
    if max_no[-1] > 0:
        scale = max_no[-1] / (valeurs_n[-1]**2)
        plt.plot(valeurs_n, [scale * n**2 for n in valeurs_n], 'k--', label=f'O(n^2)')
    plt.title('Pire Cas : Init Nord-Ouest')
    plt.legend()
    plt.grid(True)
    
    # Analyse BH (théorique plus complexe, souvent O(n^3) ou O(n^4))
    plt.subplot(2, 3, 2)
    plt.plot(valeurs_n, max_bh, 'ro-', label='Max BH')
    if max_bh[-1] > 0:
        scale = max_bh[-1] / (valeurs_n[-1]**3)
        plt.plot(valeurs_n, [scale * n**3 for n in valeurs_n], 'k--', label=f'O(n^3)')
    plt.title('Pire Cas : Init Balas-Hammer')
    plt.legend()
    plt.grid(True)
    
    # Analyse Marche-Pied (NO)
    plt.subplot(2, 3, 3)
    plt.plot(valeurs_n, max_mp_no, 'go-', label='Max MP(NO)')
    plt.title('Pire Cas : MP (sur NO)')
    plt.legend()
    plt.grid(True)

    # Analyse Marche-Pied (BH)
    plt.subplot(2, 3, 4)
    plt.plot(valeurs_n, max_mp_bh, 'yo-', label='Max MP(BH)')
    plt.title('Pire Cas : MP (sur BH)')
    plt.legend()
    plt.grid(True)

    # Analyse Total NO
    plt.subplot(2, 3, 5)
    plt.plot(valeurs_n, max_total_no, 'mo-', label='Max Total(NO)')
    plt.title('Pire Cas : Total (NO)')
    plt.legend()
    plt.grid(True)

    # Analyse Total BH
    plt.subplot(2, 3, 6)
    plt.plot(valeurs_n, max_total_bh, 'co-', label='Max Total(BH)')
    plt.title('Pire Cas : Total (BH)')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()

def comparer_algorithmes(resultats: Dict):
    """
    Affiche des graphiques comparatifs (bar charts) des temps moyens.
    """
    if not MATPLOTLIB_AVAILABLE:
        print("! Matplotlib n'est pas installé. Impossible de tracer les graphiques.")
        return

    valeurs_n = sorted([int(k) for k in resultats.keys()])
    
    avg_no = [sum(resultats[str(n)]['theta_NO'])/len(resultats[str(n)]['theta_NO']) for n in valeurs_n]
    avg_bh = [sum(resultats[str(n)]['theta_BH'])/len(resultats[str(n)]['theta_BH']) for n in valeurs_n]
    avg_total_no = [sum(resultats[str(n)]['theta_NO_plus_t_NO'])/len(resultats[str(n)]['theta_NO_plus_t_NO']) for n in valeurs_n]
    avg_total_bh = [sum(resultats[str(n)]['theta_BH_plus_t_BH'])/len(resultats[str(n)]['theta_BH_plus_t_BH']) for n in valeurs_n]
    
    plt.figure(figsize=(12, 6))
    
    # Comparaison Temps Initial
    plt.subplot(1, 2, 1)
    x = range(len(valeurs_n))
    width = 0.35
    plt.bar([i - width/2 for i in x], avg_no, width, label='Nord-Ouest', color='blue')
    plt.bar([i + width/2 for i in x], avg_bh, width, label='Balas-Hammer', color='red')
    plt.xticks(x, valeurs_n)
    plt.xlabel('Taille n')
    plt.ylabel('Temps moyen (s)')
    plt.title('Comparaison Solutions Initiales')
    plt.legend()
    
    # Comparaison Temps Total
    plt.subplot(1, 2, 2)
    plt.bar([i - width/2 for i in x], avg_total_no, width, label='Total (NO)', color='purple')
    plt.bar([i + width/2 for i in x], avg_total_bh, width, label='Total (BH)', color='brown')
    plt.xticks(x, valeurs_n)
    plt.xlabel('Taille n')
    plt.ylabel('Temps moyen (s)')
    plt.title('Comparaison Temps Total de Résolution')
    plt.legend()
    
    plt.tight_layout()
    plt.show()


def calculer_statistiques(liste_valeurs: List[float]) -> Dict[str, float]:
    """
    Calcule les statistiques d'une liste de valeurs.
    """
    if not liste_valeurs or len(liste_valeurs) == 0:
        return {
            'moyenne': 0.0,
            'mediane': 0.0,
            'min': 0.0,
            'max': 0.0,
            'ecart_type': 0.0,
            'nb_valeurs': 0
        }
    
    liste_triee = sorted(liste_valeurs)
    nb = len(liste_valeurs)
    moyenne = sum(liste_valeurs) / nb
    
    # Médiane
    if nb % 2 == 0:
        mediane = (liste_triee[nb // 2 - 1] + liste_triee[nb // 2]) / 2
    else:
        mediane = liste_triee[nb // 2]
    
    # Écart-type
    variance = sum((x - moyenne) ** 2 for x in liste_valeurs) / nb
    ecart_type = variance ** 0.5
    
    return {
        'moyenne': moyenne,
        'mediane': mediane,
        'min': min(liste_valeurs),
        'max': max(liste_valeurs),
        'ecart_type': ecart_type,
        'nb_valeurs': nb
    }


def analyser_tous_les_resultats(dossier: str = "complexity"):
    """
    Analyse tous les fichiers JSON de résultats dans le dossier complexity
    et affiche des visualisations matplotlib avec tableaux comparatifs et graphiques.
    """
    import glob
    
    if not MATPLOTLIB_AVAILABLE:
        print("! Matplotlib n'est pas installé. Impossible de créer les visualisations.")
        return
    
    print("\n" + "=" * 100)
    print(" " * 30 + "ANALYSE COMPLÈTE DES RÉSULTATS DE COMPLEXITÉ")
    print("=" * 100)
    
    # Créer le dossier s'il n'existe pas
    os.makedirs(dossier, exist_ok=True)
    
    # Trouver tous les fichiers JSON
    pattern = os.path.join(dossier, "*.json")
    fichiers_json = glob.glob(pattern)
    
    if not fichiers_json:
        print(f"\n! Aucun fichier JSON trouvé dans le dossier '{dossier}'")
        print("   Exécutez d'abord l'option 3 pour générer des résultats.")
        return
    
    # Trier les fichiers par nom
    fichiers_json_tries = sorted(fichiers_json)
    
    print(f"\n{len(fichiers_json_tries)} fichier(s) JSON trouvé(s)")
    print("\nFichiers analysés :")
    for fichier in fichiers_json_tries:
        print(f"  - {os.path.basename(fichier)}")
    
    # Charger tous les résultats
    tous_les_resultats = {}
    for fichier in fichiers_json_tries:
        try:
            resultats = charger_resultats_complexite(fichier=fichier)
            nom_fichier = os.path.basename(fichier)
            tous_les_resultats[nom_fichier] = resultats
        except Exception as e:
            print(f"\n! Erreur lors du chargement de {fichier}: {e}")
            continue
    
    if not tous_les_resultats:
        print("\n! Aucun résultat valide chargé.")
        return
    
    # Extraire toutes les valeurs de n présentes
    toutes_les_valeurs_n = set()
    for resultats in tous_les_resultats.values():
        toutes_les_valeurs_n.update(int(k) for k in resultats.keys() if k.isdigit())
    
    valeurs_n_triees = sorted(toutes_les_valeurs_n)
    
    # Métriques à analyser
    metriques = {
        'theta_NO': 'θNO',
        'theta_BH': 'θBH',
        't_NO': 'tNO',
        't_BH': 'tBH',
        'theta_NO_plus_t_NO': 'Total NO',
        'theta_BH_plus_t_BH': 'Total BH'
    }
    
    # Agréger toutes les données par valeur de n pour le résumé global
    resume_global = {}
    for n in valeurs_n_triees:
        resume_global[n] = {
            'theta_NO': [],
            'theta_BH': [],
            't_NO': [],
            't_BH': [],
            'theta_NO_plus_t_NO': [],
            'theta_BH_plus_t_BH': [],
            'cout_init_NO': [],
            'cout_init_BH': [],
            'cout_final_NO': [],
            'cout_final_BH': []
        }
        
        for resultats in tous_les_resultats.values():
            if str(n) in resultats:
                data = resultats[str(n)]
                for cle in resume_global[n].keys():
                    if cle in data:
                        resume_global[n][cle].extend(data[cle])
    
    # ========== VISUALISATION 1 : Tableaux comparatifs pour chaque n ==========
    print("\nGénération des tableaux comparatifs...")
    
    for n in valeurs_n_triees:
        print("\n" + "=" * 100)
        print(f" ANALYSE POUR n = {n}")
        print("=" * 100)
        
        # Tableau principal : une ligne par fichier, une colonne par métrique
        print("\n" + "-" * 100)
        print(f"{'Fichier':<40} | {'θNO (moy)':<12} | {'θBH (moy)':<12} | {'tNO (moy)':<12} | {'tBH (moy)':<12} | {'Total NO':<12} | {'Total BH':<12}")
        print("-" * 100)
        
        for nom_fichier, resultats in sorted(tous_les_resultats.items()):
            if str(n) not in resultats:
                continue
            
            data = resultats[str(n)]
            ligne = f"{nom_fichier:<40} | "
            
            for cle_metrique in ['theta_NO', 'theta_BH', 't_NO', 't_BH', 'theta_NO_plus_t_NO', 'theta_BH_plus_t_BH']:
                if cle_metrique in data and len(data[cle_metrique]) > 0:
                    moyenne = sum(data[cle_metrique]) / len(data[cle_metrique])
                    ligne += f"{moyenne:>10.6f} | "
                else:
                    ligne += f"{'N/A':>12} | "
            
            print(ligne)
        
        print("-" * 100)
        
        # Tableau détaillé avec statistiques pour chaque métrique
        print(f"\n{'─' * 100}")
        print(f" STATISTIQUES DÉTAILLÉES POUR n = {n}")
        print(f"{'─' * 100}\n")
        
        for cle_metrique, nom_metrique in metriques.items():
            print(f"\n{nom_metrique} ({cle_metrique}):")
            print("-" * 100)
            print(f"{'Fichier':<40} | {'Moyenne':<12} | {'Médiane':<12} | {'Min':<12} | {'Max':<12} | {'Écart-type':<12} | {'Nb':<6}")
            print("-" * 100)
            
            for nom_fichier, resultats in sorted(tous_les_resultats.items()):
                if str(n) not in resultats:
                    continue
                
                data = resultats[str(n)]
                if cle_metrique in data and len(data[cle_metrique]) > 0:
                    stats = calculer_statistiques(data[cle_metrique])
                    print(f"{nom_fichier:<40} | "
                          f"{stats['moyenne']:>10.6f} | "
                          f"{stats['mediane']:>10.6f} | "
                          f"{stats['min']:>10.6f} | "
                          f"{stats['max']:>10.6f} | "
                          f"{stats['ecart_type']:>10.6f} | "
                          f"{stats['nb_valeurs']:>6}")
                else:
                    print(f"{nom_fichier:<40} | {'N/A':<12} | {'N/A':<12} | {'N/A':<12} | {'N/A':<12} | {'N/A':<12} | {'0':>6}")
            
            print("-" * 100)
    
    # ========== VISUALISATION 5 : Tableau récapitulatif global ==========
    print("\nGénération du tableau récapitulatif global...")
    
    fig, ax = plt.subplots(figsize=(16, max(6, len(valeurs_n_triees) * 0.6 + 2)))
    ax.axis('tight')
    ax.axis('off')
    
    headers_recap = ['Valeur n', 'θNO moyen', 'θBH moyen', 'tNO moyen', 'tBH moyen', 'Total NO', 'Total BH', 'Ratio BH/NO']
    table_data_recap = []
    
    for n in valeurs_n_triees:
        data = resume_global[n]
        
        theta_NO_moy = sum(data['theta_NO']) / len(data['theta_NO']) if data['theta_NO'] else 0
        theta_BH_moy = sum(data['theta_BH']) / len(data['theta_BH']) if data['theta_BH'] else 0
        t_NO_moy = sum(data['t_NO']) / len(data['t_NO']) if data['t_NO'] else 0
        t_BH_moy = sum(data['t_BH']) / len(data['t_BH']) if data['t_BH'] else 0
        total_NO = sum(data['theta_NO_plus_t_NO']) / len(data['theta_NO_plus_t_NO']) if data['theta_NO_plus_t_NO'] else 0
        total_BH = sum(data['theta_BH_plus_t_BH']) / len(data['theta_BH_plus_t_BH']) if data['theta_BH_plus_t_BH'] else 0
        ratio_total = (theta_BH_moy + t_BH_moy) / (theta_NO_moy + t_NO_moy) if (theta_NO_moy + t_NO_moy) > 0 else 0
        
        table_data_recap.append([
            str(n),
            f"{theta_NO_moy:.6f}",
            f"{theta_BH_moy:.6f}",
            f"{t_NO_moy:.6f}",
            f"{t_BH_moy:.6f}",
            f"{total_NO:.6f}",
            f"{total_BH:.6f}",
            f"{ratio_total:.4f}x"
        ])
    
    if table_data_recap:
        table_recap = ax.table(cellText=table_data_recap, colLabels=headers_recap, 
                                cellLoc='center', loc='center')
        table_recap.auto_set_font_size(False)
        table_recap.set_fontsize(10)
        table_recap.scale(1, 2)
        
        # Style
        for i in range(len(headers_recap)):
            table_recap[(0, i)].set_facecolor('#9C27B0')
            table_recap[(0, i)].set_text_props(weight='bold', color='white')
        
        # Colorer selon le ratio
        for i in range(1, len(table_data_recap) + 1):
            ratio_str = table_data_recap[i-1][7]
            try:
                ratio_val = float(ratio_str.replace('x', ''))
                if ratio_val < 1.0:
                    couleur = '#c8e6c9'  # Vert clair : BH plus rapide
                elif ratio_val < 1.5:
                    couleur = '#fff9c4'  # Jaune clair : proche
                else:
                    couleur = '#ffcdd2'  # Rouge clair : BH plus lent
            except:
                couleur = 'white'
            
            for j in range(len(headers_recap)):
                table_recap[(i, j)].set_facecolor(couleur)
        
        plt.title('Résumé Global - Comparaison des Algorithmes (Temps)', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.show()

    # ========== NOUVELLE VISUALISATION : Comparaison de la QUALITÉ (Coûts) ==========
    print("\nGénération du tableau comparatif de qualité (Coûts)...")

    fig2, ax2 = plt.subplots(figsize=(16, max(6, len(valeurs_n_triees) * 0.6 + 2)))
    ax2.axis('tight')
    ax2.axis('off')

    headers_quality = ['Valeur n', 'Coût Init NO', 'Coût Init BH', 'Coût Final NO', 'Coût Final BH', 'Gain BH Init', 'Gain BH Final']
    table_data_quality = []

    for n in valeurs_n_triees:
        data = resume_global[n]
        
        # Vérifier si les données de coût sont disponibles
        if not data['cout_init_NO'] or not data['cout_init_BH']:
            table_data_quality.append([str(n), "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])
            continue

        c_init_no = sum(data['cout_init_NO']) / len(data['cout_init_NO'])
        c_init_bh = sum(data['cout_init_BH']) / len(data['cout_init_BH'])
        c_fin_no = sum(data['cout_final_NO']) / len(data['cout_final_NO'])
        c_fin_bh = sum(data['cout_final_BH']) / len(data['cout_final_BH'])
        
        gain_init = ((c_init_no - c_init_bh) / c_init_no * 100) if c_init_no > 0 else 0
        gain_final = ((c_fin_no - c_fin_bh) / c_fin_no * 100) if c_fin_no > 0 else 0

        table_data_quality.append([
            str(n),
            f"{c_init_no:.2f}",
            f"{c_init_bh:.2f}",
            f"{c_fin_no:.2f}",
            f"{c_fin_bh:.2f}",
            f"{gain_init:.2f}%",
            f"{gain_final:.2f}%"
        ])

    if table_data_quality:
        table_quality = ax2.table(cellText=table_data_quality, colLabels=headers_quality,
                                cellLoc='center', loc='center')
        table_quality.auto_set_font_size(False)
        table_quality.set_fontsize(10)
        table_quality.scale(1, 2)

        # Style Header
        for i in range(len(headers_quality)):
            table_quality[(0, i)].set_facecolor('#2196F3') # Bleu
            table_quality[(0, i)].set_text_props(weight='bold', color='white')

        # Colorer selon le gain
        for i in range(1, len(table_data_quality) + 1):
            try:
                gain_val = float(table_data_quality[i-1][5].replace('%', ''))
                if gain_val > 0:
                    couleur = '#c8e6c9'  # Vert : BH meilleur
                elif gain_val < 0:
                    couleur = '#ffcdd2'  # Rouge : NO meilleur (rare)
                else:
                    couleur = 'white'
            except:
                couleur = 'white'

            for j in range(len(headers_quality)):
                table_quality[(i, j)].set_facecolor(couleur)

        plt.title('Résumé Global - Comparaison de la Qualité (Coûts Moyens)', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.show()

    print("\n" + "=" * 100)
    print("Analyse terminée ! Toutes les visualisations ont été générées.")
    print("=" * 100)
