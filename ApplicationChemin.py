import sys
import os
import cv2
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QFileDialog, QMessageBox,
    QSizePolicy, QToolButton, QPushButton, QSlider, QScrollArea
)
from PyQt6.QtGui import QPixmap, QImage, QMouseEvent
from PyQt6.QtCore import Qt, QPoint, pyqtSignal

# Import du modèle renommé
from ModeleurGraphe import ModeleurGraphe

# Fonction utilitaire pour obtenir le chemin absolu des ressources (compatible PyInstaller)
def chemin_ressource(chemin_relatif):
    try:
        # PyInstaller crée un dossier temporaire _MEIPASS
        chemin_base = sys._MEIPASS
    except Exception:
        chemin_base = os.path.abspath(".")

    return os.path.join(chemin_base, chemin_relatif)

# Définition du chemin vers le fichier d'interface
FICHIER_UI = chemin_ressource('form.ui')

class LabelImage(QLabel):
    signal_clic = pyqtSignal(QPoint)

    # Initialise le label personnalisé avec les paramètres d'affichage et de souris
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMouseTracking(False)

    # Détecte le clic gauche de la souris et émet un signal avec la position
    def mousePressEvent(self, evenement: QMouseEvent):
        if evenement.button() == Qt.MouseButton.LeftButton and self.pixmap() is not None:
            self.signal_clic.emit(evenement.pos())

class ApplicationChemin(QMainWindow):
    # Constructeur principal : charge l'interface UI et initialise les variables
    def __init__(self, modeleur_graphe):
        super().__init__()
        self.modeleur = modeleur_graphe
        self.point_depart = None
        self.point_arrivee = None
        self.facteur_zoom = 1.0
        self.est_en_cours = False

        if not os.path.exists(FICHIER_UI):
             raise FileNotFoundError(f"Le fichier {FICHIER_UI} est introuvable.")

        uic.loadUi(FICHIER_UI, self)
        self.setWindowTitle("Graphe Image & Algorithme de Dijkstra ✨")

        self._connecter_widgets()
        self.reinitialiser_interface()

    # Récupère les widgets du fichier UI et connecte les signaux aux fonctions
    def _connecter_widgets(self):
        # 1. Gestion de la Zone de Défilement (Resté en anglais dans le XML -> 'imageScrollArea')
        self.zone_defilement = self.findChild(QScrollArea, 'imageScrollArea')
        self.label_image = LabelImage()
        # Nom français pour le widget interne
        self.label_image.setObjectName('labelAffichageImage')

        if self.zone_defilement:
            self.zone_defilement.setWidget(self.label_image)
            self.zone_defilement.setWidgetResizable(True)
        else:
            self.setCentralWidget(self.label_image)

        # 2. Récupération des Labels (Nouveaux noms français dans le findChild)
        self.lbl_dimensions = self.findChild(QLabel, 'valeurDimLabel')
        self.lbl_noeuds = self.findChild(QLabel, 'valeurNoeudsLabel')
        self.lbl_connexite = self.findChild(QLabel, 'valeurConnexiteLabel')

        # Ceux-ci sont restés en anglais/mixte dans mon XML pour l'exemple, ou renommés partiellement
        self.lbl_depart = self.findChild(QLabel, 'startPointLabel')
        self.lbl_arrivee = self.findChild(QLabel, 'endPointLabel')

        self.lbl_longueur = self.findChild(QLabel, 'valeurLongueurLabel')
        self.lbl_cout = self.findChild(QLabel, 'valeurCoutLabel')
        self.lbl_visites = self.findChild(QLabel, 'valeurVisitesLabel')
        self.lbl_statut = self.findChild(QLabel, 'resultStatusLabel')
        self.lbl_zoom = self.findChild(QLabel, 'valeurZoomLabel')

        # 3. Récupération des Contrôles (Nouveaux noms français)
        self.btn_charger = self.findChild(QToolButton, 'boutonCharger')
        self.btn_reset = self.findChild(QToolButton, 'boutonReinitialiser')
        self.btn_calculer = self.findChild(QPushButton, 'boutonCalculer')

        self.btn_conn4 = self.findChild(QToolButton, 'boutonConnexite4')
        self.btn_conn8 = self.findChild(QToolButton, 'boutonConnexite8')

        self.slider_zoom = self.findChild(QSlider, 'sliderZoom')

        # 4. Connexions des Signaux aux Slots (Fonctions)
        self.label_image.signal_clic.connect(self.gerer_clic_image)

        if self.btn_charger: self.btn_charger.clicked.connect(self.ouvrir_image)
        if self.btn_reset: self.btn_reset.clicked.connect(self.reinitialiser_interface)
        if self.btn_calculer: self.btn_calculer.clicked.connect(self.lancer_dijkstra)

        if self.btn_conn4: self.btn_conn4.clicked.connect(lambda: self.definir_connexite('4'))
        if self.btn_conn8: self.btn_conn8.clicked.connect(lambda: self.definir_connexite('8'))

        if self.slider_zoom:
            self.slider_zoom.valueChanged.connect(self.changer_zoom)
            self.slider_zoom.setValue(100)

    # Réinitialise l'interface et les variables pour un nouveau calcul
    def reinitialiser_interface(self):
        self.point_depart = None
        self.point_arrivee = None
        if self.btn_calculer: self.btn_calculer.setEnabled(False)

        if self.lbl_depart: self.lbl_depart.setText("N/A")
        if self.lbl_arrivee: self.lbl_arrivee.setText("N/A")
        if self.lbl_longueur: self.lbl_longueur.setText("0")
        if self.lbl_cout: self.lbl_cout.setText("0.00")
        if self.lbl_visites: self.lbl_visites.setText("0")
        if self.lbl_statut:
            self.lbl_statut.setText("Prêt. Chargez une image.")
            self.lbl_statut.setStyleSheet("color: white;")

        if self.modeleur.est_chargee:
            self.modeleur.charger_image() # Recharge l'originale sans dessins
            self.rafraichir_affichage()

    # Change le mode de connexité (4 ou 8) et met à jour l'apparence des boutons
    def definir_connexite(self, mode):
        # Gestion de l'état visuel des boutons (style "Bouton Radio")
        if self.btn_conn4 and self.btn_conn8:
            if mode == '4':
                self.btn_conn4.setChecked(True)
                self.btn_conn8.setChecked(False)
            else:
                self.btn_conn4.setChecked(False)
                self.btn_conn8.setChecked(True)

        self.modeleur.definir_mode_connexite(mode)
        if self.lbl_connexite: self.lbl_connexite.setText(f"{mode}-connexité")

        # Si un point était déjà sélectionné, on reset pour éviter les incohérences
        if self.point_depart:
            self.reinitialiser_interface()
            if self.lbl_statut: self.lbl_statut.setText(f"Mode {mode}-Connexité. Resélectionnez.")

    # Met à jour le facteur de zoom selon le slider et rafraîchit l'affichage
    def changer_zoom(self, valeur):
        self.facteur_zoom = valeur / 100.0
        if self.lbl_zoom: self.lbl_zoom.setText(f"{valeur}%")
        self.rafraichir_affichage()

    # Ouvre une boîte de dialogue pour charger une image depuis le disque
    def ouvrir_image(self):
        chemin, _ = QFileDialog.getOpenFileName(self, "Ouvrir Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if chemin:
            succes, message = self.modeleur.charger_image(chemin)
            if succes:
                self.reinitialiser_interface()
                if self.lbl_dimensions: self.lbl_dimensions.setText(f"{self.modeleur.largeur} × {self.modeleur.hauteur}")
                if self.lbl_noeuds: self.lbl_noeuds.setText(f"{self.modeleur.largeur * self.modeleur.hauteur}")
                if self.slider_zoom: self.slider_zoom.setValue(100)
            else:
                QMessageBox.critical(self, "Erreur", message)

    # Convertit l'image OpenCV en QPixmap, applique le zoom et l'affiche
    def rafraichir_affichage(self):
        if not self.modeleur.est_chargee: return

        # Copie de l'image pour affichage
        img_affichage = self.modeleur.image_couleur.copy()
        haut, larg, canaux = img_affichage.shape
        octets_par_ligne = 3 * larg

        # Conversion format OpenCV (BGR) vers Qt (RGB)
        q_img = QImage(img_affichage.data, larg, haut, octets_par_ligne, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)

        # Calcul des nouvelles dimensions
        nouv_larg = int(larg * self.facteur_zoom)
        nouv_haut = int(haut * self.facteur_zoom)

        if nouv_larg > 0 and nouv_haut > 0:
            pixmap = pixmap.scaled(nouv_larg, nouv_haut, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)

        self.label_image.setFixedSize(nouv_larg, nouv_haut)
        self.label_image.setPixmap(pixmap)

    # Convertit les coordonnées du clic souris en coordonnées réelles de l'image
    def gerer_clic_image(self, position):
        if not self.modeleur.est_chargee: return

        # Ajustement des coordonnées en fonction du zoom
        x = int(position.x() / self.facteur_zoom)
        y = int(position.y() / self.facteur_zoom)

        if 0 <= x < self.modeleur.largeur and 0 <= y < self.modeleur.hauteur:
            self.selectionner_pixel(y, x) # Attention ordre (Ligne, Colonne) -> (y, x)
        else:
            if self.lbl_statut: self.lbl_statut.setText("Clic hors limites.")

    # Gère la logique de sélection des points de départ et d'arrivée
    def selectionner_pixel(self, h, l):
        # Cas 1 : Sélection du point de départ
        if self.point_depart is None:
            self.point_depart = (h, l)
            if self.lbl_depart: self.lbl_depart.setText(f"({l}, {h})")

            img_temp = self.modeleur.image_couleur.copy()
            cv2.circle(img_temp, (l, h), radius=2, color=(255, 0, 0), thickness=-1)
            self.afficher_image_temporaire(img_temp)

            if self.lbl_statut:
                self.lbl_statut.setText("Départ validé. Sélectionnez l'arrivée.")
                self.lbl_statut.setStyleSheet("color: #55aaff;")

        # Cas 2 : Sélection du point d'arrivée
        elif self.point_arrivee is None:
            self.point_arrivee = (h, l)
            if self.lbl_arrivee: self.lbl_arrivee.setText(f"({l}, {h})")

            img_temp = self.modeleur.image_couleur.copy()
            # Redessine le départ
            cv2.circle(img_temp, (self.point_depart[1], self.point_depart[0]), radius=2, color=(255, 0, 0), thickness=-1)
            # Dessine l'arrivée
            cv2.circle(img_temp, (l, h), radius=2, color=(0, 0, 255), thickness=-1)
            self.afficher_image_temporaire(img_temp)

            if self.lbl_statut:
                self.lbl_statut.setText("Prêt ! Cliquez sur 'Calculer le chemin'.")
                self.lbl_statut.setStyleSheet("color: #55ff55; font-weight: bold;")
            if self.btn_calculer: self.btn_calculer.setEnabled(True)

        # Cas 3 : Reset si on clique une 3ème fois
        else:
            self.reinitialiser_interface()
            if self.lbl_statut: self.lbl_statut.setText("Reset. Sélectionnez un nouveau départ.")

    # Affiche une image temporaire (pour les marqueurs) sans écraser l'originale
    def afficher_image_temporaire(self, img_bgr):
        self.modeleur.image_couleur = img_bgr
        self.rafraichir_affichage()

    # Lance l'algorithme de Dijkstra et met à jour l'interface avec les résultats
    def lancer_dijkstra(self):
        if not self.point_depart or not self.point_arrivee: return

        if self.lbl_statut: self.lbl_statut.setText("Calcul en cours...")
        if self.btn_calculer: self.btn_calculer.setEnabled(False)
        QApplication.processEvents() # Force la mise à jour de l'UI

        chemin, cout, visites = self.modeleur.executer_dijkstra(self.point_depart, self.point_arrivee)

        if self.lbl_longueur: self.lbl_longueur.setText(str(len(chemin)))
        if self.lbl_cout: self.lbl_cout.setText(f"{cout:.1f}")
        if self.lbl_visites: self.lbl_visites.setText(str(visites))

        if chemin:
            self.modeleur.dessiner_chemin_sur_image(chemin)
            self.rafraichir_affichage()
            if self.lbl_statut:
                self.lbl_statut.setText("Chemin trouvé !")
                self.lbl_statut.setStyleSheet("color: #55ff55;")
        else:
            if self.lbl_statut:
                self.lbl_statut.setText("Impossible de trouver un chemin.")
                self.lbl_statut.setStyleSheet("color: red;")

        if self.btn_calculer: self.btn_calculer.setEnabled(True)
