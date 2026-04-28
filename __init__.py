"""Rizum Painter UI Font Helper.

This plugin is intentionally separate from the PT-to-PS bridge. It only
experiments with Painter's Qt UI font settings in the current session.
"""

from __future__ import annotations

from pathlib import Path

_PANEL = None
_DOCK = None
PLUGIN_VERSION = "0.2.0"


class UiScalePanel:
    def __init__(self):
        from PySide6 import QtCore, QtGui, QtWidgets

        self.QtCore = QtCore
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self.store = QtCore.QSettings("Rizum", "PainterUiFont")
        self.original_font = QtWidgets.QApplication.font()
        self.font_dir = Path(__file__).resolve().parent / "fonts"
        self._loaded_families = {}

        self.widget = QtWidgets.QWidget()
        self.widget.setWindowTitle("UI Font")
        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Size row
        size_row = QtWidgets.QHBoxLayout()
        size_row.setSpacing(6)
        size_label = QtWidgets.QLabel("Size")
        size_label.setFixedWidth(30)
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

        # Font row: label + combo
        font_row = QtWidgets.QHBoxLayout()
        font_row.setSpacing(6)
        font_label = QtWidgets.QLabel("Font")
        font_label.setFixedWidth(30)
        font_row.addWidget(font_label)
        self.font_combo = QtWidgets.QComboBox()
        self.font_combo.setMaximumWidth(160)
        font_row.addWidget(self.font_combo)
        font_row.addStretch(1)
        layout.addLayout(font_row)

        # Actions sub-row: indented under Font
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(2)
        spacer = QtWidgets.QWidget()
        spacer.setFixedWidth(36)
        actions_row.addWidget(spacer)
        self.browse_btn = QtWidgets.QPushButton("..")
        self.browse_btn.setFixedSize(24, 20)
        self.browse_btn.setToolTip("Open fonts folder")
        self.browse_btn.clicked.connect(self._open_fonts_dir)
        actions_row.addWidget(self.browse_btn)
        self.refresh_btn = QtWidgets.QPushButton("↻")
        self.refresh_btn.setFixedSize(24, 20)
        self.refresh_btn.setToolTip("Refresh font list")
        self.refresh_btn.clicked.connect(self._populate_fonts)
        actions_row.addWidget(self.refresh_btn)
        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        # Hinting checkbox
        self.hinting_cb = QtWidgets.QCheckBox("No hinting")
        self.hinting_cb.setChecked(
            _read_bool(self.store.value("hinting_off", True))
        )
        layout.addWidget(self.hinting_cb)

        layout.addStretch(1)

        # Buttons row
        btn_row = QtWidgets.QHBoxLayout()
        self.apply_btn = QtWidgets.QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply)
        btn_row.addWidget(self.apply_btn)
        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset)
        btn_row.addWidget(self.reset_btn)
        layout.addLayout(btn_row)

        self._populate_fonts()

    def _populate_fonts(self):
        self.font_combo.clear()
        self._loaded_families.clear()

        self.font_combo.addItem("System Default", None)
        self._loaded_families["System Default"] = None

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

        self.scale.setValue(1.0)
        self.font_combo.setCurrentIndex(0)
        self.hinting_cb.setChecked(True)

        self.store.setValue("scale", 1.0)
        self.store.setValue("font_family", "")
        self.store.setValue("hinting_off", True)
        self.store.sync()

    def close(self):
        pass


def start_plugin():
    import substance_painter as sp

    global _DOCK, _PANEL
    _PANEL = UiScalePanel()
    _DOCK = sp.ui.add_dock_widget(_PANEL.widget)
    _DOCK.setWindowTitle("UI Font")
    _DOCK.show()

    saved_scale = float(_PANEL.store.value("scale", 1.0))
    saved_family = _PANEL.store.value("font_family", "")
    saved_hinting = _read_bool(_PANEL.store.value("hinting_off", True))
    if saved_scale != 1.0 or saved_family or not saved_hinting:
        _PANEL.apply()

    sp.logging.info("Rizum Painter UI Font plugin loaded")


def close_plugin():
    import substance_painter as sp

    global _DOCK, _PANEL
    if _PANEL is not None:
        _PANEL.close()
        _PANEL = None
    if _DOCK is not None:
        sp.ui.delete_ui_element(_DOCK)
        _DOCK = None
    sp.logging.info("Rizum Painter UI Font plugin unloaded")


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


def _read_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
