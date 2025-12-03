import sys
from PyQt6.QtWidgets import QApplication
from PathSolverApp import PathSolverApp
from GraphModeler import GraphModeler

if __name__ == '__main__':
    modeleur = GraphModeler()
    app = QApplication(sys.argv)
    window = PathSolverApp(modeleur)
    window.show()
    sys.exit(app.exec())
