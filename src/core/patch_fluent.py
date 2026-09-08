# coding: utf-8
"""
patch_fluent.py
----------------
针对 macOS / Linux / Windows 跨平台环境下，PySide6 (Shiboken) 与 QFluentWidgets
在模态对话框与弹出式菜单（RoundMenu / ComboBoxMenu / AcrylicMenu）交互时可能出现的
C++ 析构阶段焦点通知空指针崩溃（EXC_BAD_ACCESS / SIGSEGV）进行全局运行时热修复。

本补丁随源码提交，无论本地打包还是云端 CI/CD 构建均自动生效，无需修改虚拟环境第三方包。
"""

import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

_patched = False


def patch_qfluentwidgets():
    """应用 QFluentWidgets 运行时稳定性补丁"""
    global _patched
    if _patched:
        return
    _patched = True

    try:
        _patch_menu_widgets()
    except Exception as e:
        logger.warning(f"[patch_fluent] 菜单组件补丁应用异常: {e}")

    try:
        _patch_combo_box()
    except Exception as e:
        logger.warning(f"[patch_fluent] 下拉框组件补丁应用异常: {e}")

    try:
        _patch_acrylic_menu()
    except Exception as e:
        logger.warning(f"[patch_fluent] 亚克力菜单组件补丁应用异常: {e}")

    logger.info("[patch_fluent] QFluentWidgets 跨平台稳定性补丁已成功加载")


def _clear_menu_focus(menu_obj):
    """安全清空菜单及其子视图的焦点"""
    try:
        if hasattr(menu_obj, 'view') and menu_obj.view:
            menu_obj.view.clearFocus()
        menu_obj.clearFocus()
        focused = QApplication.focusWidget()
        if focused and (
            focused is menu_obj
            or (hasattr(menu_obj, 'view') and focused is menu_obj.view)
            or menu_obj.isAncestorOf(focused)
        ):
            focused.clearFocus()
    except Exception:
        pass


def _patch_menu_widgets():
    import qfluentwidgets.components.widgets.menu as menu_mod

    # 1. 修复 MenuActionListWidget
    OrigMenuActionListWidget = menu_mod.MenuActionListWidget
    orig_malw_init = OrigMenuActionListWidget.__init__

    def safe_malw_init(self, parent=None):
        orig_malw_init(self, parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def safe_malw_focus_in(self, e):
        e.ignore()

    OrigMenuActionListWidget.__init__ = safe_malw_init
    OrigMenuActionListWidget.focusInEvent = safe_malw_focus_in

    # 2. 修复 RoundMenu 及其子类
    OrigRoundMenu = menu_mod.RoundMenu
    orig_rm_init = OrigRoundMenu.__init__
    orig_rm_hide = OrigRoundMenu._hideMenu
    orig_rm_item_clicked = OrigRoundMenu._onItemClicked
    orig_rm_close_event = OrigRoundMenu.closeEvent
    orig_rm_hide_event = OrigRoundMenu.hideEvent

    def safe_rm_init(self, title="", parent=None):
        orig_rm_init(self, title, parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def safe_rm_hide(self, isHideBySystem=False):
        _clear_menu_focus(self)
        return orig_rm_hide(self, isHideBySystem)

    def safe_rm_item_clicked(self, item):
        _clear_menu_focus(self)
        return orig_rm_item_clicked(self, item)

    def safe_rm_close_event(self, e):
        _clear_menu_focus(self)
        return orig_rm_close_event(self, e)

    def safe_rm_hide_event(self, e):
        _clear_menu_focus(self)
        return orig_rm_hide_event(self, e)

    OrigRoundMenu.__init__ = safe_rm_init
    OrigRoundMenu._hideMenu = safe_rm_hide
    OrigRoundMenu._onItemClicked = safe_rm_item_clicked
    OrigRoundMenu.closeEvent = safe_rm_close_event
    OrigRoundMenu.hideEvent = safe_rm_hide_event


def _patch_combo_box():
    import qfluentwidgets.components.widgets.combo_box as combo_mod

    OrigComboBoxBase = combo_mod.ComboBoxBase
    orig_close_combo_menu = OrigComboBoxBase._closeComboMenu

    def safe_close_combo_menu(self):
        if not self.dropMenu:
            return
        try:
            _clear_menu_focus(self.dropMenu)
            self.dropMenu.close()
        except Exception:
            pass
        self.dropMenu = None

    OrigComboBoxBase._closeComboMenu = safe_close_combo_menu


def _patch_acrylic_menu():
    try:
        import qfluentwidgets.components.material.acrylic_menu as acrylic_mod
    except ImportError:
        return

    OrigAcrylicMenuBase = acrylic_mod.AcrylicMenuBase

    def safe_set_up_menu(self, view):
        if hasattr(self, 'view') and self.view and self.view is not view:
            old_view = self.view
            try:
                self.hBoxLayout.removeWidget(old_view)
                old_view.clearFocus()
                old_view.setParent(None)
                old_view.close()
                old_view.deleteLater()
            except Exception:
                pass

        self.view = view
        self.hBoxLayout.addWidget(self.view)
        self.setShadowEffect()
        self.view.itemClicked.connect(self._onItemClicked)
        self.view.itemEntered.connect(self._onItemEntered)

    OrigAcrylicMenuBase.setUpMenu = safe_set_up_menu
