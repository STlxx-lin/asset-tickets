import sys
import os
# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from src.ui.character_selection import CharacterSelection
import os

def main():
    # 设置环境变量来禁用libpng警告
    os.environ["QT_LOGGING_RULES"] = "qt.imageformats.*=false"
    
    app = QApplication(sys.argv)
    window = CharacterSelection()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

