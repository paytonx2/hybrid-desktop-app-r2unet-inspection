import sys
import os

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def get_base_dir():
    # When built with PyInstaller, keep data/ and .env next to the .exe
    # (not inside the hidden _internal/ folder) so users can find them.
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    base_dir = get_base_dir()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow(base_dir)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
