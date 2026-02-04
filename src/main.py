import sys
from PySide6.QtWidgets import QApplication
from ui.character_selection import CharacterSelection
import os

if __name__ == "__main__":
    # 设置环境变量来禁用libpng警告
    os.environ["QT_LOGGING_RULES"] = "qt.imageformats.*=false"
    
    app = QApplication(sys.argv)
    window = CharacterSelection()
    window.show()
    sys.exit(app.exec())

