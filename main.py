# Alors là, c'est le fichier principal qui résout les problèmes de transport
# Pour faire simple : on lit un problème, on trouve une solution initiale, puis on optimise jusqu'à ce que ça marche (ou pas, si si ça va marcher, je vous jure)

import sys
import os
import glob
from io import StringIO
from typing import Optional

from transport_problem import (
    read_transport_problem,
    northwest_corner_method,
    balas_hammer_method,
    compute_total_cost
)
from marche_pied import rendre_connexe, trouver_cycle_avec_arete
from cyclique import tester_acyclique, maximiser_sur_cycle
from connexite import is_connected_transport, print_components
from potentiels import (
    calculer_potentiels,
    calculer_couts_potentiels,
    calculer_couts_marginaux,
    detecter_arete_ameliorante
)
from affichage import (
    print_cost_matrix,
    print_transport_matrix,
    print_potentials,
    print_potential_costs,
    print_marginal_costs
)
from complexite import (
    executer_etude_complexite,
    charger_resultats_complexite,
    tracer_nuages_de_points,
    determiner_complexite_pire_cas,
    comparer_algorithmes,
    analyser_tous_les_resultats
)


def generer_labels(n: int, m: int):
    # Bon alors, on crée des noms sympas pour les fournisseurs (P1, P2...) et clients (C1, C2...)
    # En clair, on fait juste des strings avec des numéros
    row_labels = [f"P{i+1}" for i in range(n)]
    col_labels = [f"C{j+1}" for j in range(m)]
    return row_labels, col_labels


class TeeOutput:
    # En fait, cette classe permet d'écrire dans plusieurs endroits en même temps
    # Bref, on écrit dans tous les fichiers d'un coup, comme un copier-coller automatique
    def __init__(self, *files):
        self.files = files
    
    def write(self, obj):
        # On écrit partout, histoire de ne rien perdre
        for f in self.files:
            f.write(obj)
            f.flush()
    
    def flush(self):
        # On force l'écriture partout, au cas où
        for f in self.files:
            f.flush()


def resoudre_un_probleme(
    num_probleme: int,
    methode: str,
    capture_output: bool = False,
    output_buffer: Optional[StringIO] = None
) -> Optional[str]:
    # Cette fonction résout un problème de transport de A à Z
    # En résumé : on lit le fichier, on trouve une solution initiale, puis on optimise jusqu'à ce que ça marche (ou qu'on abandonne)
    
    # Pseudo-code :
    # 1. Lire le fichier du problème
    # 2. Afficher le tableau de contraintes (les coûts, provisions, commandes)
    # 3. Choisir l'algo initial (Nord-Ouest ou Balas-Hammer) et l'exécuter
    # 4. Boucle d'optimisation :
    #    - Vérifier qu'il n'y a pas de cycles (sinon on les casse)
    #    - Vérifier la connexité (sinon on ajoute des arêtes)
    #    - Calculer les potentiels
    #    - Calculer les coûts marginaux
    #    - Si coût marginal négatif trouvé : ajouter l'arête et optimiser sur le cycle
    #    - Sinon : solution optimale trouvée !
    # 5. Afficher la solution finale
    
    # Pour faire simple, on capture la sortie si on veut sauvegarder les traces
    original_stdout = sys.stdout
    if capture_output and output_buffer:
        sys.stdout = TeeOutput(original_stdout, output_buffer)
    
    try:
        # Lire le fichier du problème (c'est juste un fichier texte avec des nombres, rien de compliqué ^^)
        nom_fichier = f"test/probleme{num_probleme}.txt"
        costs, supplies, demands = read_transport_problem(nom_fichier)
        
        n = len(supplies)
        m = len(demands)
        row_labels, col_labels = generer_labels(n, m)
        
        # Afficher le tableau de contraintes (pour voir ce qu'on a comme problème)
        print("\n" + "=" * 70)
        print("TABLEAU DE CONTRAINTES")
        print("=" * 70)
        print_cost_matrix(costs, row_labels, col_labels)
        print()
        print(f"Provisions : {supplies}")
        print(f"Commandes  : {demands}")
        print(f"Total provisions : {sum(supplies):.2f}")
        print(f"Total commandes  : {sum(demands):.2f}")
        
        # Choisir et exécuter l'algorithme initial (on a deux choix : Nord-Ouest ou Balas-Hammer)
        if methode == 'NO':
            methode_nom = "Nord-Ouest"
            print("\n" + "=" * 70)
            print(">>> ALGORITHME DU COIN NORD-OUEST <<<")
            print("=" * 70)
            allocation_initiale = northwest_corner_method(supplies, demands)
        elif methode == 'BH':
            methode_nom = "Balas-Hammer"
            print("\n" + "=" * 70)
            print(">>> ALGORITHME DE BALAS-HAMMER <<<")
            print("=" * 70)
            allocation_initiale = balas_hammer_method(costs, supplies, demands, verbose=True)
        else:
            raise ValueError(f"Méthode inconnue : {methode}")
        
        # Afficher la proposition initiale (pour voir ce qu'on a trouvé)
        print("\n>>> Proposition de transport initiale <<<")
        print_transport_matrix(allocation_initiale, row_labels, col_labels)
        print()
        
        cout_initial = compute_total_cost(costs, allocation_initiale)
        print(f"Coût total initial : {cout_initial:.2f}")
        print()
        
        # Dérouler la méthode du marche-pied avec potentiel
        print("=" * 70)
        print(">>> MÉTHODE DU MARCHE-PIED AVEC POTENTIEL <<<")
        print("=" * 70)
        
        allocation = [row.copy() for row in allocation_initiale]
        nb_iterations = 0
        max_iterations = 1000  # Protection contre les boucles infinies (parce que ça arrive, crois-moi, j'ai vu des choses)
        
        while nb_iterations < max_iterations:
            nb_iterations += 1
            
            print(f"\n{'=' * 70}")
            print(f"ITÉRATION {nb_iterations}")
            print('=' * 70)
            
            # Affichage de la proposition de transport actuelle
            print("\n>>> Proposition de transport actuelle <<<")
            print_transport_matrix(allocation, row_labels, col_labels)
            cout_actuel = compute_total_cost(costs, allocation)
            print(f"\nCoût total actuel : {cout_actuel:.2f}")
            
            # Détecter et éliminer les cycles de manière répétée (on casse tous les cycles qu'on trouve, c'est notre spécialité)
            cycles_detectes = 0
            while True:
                acyclique, cycle = tester_acyclique(allocation)
                if acyclique:
                    break
                
                cycles_detectes += 1
                print(f"\n⚠ Cycle détecté : {cycle}")
                delta = maximiser_sur_cycle(allocation, cycle, verbose=True)
                print(f"  Maximisation effectuée avec delta = {delta:.6f}")
                
                if delta <= 1e-9:
                    print("  ⚠ Delta = 0 : cycle éliminé structurellement")
                    if cycle:
                        i, j = cycle[0]
                        allocation[i][j] = 0.0
            
            if cycles_detectes > 0:
                print(f"\n✓ Proposition rendue acyclique ({cycles_detectes} cycle(s) éliminé(s))")
            
            # Test de connexité (on vérifie que tout est bien connecté, sinon c'est la galère)
            est_connexe, composantes = is_connected_transport(allocation)
            arêtes_ajoutées_connexité = []
            
            if not est_connexe:
                print("\n⚠ Proposition non connexe") #le saviez-vous ? on fait un ⚠ avec 26A0 et alt + X
                print("Sous-graphes connexes :")
                print_components(composantes)
                print("Ajout d'arêtes classées par coûts croissants pour rendre connexe...")
                arêtes_ajoutées_connexité = rendre_connexe(costs, allocation, supplies, demands, verbose=True)
                print("✓ Proposition rendue connexe")
                if arêtes_ajoutées_connexité:
                    print(f"  Total arêtes ajoutées : {len(arêtes_ajoutées_connexité)}")
                    print(f"  Arêtes : {[(i+1, j+1) for i, j in arêtes_ajoutées_connexité]}")
                
                # Vérifier à nouveau les cycles après connexité (parce que parfois, ajouter des arêtes crée des cycles, c'est la vie, on s'y fait)
                cycles_apres_connexite = 0
                while True:
                    acyclique, cycle = tester_acyclique(allocation)
                    if acyclique:
                        break
                    
                    cycles_apres_connexite += 1
                    if cycles_apres_connexite == 1:
                        print("\n⚠ Cycle(s) détecté(s) après ajout d'arêtes pour la connexité")
                    print(f"  Cycle détecté : {cycle}")
                    delta = maximiser_sur_cycle(allocation, cycle, verbose=True)
                    print(f"  Maximisation effectuée avec delta = {delta:.6f}")
                    
                    if delta <= 1e-9:
                        print("  ⚠ Delta = 0 : cycle éliminé structurellement")
                        if cycle:
                            i, j = cycle[0]
                            allocation[i][j] = 0.0
                
                if cycles_apres_connexite > 0:
                    print(f"\n✓ Proposition rendue acyclique après connexité ({cycles_apres_connexite} cycle(s) éliminé(s))")
            
            # Calcul et affichage des potentiels (on calcule les potentiels u et v)
            u, v = calculer_potentiels(costs, allocation)
            print("\n>>> Potentiels par sommet <<<")
            print_potentials(u, v, row_labels, col_labels)
            
            # Affichage des tables (coûts potentiels et marginaux, pour voir où on peut améliorer, histoire de progresser)
            couts_potentiels = calculer_couts_potentiels(u, v)
            print("\n>>> Table des coûts potentiels <<<")
            print_potential_costs(couts_potentiels, row_labels, col_labels)
            
            marginals = calculer_couts_marginaux(costs, u, v)
            print("\n>>> Table des coûts marginaux <<<")
            print_marginal_costs(marginals, row_labels, col_labels)
            
            # Détecter l'arête améliorante (on cherche une arête qui peut améliorer le coût)
            arete_ameliorante = detecter_arete_ameliorante(marginals, allocation)
            
            if arete_ameliorante is None:
                # Solution optimale trouvée !
                print("\n✓ Solution optimale trouvée !")
                print("  Tous les coûts marginaux sont >= 0")
                break
            
            i_ameliorant, j_ameliorant, cout_marginal = arete_ameliorante
            print(f"\n>>> Arête améliorante détectée <<<")
            print(f"  Case : ({i_ameliorant+1}, {j_ameliorant+1}) = {row_labels[i_ameliorant]} -> {col_labels[j_ameliorant]}")
            print(f"  Coût marginal : {cout_marginal:.6f}")
            
            # Ajouter l'arête et maximiser sur le cycle (on ajoute l'arête et on optimise le flux sur le cycle créé, c'est parti !)
            allocation[i_ameliorant][j_ameliorant] = 1.0
            cycle = trouver_cycle_avec_arete(allocation, i_ameliorant, j_ameliorant)
            print(f"  Cycle formé : {cycle}")
            
            delta = maximiser_sur_cycle(allocation, cycle, verbose=True)
            print(f"  Maximisation effectuée avec delta = {delta:.6f}")
            
            if delta <= 1e-9:
                # Cas particulier : delta = 0 (on garde l'arête améliorante et on enlève les arêtes de connexité)
                print("\n⚠ Delta = 0 : cas particulier détecté")
                print("  On conserve l'arête améliorante et on enlève les arêtes ajoutées lors du test de connexité")
                for i, j in arêtes_ajoutées_connexité:
                    print(f"  Suppression de l'arête ({i+1}, {j+1}) ajoutée pour la connexité")
                    allocation[i][j] = 0.0
                allocation[i_ameliorant][j_ameliorant] = 1e-6
                print("  L'arête améliorante est conservée avec valeur epsilon")
        
        if nb_iterations >= max_iterations:
            print("\n⚠ Nombre maximum d'itérations atteint")
        
        # Afficher la solution optimale
        print("\n" + "=" * 70)
        print(">>> SOLUTION OPTIMALE FINALE <<<")
        print("=" * 70)
        print("\nProposition de transport optimale :")
        print_transport_matrix(allocation, row_labels, col_labels)
        print()
        
        cout_final = compute_total_cost(costs, allocation)
        print(f"Coût total optimal : {cout_final:.2f}")
        print(f"Coût initial ({methode_nom}) : {cout_initial:.2f}")
        print(f"Amélioration : {cout_initial - cout_final:.2f} ({((cout_initial - cout_final) / cout_initial * 100):.2f}%)")
        print(f"Nombre d'itérations : {nb_iterations}")
        
        # Retourner le contenu capturé si demandé (pour sauvegarder les traces, histoire de garder une trace, justement)
        if capture_output and output_buffer:
            return output_buffer.getvalue()
        return None
        
    except Exception as e:
        error_msg = f"Erreur lors de la résolution du problème {num_probleme} avec {methode}: {e}\n"
        if capture_output and output_buffer:
            output_buffer.write(error_msg)
            return output_buffer.getvalue()
        else:
            print(error_msg)
            raise
    finally:
        if capture_output:
            sys.stdout = original_stdout


def generer_toutes_les_traces():
    # Alors là, cette fonction génère toutes les traces d'exécution pour les 12 problèmes avec les 2 algorithmes
    # En clair, on résout chaque problème avec chaque méthode et on sauvegarde tout, c'est un peu répétitif mais bon
    
    # Pseudo-code :
    # POUR chaque problème de 1 à 12:
    #   POUR chaque méthode (NO, BH):
    #       Résoudre le problème
    #       Sauvegarder la trace dans un fichier
    #   FIN POUR
    # FIN POUR
    
    # Configuration fixe (c'est pour le nom des fichiers, histoire d'être organisé)
    groupe = "NEW2"
    equipe = "3"
    
    # Créer le répertoire traces s'il n'existe pas (parce que sinon ça plante, et personne n'aime ça)
    os.makedirs("traces", exist_ok=True)
    
    print("\n" + "=" * 70)
    print("GÉNÉRATION DE TOUTES LES TRACES D'EXÉCUTION")
    print("=" * 70)
    print(f"Groupe : {groupe}")
    print(f"Équipe : {equipe}")
    print(f"Répertoire de sortie : traces/")
    print("\nGénération en cours...")
    
    total = 24  # 12 problèmes × 2 algorithmes (ça fait 24 fichiers, c'est mathématique)
    compteur = 0
    
    for num_probleme in range(1, 13):
        for methode in ['NO', 'BH']:
            compteur += 1
            methode_nom = "Nord-Ouest" if methode == 'NO' else "Balas-Hammer"
            methode_abrev = "no" if methode == 'NO' else "bh"
            
            # Nom du fichier de trace (format : NEW2-3-trace5-no.txt, on est bien groupe 3 rassurez moi ?!)
            nom_fichier = f"{groupe}-{equipe}-trace{num_probleme}-{methode_abrev}.txt"
            chemin_fichier = os.path.join("traces", nom_fichier)
            
            print(f"\n[{compteur}/{total}] Problème {num_probleme} - {methode_nom} -> {nom_fichier}")
            
            # Capturer la sortie (on capture tout ce qui est affiché, comme un enregistreur)
            output_buffer = StringIO()
            try:
                resoudre_un_probleme(
                    num_probleme,
                    methode,
                    capture_output=True,
                    output_buffer=output_buffer
                )
                
                # Sauvegarder la trace (on écrit tout dans un fichier, histoire de ne rien perdre)
                with open(chemin_fichier, 'w', encoding='utf-8') as f:
                    f.write(output_buffer.getvalue())
                
                print(f"  ✓ Trace sauvegardée : {chemin_fichier}")
                
            except Exception as e:
                error_msg = f"Erreur lors de la génération de la trace pour le problème {num_probleme} ({methode}): {e}\n"
                print(f"  ✗ {error_msg}")
                # Sauvegarder quand même l'erreur dans le fichier (pour savoir ce qui a raté, c'est toujours utile)
                with open(chemin_fichier, 'w', encoding='utf-8') as f:
                    f.write(error_msg)
                    f.write(output_buffer.getvalue())
    
    print("\n" + "=" * 70)
    print("GÉNÉRATION TERMINÉE")
    print("=" * 70)
    print(f"Toutes les traces ont été sauvegardées dans le répertoire 'traces/'")
    print(f"Total : {compteur} fichier(s) généré(s)")


def analyser_toutes_les_traces():
    # Alors là, cette fonction analyse tous les fichiers .txt dans le dossier traces
    # En clair, on lit chaque fichier, on extrait les infos importantes, et on affiche des stats avec matplotlib comme l'option 5
    
    import re
    
    # Vérifier si matplotlib est disponible
    try:
        import matplotlib.pyplot as plt
        MATPLOTLIB_AVAILABLE = True
    except ImportError:
        MATPLOTLIB_AVAILABLE = False
    
    if not MATPLOTLIB_AVAILABLE:
        print("⚠ Matplotlib n'est pas installé. Impossible de créer les visualisations.")
        return
    
    print("\n" + "=" * 100)
    print(" " * 30 + "ANALYSE COMPLÈTE DES TRACES D'EXÉCUTION")
    print("=" * 100)
    
    # Créer le répertoire traces s'il n'existe pas
    dossier_traces = "traces"
    os.makedirs(dossier_traces, exist_ok=True)
    
    # Trouver tous les fichiers .txt
    pattern = os.path.join(dossier_traces, "*.txt")
    fichiers_txt = glob.glob(pattern)
    
    if not fichiers_txt:
        print(f"\n⚠ Aucun fichier .txt trouvé dans le dossier '{dossier_traces}'")
        print("   Exécutez d'abord l'option 2 pour générer des traces.")
        return
    
    # Trier les fichiers par nom
    fichiers_txt_tries = sorted(fichiers_txt)
    
    print(f"\n✓ {len(fichiers_txt_tries)} fichier(s) .txt trouvé(s)")
    print("\nFichiers analysés :")
    for fichier in fichiers_txt_tries:
        print(f"  - {os.path.basename(fichier)}")
    
    # Extraire les informations de chaque fichier
    donnees_traces = []
    
    for fichier in fichiers_txt_tries:
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                contenu = f.read()
            
            # Extraire le numéro du problème et la méthode du nom de fichier
            nom_fichier = os.path.basename(fichier)
            match = re.search(r'trace(\d+)-(no|bh)\.txt', nom_fichier)
            if not match:
                continue
            
            num_probleme = int(match.group(1))
            methode_abrev = match.group(2)
            methode = "NO" if methode_abrev == "no" else "BH"
            
            # Extraire le coût initial
            match_cout_initial = re.search(r'Coût initial \(.*?\) : ([\d.]+)', contenu)
            cout_initial = float(match_cout_initial.group(1)) if match_cout_initial else None
            
            # Extraire le coût final
            match_cout_final = re.search(r'Coût total optimal : ([\d.]+)', contenu)
            cout_final = float(match_cout_final.group(1)) if match_cout_final else None
            
            # Extraire l'amélioration
            match_amelioration = re.search(r'Amélioration : ([\d.]+) \(([\d.]+)%\)', contenu)
            amelioration_absolue = float(match_amelioration.group(1)) if match_amelioration else None
            amelioration_pourcentage = float(match_amelioration.group(2)) if match_amelioration else None
            
            # Extraire le nombre d'itérations
            match_iterations = re.search(r'Nombre d\'itérations : (\d+)', contenu)
            nb_iterations = int(match_iterations.group(1)) if match_iterations else None
            
            if cout_initial is not None and cout_final is not None:
                donnees_traces.append({
                    'fichier': nom_fichier,
                    'probleme': num_probleme,
                    'methode': methode,
                    'cout_initial': cout_initial,
                    'cout_final': cout_final,
                    'amelioration_absolue': amelioration_absolue,
                    'amelioration_pourcentage': amelioration_pourcentage,
                    'nb_iterations': nb_iterations
                })
        except Exception as e:
            print(f"\n⚠ Erreur lors de l'analyse de {fichier}: {e}")
            continue
    
    if not donnees_traces:
        print("\n⚠ Aucune donnée valide extraite des traces.")
        return
    
    # Organiser les données par problème
    donnees_par_probleme = {}
    for donnee in donnees_traces:
        num_pb = donnee['probleme']
        if num_pb not in donnees_par_probleme:
            donnees_par_probleme[num_pb] = {'NO': None, 'BH': None}
        donnees_par_probleme[num_pb][donnee['methode']] = donnee
    
    # Fonction pour calculer les statistiques
    def calculer_stats(valeurs):
        if not valeurs:
            return {'moyenne': 0, 'mediane': 0, 'min': 0, 'max': 0, 'ecart_type': 0}
        valeurs_triees = sorted(valeurs)
        moyenne = sum(valeurs) / len(valeurs)
        mediane = valeurs_triees[len(valeurs_triees) // 2] if len(valeurs_triees) % 2 == 1 else (valeurs_triees[len(valeurs_triees) // 2 - 1] + valeurs_triees[len(valeurs_triees) // 2]) / 2
        min_val = min(valeurs)
        max_val = max(valeurs)
        variance = sum((x - moyenne) ** 2 for x in valeurs) / len(valeurs)
        ecart_type = variance ** 0.5
        return {'moyenne': moyenne, 'mediane': mediane, 'min': min_val, 'max': max_val, 'ecart_type': ecart_type}
    
    # ========== VISUALISATION 1 : Tableau détaillé par problème ==========
    print("\n📊 Génération du tableau détaillé par problème...")
    
    # Préparer les données pour le tableau
    table_data = []
    for num_pb in sorted(donnees_par_probleme.keys()):
        for methode in ['NO', 'BH']:
            donnee = donnees_par_probleme[num_pb][methode]
            if donnee:
                table_data.append([
                    f"P{num_pb}",
                    methode,
                    f"{donnee['cout_initial']:.2f}",
                    f"{donnee['cout_final']:.2f}",
                    f"{donnee['amelioration_absolue']:.2f}" if donnee['amelioration_absolue'] is not None else "N/A",
                    f"{donnee['amelioration_pourcentage']:.2f}%" if donnee['amelioration_pourcentage'] is not None else "N/A",
                    f"{donnee['nb_iterations']}" if donnee['nb_iterations'] is not None else "N/A"
                ])
    
    if table_data:
        fig, ax = plt.subplots(figsize=(18, max(8, len(table_data) * 0.4 + 2)))
        ax.axis('tight')
        ax.axis('off')
        
        headers = ['Problème', 'Méthode', 'Coût init.', 'Coût final', 'Amélioration', 'Amélioration %', 'Itérations']
        table = ax.table(cellText=table_data, colLabels=headers, cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.8)
        
        # Style de l'en-tête
        for i in range(len(headers)):
            table[(0, i)].set_facecolor('#9C27B0')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Colorer les lignes selon la méthode
        for i in range(1, len(table_data) + 1):
            methode = table_data[i-1][1]
            couleur = '#E1BEE7' if methode == 'NO' else '#BBDEFB'  # Violet clair pour NO, Bleu clair pour BH
            for j in range(len(headers)):
                table[(i, j)].set_facecolor(couleur)
        
        plt.title('Analyse Détaillée par Problème', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.show()
    
    # ========== VISUALISATION 2 : Tableau récapitulatif global par méthode ==========
    print("\n📊 Génération du tableau récapitulatif global...")
    
    donnees_no = [d for d in donnees_traces if d['methode'] == 'NO']
    donnees_bh = [d for d in donnees_traces if d['methode'] == 'BH']
    
    # Calculer les statistiques globales
    stats_globales = {}
    for methode, donnees_methode in [('NO', donnees_no), ('BH', donnees_bh)]:
        if not donnees_methode:
            continue
        
        couts_initiaux = [d['cout_initial'] for d in donnees_methode if d['cout_initial'] is not None]
        couts_finaux = [d['cout_final'] for d in donnees_methode if d['cout_final'] is not None]
        ameliorations_abs = [d['amelioration_absolue'] for d in donnees_methode if d['amelioration_absolue'] is not None]
        ameliorations_pct = [d['amelioration_pourcentage'] for d in donnees_methode if d['amelioration_pourcentage'] is not None]
        iterations = [d['nb_iterations'] for d in donnees_methode if d['nb_iterations'] is not None]
        
        stats_globales[methode] = {
            'cout_initial': calculer_stats(couts_initiaux) if couts_initiaux else None,
            'cout_final': calculer_stats(couts_finaux) if couts_finaux else None,
            'amelioration_abs': calculer_stats(ameliorations_abs) if ameliorations_abs else None,
            'amelioration_pct': calculer_stats(ameliorations_pct) if ameliorations_pct else None,
            'iterations': calculer_stats(iterations) if iterations else None
        }
    
    # Créer le tableau récapitulatif
    table_data_recap = []
    for methode in ['NO', 'BH']:
        if methode not in stats_globales:
            continue
        
        stats = stats_globales[methode]
        
        # Coût initial
        if stats['cout_initial']:
            table_data_recap.append([
                methode,
                'Coût initial',
                f"{stats['cout_initial']['moyenne']:.2f}",
                f"{stats['cout_initial']['mediane']:.2f}",
                f"{stats['cout_initial']['min']:.2f}",
                f"{stats['cout_initial']['max']:.2f}",
                f"{stats['cout_initial']['ecart_type']:.2f}"
            ])
        
        # Coût final
        if stats['cout_final']:
            table_data_recap.append([
                methode,
                'Coût final',
                f"{stats['cout_final']['moyenne']:.2f}",
                f"{stats['cout_final']['mediane']:.2f}",
                f"{stats['cout_final']['min']:.2f}",
                f"{stats['cout_final']['max']:.2f}",
                f"{stats['cout_final']['ecart_type']:.2f}"
            ])
        
        # Amélioration absolue
        if stats['amelioration_abs']:
            table_data_recap.append([
                methode,
                'Amélioration (abs)',
                f"{stats['amelioration_abs']['moyenne']:.2f}",
                f"{stats['amelioration_abs']['mediane']:.2f}",
                f"{stats['amelioration_abs']['min']:.2f}",
                f"{stats['amelioration_abs']['max']:.2f}",
                f"{stats['amelioration_abs']['ecart_type']:.2f}"
            ])
        
        # Amélioration pourcentage
        if stats['amelioration_pct']:
            table_data_recap.append([
                methode,
                'Amélioration (%)',
                f"{stats['amelioration_pct']['moyenne']:.2f}",
                f"{stats['amelioration_pct']['mediane']:.2f}",
                f"{stats['amelioration_pct']['min']:.2f}",
                f"{stats['amelioration_pct']['max']:.2f}",
                f"{stats['amelioration_pct']['ecart_type']:.2f}"
            ])
        
        # Itérations
        if stats['iterations']:
            table_data_recap.append([
                methode,
                'Itérations',
                f"{stats['iterations']['moyenne']:.2f}",
                f"{stats['iterations']['mediane']:.2f}",
                f"{stats['iterations']['min']:.2f}",
                f"{stats['iterations']['max']:.2f}",
                f"{stats['iterations']['ecart_type']:.2f}"
            ])
    
    if table_data_recap:
        fig, ax = plt.subplots(figsize=(16, max(6, len(table_data_recap) * 0.5 + 2)))
        ax.axis('tight')
        ax.axis('off')
        
        headers_recap = ['Méthode', 'Métrique', 'Moyenne', 'Médiane', 'Min', 'Max', 'Écart-type']
        table_recap = ax.table(cellText=table_data_recap, colLabels=headers_recap, cellLoc='center', loc='center')
        table_recap.auto_set_font_size(False)
        table_recap.set_fontsize(10)
        table_recap.scale(1, 2)
        
        # Style de l'en-tête
        for i in range(len(headers_recap)):
            table_recap[(0, i)].set_facecolor('#9C27B0')
            table_recap[(0, i)].set_text_props(weight='bold', color='white')
        
        # Colorer les lignes selon la méthode
        for i in range(1, len(table_data_recap) + 1):
            methode = table_data_recap[i-1][0]
            couleur = '#E1BEE7' if methode == 'NO' else '#BBDEFB'
            for j in range(len(headers_recap)):
                table_recap[(i, j)].set_facecolor(couleur)
        
        plt.title('Statistiques Globales par Méthode', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.show()
    
    # ========== VISUALISATION 3 : Tableau de comparaison NO vs BH ==========
    print("\n📊 Génération du tableau de comparaison NO vs BH...")
    
    table_data_comparaison = []
    for num_pb in sorted(donnees_par_probleme.keys()):
        no = donnees_par_probleme[num_pb]['NO']
        bh = donnees_par_probleme[num_pb]['BH']
        
        if no and bh:
            meilleur = "NO" if no['cout_final'] < bh['cout_final'] else "BH" if bh['cout_final'] < no['cout_final'] else "Égal"
            table_data_comparaison.append([
                f"P{num_pb}",
                f"{no['cout_initial']:.2f}",
                f"{bh['cout_initial']:.2f}",
                f"{no['cout_final']:.2f}",
                f"{bh['cout_final']:.2f}",
                f"{no['nb_iterations']}" if no['nb_iterations'] is not None else "N/A",
                f"{bh['nb_iterations']}" if bh['nb_iterations'] is not None else "N/A",
                meilleur
            ])
    
    if table_data_comparaison:
        fig, ax = plt.subplots(figsize=(18, max(8, len(table_data_comparaison) * 0.4 + 2)))
        ax.axis('tight')
        ax.axis('off')
        
        headers_comparaison = ['Problème', 'Coût init. NO', 'Coût init. BH', 'Coût final NO', 'Coût final BH', 'It. NO', 'It. BH', 'Meilleur']
        table_comparaison = ax.table(cellText=table_data_comparaison, colLabels=headers_comparaison, cellLoc='center', loc='center')
        table_comparaison.auto_set_font_size(False)
        table_comparaison.set_fontsize(9)
        table_comparaison.scale(1, 1.8)
        
        # Style de l'en-tête
        for i in range(len(headers_comparaison)):
            table_comparaison[(0, i)].set_facecolor('#9C27B0')
            table_comparaison[(0, i)].set_text_props(weight='bold', color='white')
        
        # Colorer selon le meilleur résultat
        for i in range(1, len(table_data_comparaison) + 1):
            meilleur = table_data_comparaison[i-1][7]
            if meilleur == "NO":
                couleur = '#c8e6c9'  # Vert clair : NO meilleur
            elif meilleur == "BH":
                couleur = '#fff9c4'  # Jaune clair : BH meilleur
            else:
                couleur = '#e0e0e0'  # Gris : Égal
            
            for j in range(len(headers_comparaison)):
                table_comparaison[(i, j)].set_facecolor(couleur)
        
        plt.title('Comparaison NO vs BH', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.show()
    
    print("\n" + "=" * 100)
    print("✅ Analyse terminée ! Toutes les visualisations ont été générées.")
    print("=" * 100)


def resoudre_probleme_transport():
    # Alors là, c'est la fonction principale qui gère le menu et tout ça
    # En résumé : on affiche un menu, l'utilisateur choisit, on fait le boulot, sauf qu'on est pas payer pour
    
    # Pseudo-code :
    # TANT QUE l'utilisateur ne quitte pas:
    #   Afficher le menu
    #   Lire le choix
    #   SI choix = 1:
    #       Demander le numéro du problème
    #       Demander l'algorithme (NO ou BH)
    #       Résoudre le problème
    #   SINON SI choix = 2:
    #       Générer toutes les traces
    #   SINON SI choix = 3:
    #       Exécuter l'étude de complexité
    #   SINON SI choix = 4:
    #       Tracer les nuages de points
    #   SINON SI choix = 5:
    #       Analyser la complexité dans le pire des cas
    #   SINON SI choix = 6:
    #       Comparer les algorithmes
    #   SINON SI choix = 7:
    #       Quitter
    #   FIN SI
    # FIN TANT QUE
    
    print("=" * 70)
    print(" " * 20 + "PROBLÈME DE TRANSPORT")
    print("=" * 70)
    
    while True:
        # Menu principal (c'est juste un menu classique, rien de sorcier)
        print("\n" + "-" * 70)
        print("MENU PRINCIPAL")
        print("-" * 70)
        print("1. Résoudre un problème individuel")
        print("2. Générer toutes les traces d'exécution (12 problèmes × 2 algorithmes)")
        print("3. Exécuter l'étude de complexité pour une valeur de n")
        print("4. Analyser les résultats de complexité (choisir un JSON)")
        print("5. Statistiques complètes et comparaison de tous les JSON")
        print("6. Analyser tous les .txt de /traces")
        print("7. Quitter")
        print("-" * 70)
        
        choix_menu = input("\nVotre choix (1-7) : ").strip()
        
        if choix_menu == '1':
            # Résoudre un problème individuel (on résout juste un problème à la fois)
            print("\n" + "-" * 70)
            print("CHOIX DU PROBLÈME")
            print("-" * 70)
            try:
                num_probleme = input("Numéro du problème à traiter (1-12) : ").strip()
                if num_probleme.lower() in ['q', 'quit', 'exit', 'retour']:
                    continue
                
                num_probleme = int(num_probleme)
                if num_probleme < 1 or num_probleme > 12:
                    print("⚠ Erreur : le numéro doit être entre 1 et 12")
                    continue
            except ValueError:
                print("⚠ Erreur : veuillez entrer un nombre valide")
                continue
            
            # Choisir l'algorithme (Nord-Ouest ou Balas-Hammer, à toi de voir)
            print("\n" + "-" * 70)
            print("CHOIX DE L'ALGORITHME INITIAL")
            print("-" * 70)
            print("1. Nord-Ouest (NO)")
            print("2. Balas-Hammer (BH)")
            print("-" * 70)
            
            choix_algo = input("\nVotre choix (1 ou 2) : ").strip()
            
            if choix_algo == '1':
                methode = 'NO'
            elif choix_algo == '2':
                methode = 'BH'
            else:
                print("⚠ Choix invalide, utilisation de Nord-Ouest par défaut")
                methode = 'NO'
            
            # Résoudre le problème (on appelle la fonction qui fait tout le boulot, let's go !)
            try:
                resoudre_un_probleme(num_probleme, methode, capture_output=False)
            except Exception as e:
                print(f"\n⚠ Erreur : {e}")
                import traceback
                traceback.print_exc()
            
            # Proposer de continuer (on demande si l'utilisateur veut en faire un autre, histoire de voir)
            print("\n" + "-" * 70)
            continuer = input("Voulez-vous traiter un autre problème ? (o/n) : ").strip().lower()
            if continuer != 'o' and continuer != 'oui':
                continue
        
        elif choix_menu == '2':
            # Générer toutes les traces (on génère tous les fichiers de trace d'un coup, c'est efficace)
            print("\n" + "-" * 70)
            print("GÉNÉRATION DE TOUTES LES TRACES")
            print("-" * 70)
            print("Groupe : NEW2")
            print("Équipe : 3")
            print(f"\n⚠ Attention : Cette opération va générer 24 fichiers de trace (12 problèmes × 2 algorithmes).")
            confirmer = input("Continuer ? (o/n) : ").strip().lower()
            if confirmer == 'o' or confirmer == 'oui':
                try:
                    generer_toutes_les_traces()
                except Exception as e:
                    print(f"\n⚠ Erreur lors de la génération : {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("Opération annulée.")
        
        elif choix_menu == '3':
            # Exécuter l'étude de complexité pour une valeur de n spécifique
            print("\n" + "-" * 70)
            print("ÉTUDE DE LA COMPLEXITÉ")
            print("-" * 70)
            print("⚠ Attention : Cette opération peut prendre du temps selon le nombre d'exécutions choisi !")
            
            # Menu de choix de la valeur de n
            print("\n" + "-" * 70)
            print("CHOIX DE LA VALEUR DE N")
            print("-" * 70)
            print("1. n = 10")
            print("2. n = 40")
            print("3. n = 1e2 (100)")
            print("4. n = 4.1e2 (410)")
            print("5. n = 1e3 (1000)")
            print("6. n = 4.1e3 (4100)")
            print("7. n = 1e4 (10000)")
            print("8. Tous les n (test d'ensemble)")
            print("-" * 70)
            
            choix_n = input("\nVotre choix (1-8) : ").strip()
            
            # Mapping des choix vers les valeurs de n
            valeurs_n_map = {
                '1': 10,
                '2': 40,
                '3': 100,  # 1e2
                '4': 410,  # 4.1e2
                '5': 1000,  # 1e3
                '6': 4100,  # 4.1e3
                '7': 10000  # 1e4
            }
            
            # Créer le dossier complexity s'il n'existe pas
            dossier_complexity = "complexity"
            os.makedirs(dossier_complexity, exist_ok=True)
            
            if choix_n == '8':
                # Test d'ensemble : toutes les valeurs de n
                valeurs_n = [10, 40, 100, 410, 1000, 4100, 10000]
                fichier_json = os.path.join(dossier_complexity, 'complexite_resultats.json')
                print(f"\n✓ Test d'ensemble sélectionné")
                print(f"   Valeurs de n : {valeurs_n}")
                print(f"   Fichier de sortie : {fichier_json}")
            elif choix_n in valeurs_n_map:
                n_choisi = valeurs_n_map[choix_n]
                valeurs_n = [n_choisi]
                
                # Générer le nom du fichier JSON basé sur n
                # Pour les valeurs avec notation scientifique, utiliser une représentation claire
                noms_fichiers = {
                    10: 'complexite_resultats_n10.json',
                    40: 'complexite_resultats_n40.json',
                    100: 'complexite_resultats_n100.json',
                    410: 'complexite_resultats_n410.json',
                    1000: 'complexite_resultats_n1000.json',
                    4100: 'complexite_resultats_n4100.json',
                    10000: 'complexite_resultats_n10000.json'
                }
                nom_fichier = noms_fichiers[n_choisi]
                fichier_json = os.path.join(dossier_complexity, nom_fichier)
                
                print(f"\n✓ Valeur de n sélectionnée : {n_choisi}")
                print(f"   Fichier de sortie : {fichier_json}")
            else:
                print("⚠ Choix invalide, opération annulée.")
                continue
            
            # Afficher les informations sur la parallélisation
            from multiprocessing import cpu_count
            nb_cores = cpu_count()
            
            # Menu de choix de mode
            print("\n" + "-" * 70)
            print("CHOIX DU MODE D'EXÉCUTION")
            print("-" * 70)
            print("1. Mode Silencieux (peu de processus, plus lent mais moins de charge CPU)")
            print("2. Mode Modéré (plus de processus, équilibré)")
            print("3. Mode Vénère (maximum de processus, plus rapide mais charge CPU élevée)")
            print("-" * 70)
            
            choix_mode = input("\nVotre choix (1-3) : ").strip()
            
            # Configuration selon le mode choisi
            if choix_mode == '1':
                mode = 'silencieux'
                nb_processus_choisi = max(1, nb_cores // 4)  # 25% des cœurs
                taille_lot = 5
                pause_entre_lots = 0.3
                print(f"\n✓ Mode Silencieux sélectionné")
                print(f"   Processus : {nb_processus_choisi}/{nb_cores}")
                print(f"   Taille des lots : {taille_lot}")
                print(f"   Pause entre lots : {pause_entre_lots}s")
            elif choix_mode == '2':
                mode = 'modere'
                nb_processus_choisi = max(1, nb_cores - 1) if nb_cores > 2 else max(1, nb_cores)
                taille_lot = 10
                pause_entre_lots = 0.1
                print(f"\n✓ Mode Modéré sélectionné")
                print(f"   Processus : {nb_processus_choisi}/{nb_cores}")
                print(f"   Taille des lots : {taille_lot}")
                print(f"   Pause entre lots : {pause_entre_lots}s")
            elif choix_mode == '3':
                mode = 'venere'
                nb_processus_choisi = nb_cores  # Utiliser tous les cœurs
                taille_lot = 20
                pause_entre_lots = 0.05
                print(f"\n✓ Mode Vénère sélectionné")
                print(f"   Processus : {nb_processus_choisi}/{nb_cores} (TOUS LES CŒURS)")
                print(f"   Taille des lots : {taille_lot}")
                print(f"   Pause entre lots : {pause_entre_lots}s")
                print(f"   ⚠ ATTENTION : Charge CPU maximale !")
            else:
                print("⚠ Choix invalide, utilisation du mode Modéré par défaut")
                mode = 'modere'
                nb_processus_choisi = max(1, nb_cores - 1) if nb_cores > 2 else max(1, nb_cores)
                taille_lot = 10
                pause_entre_lots = 0.1
            
            # Menu de choix du nombre d'exécutions
            print("\n" + "-" * 70)
            print("CHOIX DU NOMBRE D'EXÉCUTIONS")
            print("-" * 70)
            print("1. Petit (1 exécution - rapide, pour tests)")
            print("2. Modéré (10 exécutions - équilibré)")
            print("3. Respecte du cahier des charges (100 exécutions - complet)")
            print("-" * 70)
            
            choix_nb_executions = input("\nVotre choix (1-3) : ").strip()
            
            # Configuration selon le nombre d'exécutions choisi
            if choix_nb_executions == '1':
                nb_executions = 1
                nom_mode_exec = "Petit"
                print(f"\n✓ Mode {nom_mode_exec} sélectionné")
                if choix_n == '8':
                    print(f"   Nombre d'exécutions par valeur de n : {nb_executions}")
                    print(f"   Total : {len(valeurs_n)} × {nb_executions} = {len(valeurs_n) * nb_executions} exécutions")
                else:
                    print(f"   Nombre d'exécutions : {nb_executions}")
            elif choix_nb_executions == '2':
                nb_executions = 10
                nom_mode_exec = "Modéré"
                print(f"\n✓ Mode {nom_mode_exec} sélectionné")
                if choix_n == '8':
                    print(f"   Nombre d'exécutions par valeur de n : {nb_executions}")
                    print(f"   Total : {len(valeurs_n)} × {nb_executions} = {len(valeurs_n) * nb_executions} exécutions")
                else:
                    print(f"   Nombre d'exécutions : {nb_executions}")
            elif choix_nb_executions == '3':
                nb_executions = 100
                nom_mode_exec = "Respecte du cahier des charges"
                print(f"\n✓ Mode {nom_mode_exec} sélectionné")
                if choix_n == '8':
                    print(f"   Nombre d'exécutions par valeur de n : {nb_executions}")
                    print(f"   Total : {len(valeurs_n)} × {nb_executions} = {len(valeurs_n) * nb_executions} exécutions")
                else:
                    print(f"   Nombre d'exécutions : {nb_executions}")
            else:
                print("⚠ Choix invalide, utilisation du mode Modéré par défaut (10 exécutions)")
                nb_executions = 10
                nom_mode_exec = "Modéré"
            
            # Estimation du temps (approximative, basée sur des estimations)
            temps_estime_par_n = {
                10: 0.01,
                40: 0.05,
                100: 0.15,
                410: 0.6,
                1000: 5.0,
                4100: 20.0,
                10000: 120.0
            }
            
            if choix_n == '8':
                # Test d'ensemble : calculer pour toutes les valeurs
                temps_total_estime = sum(temps_estime_par_n.get(n, 1.0) * nb_executions for n in valeurs_n)
            else:
                # Une seule valeur de n
                temps_total_estime = temps_estime_par_n.get(valeurs_n[0], 1.0) * nb_executions
            
            # Ajuster selon le nombre de processus (accélération approximative)
            acceleration = min(nb_processus_choisi, 0.8)  # Pas de gain linéaire parfait
            temps_total_estime = temps_total_estime / (1 + acceleration * (nb_processus_choisi - 1))
            
            heures = int(temps_total_estime // 3600)
            minutes = int((temps_total_estime % 3600) // 60)
            secondes = int(temps_total_estime % 60)
            
            print(f"\n⏱ Estimation du temps total : {heures}h {minutes}min {secondes}s")
            print(f"   (Estimation approximative, peut varier selon votre machine)")
            
            confirmer = input("\nContinuer ? (o/n) : ").strip().lower()
            if confirmer == 'o' or confirmer == 'oui':
                try:
                    resultats = executer_etude_complexite(
                        valeurs_n=valeurs_n,
                        utiliser_parallele=True,
                        nb_processus=nb_processus_choisi,
                        taille_lot=taille_lot,
                        pause_entre_lots=pause_entre_lots,
                        nb_executions=nb_executions,
                        fichier=fichier_json
                    )
                    print(f"\n✓ Étude terminée ! Résultats sauvegardés dans '{fichier_json}'")
                    print("   Vous pouvez maintenant utiliser l'option 4 pour analyser les résultats.")
                except Exception as e:
                    print(f"\n⚠ Erreur lors de l'étude : {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("Opération annulée.")
        
        elif choix_menu == '4':
            # Analyser les résultats de complexité (choisir un JSON puis sous-menu)
            print("\n" + "-" * 70)
            print("ANALYSE DES RÉSULTATS DE COMPLEXITÉ")
            print("-" * 70)
            
            # Lister les fichiers JSON disponibles dans le dossier complexity
            dossier_complexity = "complexity"
            os.makedirs(dossier_complexity, exist_ok=True)
            pattern = os.path.join(dossier_complexity, "complexite_resultats_n*.json")
            fichiers_json = glob.glob(pattern)
            # Ajouter aussi le fichier complexite_resultats.json s'il existe
            fichier_ensemble = os.path.join(dossier_complexity, "complexite_resultats.json")
            if os.path.exists(fichier_ensemble):
                fichiers_json.append(fichier_ensemble)
            
            if not fichiers_json:
                print("⚠ Aucun fichier de résultats trouvé.")
                print("   Exécutez d'abord l'option 3 pour générer des résultats.")
                continue
            
            # Trier les fichiers pour un affichage cohérent
            fichiers_json_tries = sorted(fichiers_json)
            
            # Afficher les fichiers disponibles
            print("\nFichiers JSON disponibles :")
            for idx, fichier in enumerate(fichiers_json_tries, 1):
                # Afficher seulement le nom du fichier (sans le chemin)
                nom_affichage = os.path.basename(fichier)
                print(f"  {idx}. {nom_affichage}")
            print(f"  {len(fichiers_json_tries) + 1}. Annuler")
            print("-" * 70)
            
            choix_fichier = input(f"\nVotre choix (1-{len(fichiers_json_tries) + 1}) : ").strip()
            
            try:
                idx_fichier = int(choix_fichier)
                if idx_fichier < 1 or idx_fichier > len(fichiers_json_tries) + 1:
                    print("⚠ Choix invalide, opération annulée.")
                    continue
                if idx_fichier == len(fichiers_json_tries) + 1:
                    continue  # Annuler
                
                fichier_selectionne = fichiers_json_tries[idx_fichier - 1]
                print(f"\n✓ Fichier sélectionné : {fichier_selectionne}")
                
                # Charger les résultats
                try:
                    resultats = charger_resultats_complexite(fichier=fichier_selectionne)
                except FileNotFoundError:
                    print(f"\n⚠ Erreur : Le fichier '{fichier_selectionne}' n'existe pas.")
                    continue
                except Exception as e:
                    print(f"\n⚠ Erreur lors du chargement : {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                # Sous-menu pour les analyses
                while True:
                    print("\n" + "-" * 70)
                    print("OPTIONS D'ANALYSE")
                    print("-" * 70)
                    print("1. Tracer les nuages de points")
                    print("2. Analyser la complexité dans le pire des cas")
                    print("3. Comparer les algorithmes")
                    print("4. Retour au menu principal")
                    print("-" * 70)
                    
                    choix_analyse = input("\nVotre choix (1-4) : ").strip()
                    
                    if choix_analyse == '1':
                        # Tracer les nuages de points
                        print("\n" + "-" * 70)
                        print("TRACÉ DES NUAGES DE POINTS")
                        print("-" * 70)
                        try:
                            tracer_nuages_de_points(resultats)
                            print("\n✓ Nuages de points tracés !")
                        except Exception as e:
                            print(f"\n⚠ Erreur : {e}")
                            import traceback
                            traceback.print_exc()
                    
                    elif choix_analyse == '2':
                        # Analyser la complexité dans le pire des cas
                        print("\n" + "-" * 70)
                        print("ANALYSE DE LA COMPLEXITÉ DANS LE PIRE DES CAS")
                        print("-" * 70)
                        try:
                            max_values = determiner_complexite_pire_cas(resultats)
                            print("\n✓ Analyse terminée ! Les graphiques montrent les valeurs maximales et les courbes de référence.")
                        except Exception as e:
                            print(f"\n⚠ Erreur : {e}")
                            import traceback
                            traceback.print_exc()
                    
                    elif choix_analyse == '3':
                        # Comparer les algorithmes
                        print("\n" + "-" * 70)
                        print("COMPARAISON DES ALGORITHMES")
                        print("-" * 70)
                        try:
                            comparer_algorithmes(resultats)
                            print("\n✓ Comparaison terminée !")
                        except Exception as e:
                            print(f"\n⚠ Erreur : {e}")
                            import traceback
                            traceback.print_exc()
                    
                    elif choix_analyse == '4':
                        # Retour au menu principal
                        break
                    
                    else:
                        print("⚠ Choix invalide, veuillez choisir un nombre entre 1 et 4")
            
            except ValueError:
                print("⚠ Choix invalide, veuillez entrer un nombre valide")
                continue
        
        elif choix_menu == '5':
            # Statistiques complètes et comparaison de tous les JSON
            try:
                analyser_tous_les_resultats()
            except Exception as e:
                print(f"\n⚠ Erreur : {e}")
                import traceback
                traceback.print_exc()
        
        elif choix_menu == '6':
            # Analyser tous les .txt de /traces
            try:
                analyser_toutes_les_traces()
            except Exception as e:
                print(f"\n⚠ Erreur : {e}")
                import traceback
                traceback.print_exc()
        
        elif choix_menu == '7':
            print("\nAu revoir !")
            break
        
        else:
            print("⚠ Choix invalide, veuillez choisir un nombre entre 1 et 7")


if __name__ == "__main__":
    # Alors là, c'est le point d'entrée du programme
    # Pour faire simple : on lance la fonction principale et on gère les erreurs, au cas où
    try:
        resoudre_probleme_transport()
    except KeyboardInterrupt:
        print("\n\nInterruption par l'utilisateur. Au revoir !")
    except Exception as e:
        print(f"\n⚠ Erreur fatale : {e}")
        import traceback
        traceback.print_exc()
