import cv2
import numpy as np
import heapq

# Définition des mouvements pour la 4-connexité (Haut, Bas, Gauche, Droite)
VOISINS_4_CONNEXITE = [
    (-1, 0), (1, 0), (0, -1), (0, 1)
]

# Définition de la 8-connexité (ajoute les 4 diagonales)
VOISINS_8_CONNEXITE = VOISINS_4_CONNEXITE + [
    (-1, -1), (-1, 1), (1, -1), (1, 1)
]

class ModeleurGraphe:

    # Initialise les variables de l'image, les dimensions et le mode par défaut
    def __init__(self):
        self.chemin_fichier_original = None
        self.image_couleur = None
        self.image_gris = None
        self.largeur = 0
        self.hauteur = 0
        self.est_chargee = False
        self.mode_connexite = '4' # Mode par défaut

    # Met à jour le mode de connexité (4 ou 8 voisins)
    def definir_mode_connexite(self, mode):
        self.mode_connexite = mode

    # Charge l'image depuis le disque, crée une copie grise et met à jour l'état
    def charger_image(self, chemin=None):
        if chemin is None and self.chemin_fichier_original is not None:
             chemin = self.chemin_fichier_original
        elif chemin is None:
             return False, "Aucun chemin de fichier fourni."

        try:
            img = cv2.imread(chemin)
            if img is None:
                return False, "Le fichier n'a pas pu être chargé."

            self.image_couleur = img.copy()
            # Conversion en niveaux de gris pour calculer les poids (intensité)
            self.image_gris = cv2.cvtColor(self.image_couleur, cv2.COLOR_BGR2GRAY)

            self.hauteur, self.largeur = self.image_gris.shape
            self.est_chargee = True
            self.chemin_fichier_original = chemin
            return True, f"Image chargée. Dimensions: {self.largeur}x{self.hauteur}"

        except Exception as e:
            self.est_chargee = False
            return False, f"Erreur lors du chargement : {e}"

    # Générateur qui renvoie les voisins valides et le coût du déplacement (poids)
    def obtenir_voisins_et_poids(self, h, l):
        if not self.est_chargee:
            return

        intensite_u = self.image_gris[h, l]

        # Sélection de la liste de voisins selon le mode choisi
        liste_voisins = VOISINS_8_CONNEXITE if self.mode_connexite == '8' else VOISINS_4_CONNEXITE

        for dh, dl in liste_voisins:
            h_v, l_v = h + dh, l + dl

            # Vérification des limites de l'image
            if 0 <= h_v < self.hauteur and 0 <= l_v < self.largeur:
                intensite_v = self.image_gris[h_v, l_v]
                # Le poids est la différence absolue d'intensité (contraste)
                poids = abs(int(intensite_u) - int(intensite_v))

                yield (h_v, l_v), max(1, poids)

    # Exécute l'algorithme de Dijkstra pour trouver le chemin le plus court
    def executer_dijkstra(self, noeud_depart, noeud_arrivee):
        if not self.est_chargee:
            return [], 0, 0

        h_depart, l_depart = noeud_depart
        h_arrivee, l_arrivee = noeud_arrivee

        # Initialisation des structures de données
        distances = np.full((self.hauteur, self.largeur), np.inf)
        distances[h_depart, l_depart] = 0
        predecesseurs = np.empty((self.hauteur, self.largeur), dtype=object)

        # File de priorité (Tas binaire) : (distance, h, l)
        file_priorite = [(0, h_depart, l_depart)]
        nb_noeuds_visites = 0

        while file_priorite:
            dist_u, h_u, l_u = heapq.heappop(file_priorite)

            # Optimisation : si on a déjà trouvé mieux, on ignore
            if dist_u > distances[h_u, l_u]:
                continue

            nb_noeuds_visites += 1
            if (h_u, l_u) == noeud_arrivee:
                break

            # Exploration des voisins
            for (h_v, l_v), poids in self.obtenir_voisins_et_poids(h_u, l_u):
                nouvelle_dist = dist_u + poids

                if nouvelle_dist < distances[h_v, l_v]:
                    distances[h_v, l_v] = nouvelle_dist
                    predecesseurs[h_v, l_v] = (h_u, l_u)
                    heapq.heappush(file_priorite, (nouvelle_dist, h_v, l_v))

        # Reconstruction du chemin (Backtracking)
        chemin = []
        h_courant, l_courant = noeud_arrivee
        cout_final = distances[h_arrivee, l_arrivee]

        if cout_final == np.inf:
            return [], 0, nb_noeuds_visites

        while (h_courant, l_courant) != noeud_depart:
            chemin.append((h_courant, l_courant))
            predecesseur = predecesseurs[h_courant, l_courant]
            if predecesseur is None:
                return [], 0, nb_noeuds_visites
            h_courant, l_courant = predecesseur

        chemin.append(noeud_depart)
        chemin.reverse()

        return chemin, cout_final, nb_noeuds_visites

    # Dessine le chemin trouvé et les marqueurs sur l'image couleur
    def dessiner_chemin_sur_image(self, chemin, taille_marqueur=4):
        if not self.est_chargee or not chemin:
            return self.image_couleur

        # Convention OpenCV : BGR (Bleu, Vert, Rouge)
        # Chemin : Rouge (0, 0, 255)
        for h, l in chemin:
            cv2.circle(self.image_couleur, (l, h), radius=0, color=(0, 0, 255), thickness=1)

        # Départ : Bleu (255, 0, 0)
        h_dep, l_dep = chemin[0]
        cv2.circle(self.image_couleur, (l_dep, h_dep), radius=taille_marqueur, color=(255, 0, 0), thickness=-1)

        # Arrivée : Vert (0, 255, 0)
        h_arr, l_arr = chemin[-1]
        cv2.circle(self.image_couleur, (l_arr, h_arr), radius=taille_marqueur, color=(0, 255, 0), thickness=-1)

        return self.image_couleur
