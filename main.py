import sys
from PySide6.QtWidgets import QApplication
from ui.character_selection import CharacterSelection

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CharacterSelection()
    window.show()
    sys.exit(app.exec())

