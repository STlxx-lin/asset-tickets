import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.core.database import db_manager
from src.ui.character_selection import CharacterSelection

ICON_FILES = ["app_icon.ico", "app_icon.icns", "logo-ykohqv-s3wb4i-pck6c0.png"]

def _resolve_icon_path():
    """按优先级从打包临时目录、程序所在目录和源码根目录解析图标文件。"""
    search_dirs = []
    
    # 1. PyInstaller 打包解压目录
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        search_dirs.append(meipass)
        
    # 2. 可执行文件所在目录（Nuitka / PyInstaller 目录模式）与 macOS App Bundle 目录
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        search_dirs.append(exe_dir)
        contents_dir = os.path.dirname(exe_dir)
        if os.path.basename(contents_dir) == 'Contents':
            search_dirs.append(os.path.join(contents_dir, 'Resources'))
            app_dir = os.path.dirname(contents_dir)
            search_dirs.append(app_dir)
            search_dirs.append(os.path.dirname(app_dir))
    except Exception:
        pass

    # 3. 入口脚本路径所在目录
    try:
        search_dirs.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        pass

    # 4. 源码根目录（src/main.py 上溯一级）
    search_dirs.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    search_dirs.append(os.getcwd())

    for base_dir in search_dirs:
        for icon_name in ICON_FILES:
            path = os.path.join(base_dir, icon_name)
            if os.path.exists(path):
                return path
    return ""

def main():
    # 设置 Windows 任务栏专属 AppUserModelID，确保任务栏独立显示应用图标
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "takuya.material.workorder.system"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    os.environ["QT_LOGGING_RULES"] = "qt.imageformats.*=false"
    
    app = QApplication(sys.argv)
    # 应用退出时关闭数据库常驻连接
    app.aboutToQuit.connect(db_manager.disconnect)
    
    icon_path = _resolve_icon_path()
    if icon_path:
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    else:
        app_icon = None

    window = CharacterSelection()
    if app_icon:
        window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

