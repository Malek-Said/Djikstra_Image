import sys
import os
import cv2
import math
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QFileDialog, QMessageBox,
    QSizePolicy, QToolButton, QPushButton, QSlider, QScrollArea, QWidget, QCheckBox, QStatusBar
)
from PyQt6.QtGui import QPixmap, QImage, QMouseEvent, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal

from GraphModeler import GraphModeler

#UI_FILE = 'form.ui'

# --- AJOUTEZ CE BLOC AU DÉBUT DE PathSolverApp.py (après les imports) ---

def resource_path(relative_path):
    """ Obtenir le chemin absolu vers la ressource, fonctionne pour le dev et pour PyInstaller """
    try:
        # PyInstaller crée un dossier temporaire _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Utilisez cette fonction pour définir le chemin de votre fichier UI
UI_FILE = resource_path('form.ui')

class ImageLabel(QLabel):
    clicked_signal = pyqtSignal(QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMouseTracking(False)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap() is not None:
            self.clicked_signal.emit(event.pos())

class PathSolverApp(QMainWindow):
    def __init__(self, graph_modeler):
        super().__init__()
        self.graph_modeler = graph_modeler
        self.start_point = None
        self.end_point = None
        self.zoom_factor = 1.0
        self.is_running = False

        if not os.path.exists(UI_FILE):
             raise FileNotFoundError(f"Le fichier {UI_FILE} est introuvable.")

        uic.loadUi(UI_FILE, self)
        self.setWindowTitle("Graphe Image & Algorithme de Dijkstra ✨")

        self._connect_widgets()
        self.reset_ui_state()

    def _connect_widgets(self):
        # 1. Gestion de la ScrollArea
        self.scroll_area = self.findChild(QScrollArea, 'imageScrollArea')
        self.image_label = ImageLabel()
        self.image_label.setObjectName('imageDisplayLabel')

        if self.scroll_area:
            self.scroll_area.setWidget(self.image_label)
            self.scroll_area.setWidgetResizable(True)
        else:
            self.setCentralWidget(self.image_label)

        # 2. Labels
        self.lbl_dim = self.findChild(QLabel, 'dimValueLabel')
        self.lbl_nodes = self.findChild(QLabel, 'nodesValueLabel')
        self.lbl_conn = self.findChild(QLabel, 'connValueLabel')
        self.lbl_start = self.findChild(QLabel, 'startPointLabel')
        self.lbl_end = self.findChild(QLabel, 'endPointLabel')
        self.lbl_len = self.findChild(QLabel, 'pathLengthValueLabel')
        self.lbl_cost = self.findChild(QLabel, 'totalCostValueLabel')
        self.lbl_visited = self.findChild(QLabel, 'visitedNodesValueLabel')
        self.lbl_status = self.findChild(QLabel, 'resultStatusLabel')
        self.lbl_zoom = self.findChild(QLabel, 'zoomValueLabel')

        # 3. Contrôles
        self.btn_load = self.findChild(QToolButton, 'loadButton')
        self.btn_reset = self.findChild(QToolButton, 'resetButton')
        self.btn_calc = self.findChild(QPushButton, 'calculateButton')
        self.btn_conn4 = self.findChild(QToolButton, 'size16Button')
        self.btn_conn8 = self.findChild(QToolButton, 'size32Button')
        self.slider_zoom = self.findChild(QSlider, 'zoomSlider')

        # 4. Connexions
        self.image_label.clicked_signal.connect(self.handle_image_click)

        if self.btn_load: self.btn_load.clicked.connect(self.open_image)
        if self.btn_reset: self.btn_reset.clicked.connect(self.reset_ui_state)
        if self.btn_calc: self.btn_calc.clicked.connect(self.run_dijkstra)

        if self.btn_conn4: self.btn_conn4.clicked.connect(lambda: self.set_connectivity('4'))
        if self.btn_conn8: self.btn_conn8.clicked.connect(lambda: self.set_connectivity('8'))

        if self.slider_zoom:
            self.slider_zoom.valueChanged.connect(self.change_zoom)
            self.slider_zoom.setValue(100)

    def reset_ui_state(self):
        self.start_point = None
        self.end_point = None
        if self.btn_calc: self.btn_calc.setEnabled(False)

        if self.lbl_start: self.lbl_start.setText("N/A")
        if self.lbl_end: self.lbl_end.setText("N/A")
        if self.lbl_len: self.lbl_len.setText("0")
        if self.lbl_cost: self.lbl_cost.setText("0.00")
        if self.lbl_visited: self.lbl_visited.setText("0")
        if self.lbl_status:
            self.lbl_status.setText("Prêt. Chargez une image.")
            self.lbl_status.setStyleSheet("color: white;")

        if self.graph_modeler.is_loaded:
            self.graph_modeler.load_image()
            self.refresh_display()

    def set_connectivity(self, mode):
        # Cette logique active/désactive la propriété 'checked' du bouton
        # Ce qui déclenchera le style CSS que nous avons ajouté dans le .ui
        if self.btn_conn4 and self.btn_conn8:
            if mode == '4':
                self.btn_conn4.setChecked(True)
                self.btn_conn8.setChecked(False)
            else:
                self.btn_conn4.setChecked(False)
                self.btn_conn8.setChecked(True)

        self.graph_modeler.set_connectivity_mode(mode)
        if self.lbl_conn: self.lbl_conn.setText(f"{mode}-connexité")

        if self.start_point:
            self.reset_ui_state()
            if self.lbl_status: self.lbl_status.setText(f"Mode {mode}-Connexité. Resélectionnez.")

    def change_zoom(self, value):
        self.zoom_factor = value / 100.0
        if self.lbl_zoom: self.lbl_zoom.setText(f"{value}%")
        self.refresh_display()

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            success, msg = self.graph_modeler.load_image(path)
            if success:
                self.reset_ui_state()
                if self.lbl_dim: self.lbl_dim.setText(f"{self.graph_modeler.W} × {self.graph_modeler.H}")
                if self.lbl_nodes: self.lbl_nodes.setText(f"{self.graph_modeler.W * self.graph_modeler.H}")
                if self.slider_zoom: self.slider_zoom.setValue(100)
            else:
                QMessageBox.critical(self, "Erreur", msg)

    def refresh_display(self):
        if not self.graph_modeler.is_loaded: return

        display_img = self.graph_modeler.color_image.copy()
        height, width, channel = display_img.shape
        bytes_per_line = 3 * width
        q_img = QImage(display_img.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)

        new_w = int(width * self.zoom_factor)
        new_h = int(height * self.zoom_factor)

        if new_w > 0 and new_h > 0:
            pixmap = pixmap.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)

        self.image_label.setFixedSize(new_w, new_h)
        self.image_label.setPixmap(pixmap)

    def handle_image_click(self, pos: QPoint):
        if not self.graph_modeler.is_loaded: return

        x = int(pos.x() / self.zoom_factor)
        y = int(pos.y() / self.zoom_factor)

        if 0 <= x < self.graph_modeler.W and 0 <= y < self.graph_modeler.H:
            self.select_pixel(y, x)
        else:
            if self.lbl_status: self.lbl_status.setText("Clic hors limites.")

    def select_pixel(self, h, w):
        if self.start_point is None:
            self.start_point = (h, w)
            if self.lbl_start: self.lbl_start.setText(f"({w}, {h})")

            temp_img = self.graph_modeler.color_image.copy()
            cv2.circle(temp_img, (w, h), radius=2, color=(255, 0, 0), thickness=-1)
            self.display_temp_image(temp_img)

            if self.lbl_status:
                self.lbl_status.setText("Départ validé. Sélectionnez l'arrivée.")
                self.lbl_status.setStyleSheet("color: #55aaff;")

        elif self.end_point is None:
            self.end_point = (h, w)
            if self.lbl_end: self.lbl_end.setText(f"({w}, {h})")

            temp_img = self.graph_modeler.color_image.copy()
            cv2.circle(temp_img, (self.start_point[1], self.start_point[0]), radius=2, color=(255, 0, 0), thickness=-1)
            cv2.circle(temp_img, (w, h), radius=2, color=(0, 0, 255), thickness=-1)
            self.display_temp_image(temp_img)

            if self.lbl_status:
                self.lbl_status.setText("Prêt ! Cliquez sur 'Calculer le chemin'.")
                self.lbl_status.setStyleSheet("color: #55ff55; font-weight: bold;")
            if self.btn_calc: self.btn_calc.setEnabled(True)

        else:
            self.reset_ui_state()
            if self.lbl_status: self.lbl_status.setText("Reset. Sélectionnez un nouveau départ.")

    def display_temp_image(self, img_bgr):
        self.graph_modeler.color_image = img_bgr
        self.refresh_display()

    def run_dijkstra(self):
        if not self.start_point or not self.end_point: return

        if self.lbl_status: self.lbl_status.setText("Calcul en cours...")
        if self.btn_calc: self.btn_calc.setEnabled(False)
        QApplication.processEvents()

        path, cost, visited = self.graph_modeler.run_dijkstra(self.start_point, self.end_point)

        if self.lbl_len: self.lbl_len.setText(str(len(path)))
        if self.lbl_cost: self.lbl_cost.setText(f"{cost:.1f}")
        if self.lbl_visited: self.lbl_visited.setText(str(visited))

        if path:
            self.graph_modeler.draw_path_on_image(path)
            self.refresh_display()
            if self.lbl_status:
                self.lbl_status.setText("Chemin trouvé !")
                self.lbl_status.setStyleSheet("color: #55ff55;")
        else:
            if self.lbl_status:
                self.lbl_status.setText("Impossible de trouver un chemin.")
                self.lbl_status.setStyleSheet("color: red;")

        if self.btn_calc: self.btn_calc.setEnabled(True)
