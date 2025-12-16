import sys
from PyQt6.QtWidgets import QApplication
from ApplicationChemin import ApplicationChemin
from ModeleurGraphe import ModeleurGraphe

if __name__ == '__main__':
    # Initialisation du modèle (logique métier)
    modeleur = ModeleurGraphe()

    # Création de l'application Qt
    app = QApplication(sys.argv)

    # Création de la fenêtre principale (Vue) en lui passant le modèle
    fenetre = ApplicationChemin(modeleur)
    fenetre.show()

    # Exécution de la boucle principale
    sys.exit(app.exec())
