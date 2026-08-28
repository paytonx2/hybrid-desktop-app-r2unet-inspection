import sys
import os

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow(base_dir)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
