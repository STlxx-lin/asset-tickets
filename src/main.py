import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.ui.character_selection import CharacterSelection

ICON_FILE_NAME = "logo-ykohqv-s3wb4i-pck6c0.png"

def _resolve_icon_path():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ICON_FILE_NAME),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ICON_FILE_NAME),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""

def main():
    os.environ["QT_LOGGING_RULES"] = "qt.imageformats.*=false"
    
    app = QApplication(sys.argv)
    icon_path = _resolve_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    window = CharacterSelection()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
