"""Rizum Painter UI Font Helper.

This plugin is intentionally separate from the PT-to-PS bridge. It only
experiments with Painter's Qt UI font settings in the current session.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PANEL = None
_DOCK = None
PLUGIN_VERSION = "0.2.0"
_MIN_DOCK_WIDTH = 250
_DEFAULT_DOCK_WIDTH = _MIN_DOCK_WIDTH
_DEFAULT_DOCK_HEIGHT = 184
_RESET_BUTTON_WIDTH = 68
_APPLY_BUTTON_WIDTH = 72
_DEFAULT_LANGUAGE = "en"
_I18N_DIR = Path(__file__).resolve().parent / "i18n"
_FALLBACK_TEXT = {
    "panel_title": "UI Font",
    "size": "Size",
    "font": "Font",
    "system_default": "System Default",
    "open_fonts_folder": "Open fonts folder",
    "refresh_font_list": "Refresh font list",
    "refresh": "Refresh",
    "no_hinting": "No hinting",
    "reset": "Reset",
    "apply": "Apply",
    "loaded": "Rizum Painter UI Font plugin loaded",
    "unloaded": "Rizum Painter UI Font plugin unloaded",
}


def _load_translations():
    translations = {_DEFAULT_LANGUAGE: dict(_FALLBACK_TEXT)}
    if not _I18N_DIR.exists():
        return translations

    for path in sorted(_I18N_DIR.glob("*.json")):
        language = _normalize_language(path.stem)
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        translations[language] = {str(key): str(value) for key, value in data.items()}
        root = language.split("_", 1)[0]
        translations.setdefault(root, translations[language])
    return translations


def _normalize_language(language):
    return str(language or "").strip().lower().replace("-", "_")


def _resolve_language(saved_language, app_language, system_language):
    for candidate in (saved_language, app_language, system_language):
        language = _normalize_language(candidate)
        if not language:
            continue
        if language in _TEXT:
            return language
        root = language.split("_", 1)[0]
        if root in _TEXT:
            return root
    return _DEFAULT_LANGUAGE


_TEXT = _load_translations()


def _load_prettier_ui():
    """Return the sibling UI kit when it is installed next to this plugin."""
    plugin_root = Path(__file__).resolve().parent
    prettier_root = plugin_root.parent / "rizum-pt-ui-prettier"
    if not prettier_root.exists():
        return None
    prettier_path = str(prettier_root)
    if prettier_path not in sys.path:
        sys.path.insert(0, prettier_path)
    try:
        import rizum_ui
    except Exception:
        return None
    return rizum_ui


class UiScalePanel:
    def __init__(self):
        from PySide6 import QtCore, QtGui, QtWidgets

        self.QtCore = QtCore
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self.ui = _load_prettier_ui()
        self.store = QtCore.QSettings("Rizum", "PainterUiFont")
        self.language = _resolve_language(
            self.store.value("language", ""),
            QtCore.QLocale().name(),
            QtCore.QLocale.system().name(),
        )
        self.original_font = QtWidgets.QApplication.font()
        self.font_dir = Path(__file__).resolve().parent / "fonts"
        self._loaded_families = {}
        self._base_panel_stylesheet = ""

        self.widget = QtWidgets.QWidget()
        self.widget.setWindowTitle(self._tr("panel_title"))
        if self.ui is not None:
            self._build_prettier_layout()
        else:
            self._build_fallback_layout()

        self._populate_fonts()

    def _build_prettier_layout(self):
        QtCore = self.QtCore
        QtWidgets = self.QtWidgets

        self.ui.apply_theme(self.widget, mode="overlay")
        self.ui.apply_compact_dock_surface(self.widget)
        layout = self.ui.make_compact_dock_layout(self.widget)

        card = self.ui.make_compact_dock_card()
        card_layout = card.layout()
        layout.addWidget(card)

        main = QtWidgets.QWidget()
        main.setObjectName("RizumTransparent")
        main_layout = QtWidgets.QVBoxLayout(main)
        main_layout.setContentsMargins(12, 12, 12, 6)
        main_layout.setSpacing(10)

        self.scale = self.ui.make_spin_input(float(self.store.value("scale", 1.0)))
        main_layout.addWidget(
            self.ui.make_field_row(
                self._tr("size"),
                self.scale,
                label_width=self._label_width(),
                gap=8,
                width=66,
            )
        )

        self.font_combo = self.ui.make_combo_input()
        self.font_combo.setMinimumWidth(54)
        main_layout.addWidget(
            self.ui.make_field_row(
                self._tr("font"),
                self.font_combo,
                label_width=self._label_width(),
                gap=8,
            )
        )

        tool_row = QtWidgets.QHBoxLayout()
        tool_row.setContentsMargins(self._label_width() + 8, -6, 0, 2)
        tool_row.setSpacing(0)

        icon_group = QtWidgets.QHBoxLayout()
        icon_group.setContentsMargins(0, 0, 0, 0)
        icon_group.setSpacing(4)
        self.browse_btn = self.ui.make_icon_button("folder.svg", self._tr("open_fonts_folder"))
        self.browse_btn.clicked.connect(self._open_fonts_dir)
        self.refresh_btn = self.ui.make_icon_button("refresh.svg", self._tr("refresh_font_list"))
        self.refresh_btn.clicked.connect(self._populate_fonts)
        icon_group.addWidget(self.browse_btn)
        icon_group.addWidget(self.refresh_btn)
        tool_row.addLayout(icon_group)
        tool_row.addStretch(1)

        hint_widget = QtWidgets.QWidget()
        hint_widget.setObjectName("RizumInlineCheckbox")
        hint_widget.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        hint_widget.setMinimumWidth(88)
        hint_layout = QtWidgets.QHBoxLayout(hint_widget)
        hint_layout.setContentsMargins(6, 3, 6, 3)
        hint_layout.setSpacing(6)
        hint_label = QtWidgets.QLabel(self._tr("no_hinting"))
        hint_label.setObjectName("RizumHintLabel")
        hint_label.setMinimumWidth(62)
        hint_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        hint_layout.addWidget(hint_label)
        self.hinting_cb = self.ui.make_mock_checkbox()
        self.hinting_cb.setChecked(_read_bool(self.store.value("hinting_off", True)))
        hint_layout.addWidget(self.hinting_cb)
        hint_widget.mousePressEvent = (
            lambda event: self.hinting_cb.toggle()
            if event.button() == QtCore.Qt.MouseButton.LeftButton
            else None
        )
        tool_row.addWidget(hint_widget)
        main_layout.addLayout(tool_row)

        card_layout.addWidget(main)
        card_layout.addStretch(1)

        footer = QtWidgets.QWidget()
        footer.setObjectName("RizumTransparent")
        footer.setFixedHeight(48)
        footer_outer = QtWidgets.QVBoxLayout(footer)
        footer_outer.setContentsMargins(0, 0, 0, 0)
        footer_outer.setSpacing(0)
        footer_row = QtWidgets.QWidget()
        footer_row.setObjectName("RizumTransparent")
        footer_layout = QtWidgets.QHBoxLayout(footer_row)
        footer_layout.setContentsMargins(10, 0, 10, 0)
        footer_layout.setSpacing(8)
        footer_layout.addStretch(1)
        self.reset_btn = self.ui.ActionButton.create(self._tr("reset"), "dialog-secondary")
        self.ui.set_compact_footer_button_width(self.reset_btn, _RESET_BUTTON_WIDTH)
        self.reset_btn.clicked.connect(self.reset)
        self.apply_btn = self.ui.ActionButton.create(self._tr("apply"), "dialog-primary")
        self.ui.set_compact_footer_button_width(self.apply_btn, _APPLY_BUTTON_WIDTH)
        self.apply_btn.clicked.connect(self.apply)
        footer_layout.addWidget(self.reset_btn)
        footer_layout.addWidget(self.apply_btn)
        footer_outer.addWidget(footer_row, 1)
        card_layout.addWidget(footer)
        self.widget.setMinimumWidth(_MIN_DOCK_WIDTH)
        self.widget.setMinimumHeight(self.widget.minimumSizeHint().height())
        self._base_panel_stylesheet = self.widget.styleSheet()

    def _build_fallback_layout(self):
        QtWidgets = self.QtWidgets

        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        size_row = QtWidgets.QHBoxLayout()
        size_row.setSpacing(6)
        size_label = QtWidgets.QLabel(self._tr("size"))
        size_label.setFixedWidth(self._label_width())
        size_row.addWidget(size_label)
        self.scale = QtWidgets.QDoubleSpinBox()
        self.scale.setRange(0.75, 2.0)
        self.scale.setSingleStep(0.05)
        self.scale.setDecimals(2)
        self.scale.setMaximumWidth(80)
        self.scale.setValue(float(self.store.value("scale", 1.0)))
        size_row.addWidget(self.scale)
        size_row.addStretch(1)
        layout.addLayout(size_row)

        font_row = QtWidgets.QHBoxLayout()
        font_row.setSpacing(6)
        font_label = QtWidgets.QLabel(self._tr("font"))
        font_label.setFixedWidth(self._label_width())
        font_row.addWidget(font_label)
        self.font_combo = QtWidgets.QComboBox()
        self.font_combo.setMaximumWidth(160)
        font_row.addWidget(self.font_combo)
        font_row.addStretch(1)
        layout.addLayout(font_row)

        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(2)
        spacer = QtWidgets.QWidget()
        spacer.setFixedWidth(self._label_width() + 6)
        actions_row.addWidget(spacer)
        self.browse_btn = _fallback_icon_button(
            self.QtCore,
            self.QtGui,
            QtWidgets,
            "folder.svg",
            "..",
            self._tr("open_fonts_folder"),
        )
        self.browse_btn.setToolTip(self._tr("open_fonts_folder"))
        self.browse_btn.clicked.connect(self._open_fonts_dir)
        actions_row.addWidget(self.browse_btn)
        self.refresh_btn = _fallback_icon_button(
            self.QtCore,
            self.QtGui,
            QtWidgets,
            "refresh.svg",
            self._tr("refresh"),
            self._tr("refresh_font_list"),
        )
        self.refresh_btn.setToolTip(self._tr("refresh_font_list"))
        self.refresh_btn.clicked.connect(self._populate_fonts)
        actions_row.addWidget(self.refresh_btn)
        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        self.hinting_cb = QtWidgets.QCheckBox(self._tr("no_hinting"))
        self.hinting_cb.setChecked(_read_bool(self.store.value("hinting_off", True)))
        layout.addWidget(self.hinting_cb)

        layout.addStretch(1)

        btn_row = QtWidgets.QHBoxLayout()
        self.reset_btn = QtWidgets.QPushButton(self._tr("reset"))
        self.reset_btn.clicked.connect(self.reset)
        btn_row.addWidget(self.reset_btn)
        self.apply_btn = QtWidgets.QPushButton(self._tr("apply"))
        self.apply_btn.clicked.connect(self.apply)
        btn_row.addWidget(self.apply_btn)
        layout.addLayout(btn_row)

    def _populate_fonts(self):
        self.font_combo.clear()
        self._loaded_families.clear()

        system_default = self._tr("system_default")
        self.font_combo.addItem(system_default, None)
        self._loaded_families[system_default] = None

        if self.font_dir.exists():
            for font_path in sorted(self.font_dir.iterdir()):
                if font_path.suffix.lower() not in {".ttf", ".otf"}:
                    continue
                font_id = self.QtGui.QFontDatabase.addApplicationFont(str(font_path))
                if font_id < 0:
                    continue
                families = self.QtGui.QFontDatabase.applicationFontFamilies(font_id)
                for family in families:
                    if family not in self._loaded_families:
                        self._loaded_families[family] = family
                        self.font_combo.addItem(family, family)

        saved_family = self.store.value("font_family", "")
        if saved_family:
            idx = self.font_combo.findData(saved_family)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)

    def _open_fonts_dir(self):
        self.font_dir.mkdir(parents=True, exist_ok=True)
        url = self.QtCore.QUrl.fromLocalFile(str(self.font_dir))
        self.QtGui.QDesktopServices.openUrl(url)

    def apply(self):
        app = self.QtWidgets.QApplication.instance()
        if app is None:
            return

        scale = float(self.scale.value())
        font_family = self.font_combo.currentData()

        font = self.QtGui.QFont(self.original_font)
        base_size = self.original_font.pointSizeF()
        if base_size <= 0:
            base_size = float(self.original_font.pointSize())
        if base_size > 0:
            font.setPointSizeF(base_size * scale)
        if font_family:
            font.setFamily(font_family)
        if self.hinting_cb.isChecked():
            font.setHintingPreference(self.QtGui.QFont.PreferNoHinting)

        app.setFont(font)
        for widget in app.allWidgets():
            _refresh_widget_font(widget, font)
        self._refresh_own_panel_font(font)

        self.store.setValue("scale", scale)
        self.store.setValue("font_family", font_family or "")
        self.store.setValue("hinting_off", self.hinting_cb.isChecked())
        self.store.sync()

    def reset(self):
        app = self.QtWidgets.QApplication.instance()
        if app is None:
            return

        app.setFont(self.original_font)
        for widget in app.allWidgets():
            _refresh_widget_font(widget, self.original_font)
        self._refresh_own_panel_font(self.original_font)

        self.scale.setValue(1.0)
        self.font_combo.setCurrentIndex(0)
        self.hinting_cb.setChecked(True)

        self.store.setValue("scale", 1.0)
        self.store.setValue("font_family", "")
        self.store.setValue("hinting_off", True)
        self.store.sync()

    def close(self):
        pass

    def _tr(self, key):
        return _TEXT.get(self.language, _TEXT[_DEFAULT_LANGUAGE]).get(
            key, _TEXT[_DEFAULT_LANGUAGE][key]
        )

    def _label_width(self):
        return 44 if self.language in {"ja", "es"} else 28

    def _refresh_own_panel_font(self, font):
        _refresh_widget_tree_font(self.widget, font)
        if _DOCK is not None:
            _refresh_widget_tree_font(_DOCK, font)
        if self.ui is not None:
            self.widget.setStyleSheet(
                self._base_panel_stylesheet + "\n" + _build_panel_font_override(font)
            )


def start_plugin():
    import substance_painter as sp

    global _DOCK, _PANEL
    _PANEL = UiScalePanel()
    _DOCK = sp.ui.add_dock_widget(_PANEL.widget)
    _DOCK.setWindowTitle(_PANEL._tr("panel_title"))
    _connect_floating_resize()
    _DOCK.show()
    _resize_floating_dock()

    saved_scale = float(_PANEL.store.value("scale", 1.0))
    saved_family = _PANEL.store.value("font_family", "")
    saved_hinting = _read_bool(_PANEL.store.value("hinting_off", True))
    if saved_scale != 1.0 or saved_family or not saved_hinting:
        _PANEL.apply()

    sp.logging.info(_PANEL._tr("loaded"))


def close_plugin():
    import substance_painter as sp

    global _DOCK, _PANEL
    language = _PANEL.language if _PANEL is not None else _DEFAULT_LANGUAGE
    if _PANEL is not None:
        _PANEL.close()
        _PANEL = None
    if _DOCK is not None:
        sp.ui.delete_ui_element(_DOCK)
        _DOCK = None
    sp.logging.info(_TEXT.get(language, _TEXT[_DEFAULT_LANGUAGE])["unloaded"])


def _connect_floating_resize():
    try:
        _DOCK.topLevelChanged.connect(lambda floating: _resize_floating_dock() if floating else None)
    except Exception:
        pass


def _resize_floating_dock():
    if _DOCK is None:
        return
    try:
        if hasattr(_DOCK, "isFloating") and not _DOCK.isFloating():
            return
    except Exception:
        pass
    try:
        _DOCK.resize(_DEFAULT_DOCK_WIDTH, _DEFAULT_DOCK_HEIGHT)
    except Exception:
        pass
    try:
        _PANEL.widget.resize(_DEFAULT_DOCK_WIDTH, _DEFAULT_DOCK_HEIGHT)
    except Exception:
        pass
    try:
        _PANEL.QtCore.QTimer.singleShot(0, lambda: _DOCK.resize(_DEFAULT_DOCK_WIDTH, _DEFAULT_DOCK_HEIGHT))
    except Exception:
        pass


def _refresh_widget_font(widget, font):
    try:
        widget.setFont(font)
    except Exception:
        return
    try:
        widget.updateGeometry()
    except Exception:
        pass
    try:
        widget.repaint()
    except Exception:
        pass


def _refresh_widget_tree_font(root, font):
    if root is None:
        return
    _refresh_widget_font(root, font)
    try:
        from PySide6 import QtWidgets

        children = root.findChildren(QtWidgets.QWidget)
    except Exception:
        children = []
    for child in children:
        _refresh_widget_font(child, font)


def _build_panel_font_override(font):
    family = font.family().replace('"', '\\"')
    point_size = font.pointSizeF()
    if point_size <= 0:
        point_size = float(font.pointSize())
    if point_size <= 0:
        point_size = 11.0
    return f"""
QWidget#RizumSurface,
QWidget#RizumSurface *,
QWidget#RizumCompactDockSurface,
QWidget#RizumCompactDockSurface *,
QLabel#RizumFieldLabel,
QLabel#RizumHintLabel,
QLabel#RizumMockText,
QPushButton[variant="dialog-secondary"],
QPushButton[variant="dialog-primary"],
QMenu#RizumPopupMenu {{
    font-family: "{family}", Arial, sans-serif;
    font-size: {point_size:.2f}pt;
}}
"""


def _fallback_icon_button(QtCore, QtGui, QtWidgets, icon_name, text, tooltip):
    button = QtWidgets.QPushButton()
    icon_path = Path(__file__).resolve().parent / "icons" / icon_name
    if icon_path.exists():
        button.setIcon(QtGui.QIcon(str(icon_path)))
        button.setIconSize(QtCore.QSize(14, 14))
        button.setFixedSize(26, 26)
    else:
        button.setText(text)
        button.setFixedSize(64 if len(text) > 2 else 24, 20)
    button.setToolTip(tooltip)
    return button


def _read_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
