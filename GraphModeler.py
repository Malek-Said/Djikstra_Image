import cv2
import numpy as np
import heapq
import os

# Définition de la 4-connexité
VOISINS_4_CONNEXITE = [
    (-1, 0), (1, 0), (0, -1), (0, 1)    # Haut, Bas, Gauche, Droite
]
# Définition de la 8-connexité (inclut les diagonales)
VOISINS_8_CONNEXITE = VOISINS_4_CONNEXITE + [
    (-1, -1), (-1, 1), (1, -1), (1, 1)  # Diagonales
]

class GraphModeler:
    """Gère le chargement de l'image, la modélisation et l'exécution de Dijkstra."""
    def __init__(self):
        self.original_path = None
        self.color_image = None
        self.gray_image = None
        self.W = 0
        self.H = 0
        self.is_loaded = False
        self.connectivity_mode = '4' # Mode de connexité par défaut

    def set_connectivity_mode(self, mode):
        """Met à jour le mode de connexité à utiliser pour le calcul."""
        self.connectivity_mode = mode

    def load_image(self, path=None):
        """Charge l'image à partir du chemin ou la recharge si path est None."""
        if path is None and self.original_path is not None:
             path = self.original_path
        elif path is None:
             return False, "Aucun chemin de fichier fourni."

        try:
            img = cv2.imread(path)
            if img is None:
                return False, "Le fichier n'a pas pu être chargé."

            self.color_image = img.copy()
            self.gray_image = cv2.cvtColor(self.color_image, cv2.COLOR_BGR2GRAY)

            self.H, self.W = self.gray_image.shape
            self.is_loaded = True
            self.original_path = path
            return True, f"Image chargée. Dimensions: {self.W}x{self.H}"

        except Exception as e:
            self.is_loaded = False
            return False, f"Erreur lors du chargement : {e}"

    def get_neighbors_and_weights(self, h, w):
        """Génère les voisins et le poids en fonction de self.connectivity_mode."""
        if not self.is_loaded:
            return

        intensite_u = self.gray_image[h, w]

        # Choisir la liste de voisins en fonction du mode
        voisins_list = VOISINS_8_CONNEXITE if self.connectivity_mode == '8' else VOISINS_4_CONNEXITE

        for dh, dw in voisins_list:
            h_v, w_v = h + dh, w + dw

            if 0 <= h_v < self.H and 0 <= w_v < self.W:
                intensite_v = self.gray_image[h_v, w_v]
                poids = abs(int(intensite_u) - int(intensite_v))

                yield (h_v, w_v), max(1, poids)

    def run_dijkstra(self, start_node, end_node):
        """Exécute l'algorithme de Dijkstra et retourne le chemin et le coût."""
        if not self.is_loaded:
            return [], 0, 0

        start_h, start_w = start_node
        end_h, end_w = end_node

        distances = np.full((self.H, self.W), np.inf)
        distances[start_h, start_w] = 0
        predecesseurs = np.empty((self.H, self.W), dtype=object)
        priority_queue = [(0, start_h, start_w)]
        visited_nodes_count = 0

        while priority_queue:
            dist_u, h_u, w_u = heapq.heappop(priority_queue)

            if dist_u > distances[h_u, w_u]:
                continue

            visited_nodes_count += 1
            if (h_u, w_u) == end_node:
                break

            for (h_v, w_v), poids in self.get_neighbors_and_weights(h_u, w_u):
                nouvelle_dist = dist_u + poids

                if nouvelle_dist < distances[h_v, w_v]:
                    distances[h_v, w_v] = nouvelle_dist
                    predecesseurs[h_v, w_v] = (h_u, w_u)
                    heapq.heappush(priority_queue, (nouvelle_dist, h_v, w_v))

        # Reconstruction du chemin
        path = []
        current_h, current_w = end_node
        final_cost = distances[end_h, end_w]

        if final_cost == np.inf:
            return [], 0, visited_nodes_count

        while (current_h, current_w) != start_node:
            path.append((current_h, current_w))
            predecesseur = predecesseurs[current_h, current_w]
            if predecesseur is None:
                return [], 0, visited_nodes_count
            current_h, current_w = predecesseur

        path.append(start_node)
        path.reverse()

        return path, final_cost, visited_nodes_count

    def draw_path_on_image(self, path, marker_size=4):
        """Trace le chemin et les marqueurs sur l'image couleur."""
        if not self.is_loaded or not path:
            return self.color_image

        # NOTE: Les couleurs de l'UI sont inversées par rapport à la convention BGR:
        # Bleu (Départ) -> (255, 0, 0)
        # Rouge (Arrivée) -> (0, 0, 255)
        # Chemin (Tracé) -> (0, 0, 255) (Rouge)

        # Tracer le chemin en ROUGE vif (BGR = (0, 0, 255))
        for h, w in path:
            cv2.circle(self.color_image, (w, h), radius=0, color=(0, 0, 255), thickness=1)

        # Marquer le point de départ en BLEU (BGR = (255, 0, 0)) pour correspondre au style UI
        start_h, start_w = path[0]
        cv2.circle(self.color_image, (start_w, start_h), radius=marker_size, color=(255, 0, 0), thickness=-1)

        # Marquer le point d'arrivée en ROUGE (BGR = (0, 0, 255))
        end_h, end_w = path[-1]
        cv2.circle(self.color_image, (end_w, end_h), radius=marker_size, color=(0, 0, 255), thickness=-1)

        return self.color_image
