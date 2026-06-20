"""Rizum Painter UI Font Helper.

This plugin is intentionally separate from the PT-to-PS bridge. It only
experiments with Painter's Qt UI font settings in the current session.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

try:
    from ui_kit_loader import load_ui_kit as _load_bundled_ui_kit
except Exception:
    _load_bundled_ui_kit = None

_PANEL = None
_DOCK = None
PLUGIN_VERSION = "0.4.0"
_MIN_DOCK_WIDTH = 250
_DEFAULT_DOCK_WIDTH = _MIN_DOCK_WIDTH
_DEFAULT_DOCK_HEIGHT = 184
_RESET_BUTTON_WIDTH = 68
_SAVE_BUTTON_WIDTH = 72
_HINT_ROW_MIN_WIDTH = 108
_HINT_ROW_MAX_WIDTH = 184
_DEFAULT_LANGUAGE = "en"
_I18N_DIR = _PLUGIN_ROOT / "i18n"
_PAINTER_LOCALE_PATTERN = re.compile(r"Using locale:\s*([A-Za-z]{2}(?:[_-][A-Za-z]{2})?)")
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
    "save": "Save",
    "saved": "Saved",
    "undo": "Undo changes",
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


def _resolve_language(*candidates):
    for candidate in candidates:
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


def _read_painter_log_language():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return ""

    log_path = (
        Path(local_app_data)
        / "Adobe"
        / "Adobe Substance 3D Painter"
        / "log.txt"
    )
    try:
        with log_path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(size - 131072, 0))
            text = handle.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

    matches = _PAINTER_LOCALE_PATTERN.findall(text)
    return matches[-1] if matches else ""


def _load_ui_kit():
    """Return the compact UI kit used by the panel."""
    if _load_bundled_ui_kit is None:
        return None
    try:
        return _load_bundled_ui_kit(_PLUGIN_ROOT)
    except Exception:
        return None


def _load_prettier_ui():
    """Compatibility alias for older local smoke tests."""
    return _load_ui_kit()
    return None


class UiScalePanel:
    def __init__(self):
        from PySide6 import QtCore, QtGui, QtWidgets

        self.QtCore = QtCore
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self.ui = _load_ui_kit()
        self.store = QtCore.QSettings("Rizum", "PainterUiFont")
        self.language = _resolve_language(_read_painter_log_language())
        self.original_font = QtWidgets.QApplication.font()
        self.font_dir = Path(__file__).resolve().parent / "fonts"
        self._loaded_families = {}
        self._base_panel_stylesheet = ""
        self._styled_rows = {}
        # Live-preview history stack. Each live change (size/font/hinting) is
        # recorded here; "undo" reverts to the previous live state. "save" is
        # the only action that persists to QSettings; closing without saving
        # discards unsaved live changes.
        self._live_history = []
        self._live_index = -1

        self.widget = QtWidgets.QWidget()
        self.widget.setWindowTitle(self._tr("panel_title"))
        if self.ui is not None:
            self._build_prettier_layout()
        else:
            self._build_fallback_layout()

        self._populate_fonts()
        self._refresh_compact_metrics()
        self._seed_history()
        self._connect_live_sync()

    def _build_prettier_layout(self):
        QtCore = self.QtCore
        QtWidgets = self.QtWidgets

        self.ui.apply_theme(self.widget, mode="overlay")
        self.ui.apply_compact_dock_surface(self.widget)
        layout = self.ui.make_compact_dock_layout(self.widget)

        card = self.ui.make_compact_dock_card()
        card_layout = card.layout()
        self._card_layout = card_layout
        card_layout.setContentsMargins(0, 0, 0, 8)
        layout.addWidget(card)

        main = QtWidgets.QWidget()
        main.setObjectName("RizumTransparent")
        main_layout = QtWidgets.QVBoxLayout(main)
        self._main_layout = main_layout
        main_layout.setContentsMargins(12, 12, 12, 6)
        main_layout.setSpacing(10)
        label_width = self._label_width()

        self.scale = self.ui.make_spin_input(float(self.store.value("scale", 1.0)))
        self._styled_rows["size"] = self.ui.make_field_row(
            self._tr("size"),
            self.scale,
            label_width=label_width,
            gap=8,
            width=self._scale_control_width(),
        )
        main_layout.addWidget(self._styled_rows["size"])

        self.font_combo = self.ui.make_combo_input()
        if hasattr(self.font_combo, "setFitToContents"):
            self.font_combo.setFitToContents(False)
        self.font_combo.setMinimumWidth(54)
        self._styled_rows["font"] = self.ui.make_field_row(
            self._tr("font"),
            self.font_combo,
            label_width=label_width,
            gap=8,
        )
        main_layout.addWidget(self._styled_rows["font"])

        tool_row = QtWidgets.QHBoxLayout()
        self.tool_row = tool_row
        # Right margin aligns hint checkbox with the combo input's right edge
        # (combo has a fixed width + stretch in its field row, so its right
        # edge doesn't reach the panel edge; match that offset here).
        tool_row.setContentsMargins(label_width + 8, -6, 0, 2)
        tool_row.setSpacing(0)

        icon_group = QtWidgets.QHBoxLayout()
        icon_group.setContentsMargins(0, 0, 0, 0)
        icon_group.setSpacing(2)
        self.browse_btn = self.ui.make_icon_button("folder.svg", self._tr("open_fonts_folder"))
        self.browse_btn.setProperty("accent", True)
        self.browse_btn.clicked.connect(self._open_fonts_dir)
        self.refresh_btn = self.ui.make_icon_button("refresh.svg", self._tr("refresh_font_list"))
        self.refresh_btn.setProperty("accent", True)
        self.refresh_btn.clicked.connect(self._populate_fonts)
        icon_group.addWidget(self.browse_btn)
        icon_group.addWidget(self.refresh_btn)
        tool_row.addLayout(icon_group)
        tool_row.addStretch(1)

        self.hinting_cb = self.ui.make_mock_checkbox()
        self.hinting_cb.setChecked(_read_bool(self.store.value("hinting_off", True)))
        self.hint_widget = self.ui.make_inline_checkbox_row(
            self._tr("no_hinting"),
            self.hinting_cb,
            minimum=_HINT_ROW_MIN_WIDTH,
            maximum=_HINT_ROW_MAX_WIDTH,
        )
        # Align the checkbox with the combo's chevron: the combo container has
        # 8px right margin + ~7px half-chevron offset, while the hint row has
        # 8px right margin. Add the difference so the checkbox sits at the same
        # x as the chevron.
        self.hint_widget.layout().setContentsMargins(8, 4, 8 + 7, 4)
        tool_row.addWidget(self.hint_widget)
        main_layout.addLayout(tool_row)

        card_layout.addWidget(main)
        card_layout.addStretch(1)

        footer = QtWidgets.QWidget()
        footer.setObjectName("RizumTransparent")
        self._footer = footer
        footer.setFixedHeight(48)
        self._footer = footer
        footer_outer = QtWidgets.QVBoxLayout(footer)
        footer_outer.setContentsMargins(0, 0, 0, 0)
        footer_outer.setSpacing(0)
        footer_row = QtWidgets.QWidget()
        footer_row.setObjectName("RizumTransparent")
        footer_layout = QtWidgets.QHBoxLayout(footer_row)
        footer_layout.setContentsMargins(10, 0, 10, 0)
        footer_layout.setSpacing(8)
        footer_layout.addStretch(1)
        self._save_feedback = QtWidgets.QLabel("")
        self._save_feedback.setObjectName("RizumHintLabel")
        self._save_feedback.setStyleSheet("color: #37c98b; background: transparent; border: 0;")
        self._save_feedback.setAlignment(self.QtCore.Qt.AlignmentFlag.AlignRight | self.QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._save_feedback.setFixedHeight(22)
        self._save_feedback.hide()
        footer_layout.addWidget(self._save_feedback)
        self.undo_btn = self.ui.make_icon_button("undo.svg", self._tr("undo"))
        self.undo_btn.setProperty("accent", True)
        self.undo_btn.clicked.connect(self._undo_live)
        footer_layout.addWidget(self.undo_btn)
        self.reset_btn = self.ui.ActionButton.create(self._tr("reset"), "dialog-secondary")
        self.ui.set_compact_footer_button_width(
            self.reset_btn,
            self.ui.compact_footer_button_width(
                self.reset_btn,
                minimum=_RESET_BUTTON_WIDTH,
                maximum=118,
            ),
        )
        self.reset_btn.clicked.connect(self.reset)
        self.save_btn = self.ui.ActionButton.create(self._tr("save"), "dialog-primary")
        self.ui.set_compact_footer_button_width(
            self.save_btn,
            self.ui.compact_footer_button_width(
                self.save_btn,
                minimum=_SAVE_BUTTON_WIDTH,
                maximum=112,
            ),
        )
        self.save_btn.clicked.connect(self.save)
        footer_layout.addWidget(self.reset_btn)
        footer_layout.addWidget(self.save_btn)
        footer_outer.addWidget(footer_row, 1)
        card_layout.addWidget(footer)
        self._refresh_compact_metrics()
        self.widget.setMinimumWidth(max(_MIN_DOCK_WIDTH, self.widget.minimumSizeHint().width()))
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
        btn_row.addStretch(1)
        self._save_feedback = QtWidgets.QLabel("")
        self._save_feedback.setStyleSheet("color: #37c98b; background: transparent; border: 0;")
        self._save_feedback.setAlignment(self.QtCore.Qt.AlignmentFlag.AlignRight | self.QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._save_feedback.hide()
        btn_row.addWidget(self._save_feedback)
        self.undo_btn = _fallback_icon_button(
            self.QtCore,
            self.QtGui,
            QtWidgets,
            "undo.svg",
            "undo",
            self._tr("undo"),
        )
        self.undo_btn.setToolTip(self._tr("undo"))
        self.undo_btn.clicked.connect(self._undo_live)
        btn_row.addWidget(self.undo_btn)
        self.reset_btn = QtWidgets.QPushButton(self._tr("reset"))
        self.reset_btn.clicked.connect(self.reset)
        btn_row.addWidget(self.reset_btn)
        self.save_btn = QtWidgets.QPushButton(self._tr("save"))
        self.save_btn.clicked.connect(self.save)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    def _populate_fonts(self):
        self.font_combo.blockSignals(True)
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
        self.font_combo.blockSignals(False)

    def _open_fonts_dir(self):
        self.font_dir.mkdir(parents=True, exist_ok=True)
        url = self.QtCore.QUrl.fromLocalFile(str(self.font_dir))
        self.QtGui.QDesktopServices.openUrl(url)

    # --- live preview + history ------------------------------------------------

    def _current_state(self):
        try:
            scale = float(self.scale.value())
        except Exception:
            scale = 1.0
        try:
            family = self.font_combo.currentData() or ""
        except Exception:
            family = ""
        try:
            hinting = self.hinting_cb.isChecked()
        except Exception:
            hinting = True
        return {"scale": scale, "family": family, "hinting": hinting}

    def _seed_history(self):
        self._live_history = [self._current_state()]
        self._live_index = 0
        self._update_undo_enabled()

    def _record_live_state(self):
        state = self._current_state()
        if self._live_history and state == self._live_history[self._live_index]:
            return
        self._live_history = self._live_history[: self._live_index + 1]
        self._live_history.append(state)
        self._live_index = len(self._live_history) - 1
        self._update_undo_enabled()

    def _update_undo_enabled(self):
        if hasattr(self, "undo_btn"):
            try:
                self.undo_btn.setEnabled(self._live_index > 0)
            except Exception:
                pass

    def _set_controls(self, state, block=True):
        widgets = [self.scale, self.font_combo, self.hinting_cb]
        if block:
            for widget in widgets:
                try:
                    widget.blockSignals(True)
                except Exception:
                    pass
        try:
            self.scale.setValue(float(state.get("scale", 1.0)))
        except Exception:
            pass
        try:
            family = state.get("family", "") or ""
            idx = self.font_combo.findData(family) if family else 0
            if idx < 0:
                idx = 0
            self.font_combo.setCurrentIndex(idx)
        except Exception:
            pass
        try:
            self.hinting_cb.setChecked(bool(state.get("hinting", True)))
        except Exception:
            pass
        if block:
            for widget in widgets:
                try:
                    widget.blockSignals(False)
                except Exception:
                    pass

    def _connect_live_sync(self):
        # Auto-sync the UI font live as the user adjusts size/font. Hinting is
        # connected too where the widget exposes a toggled signal (fallback
        # QCheckBox); the prettier mock checkbox has no signal and is only
        # applied on save.
        try:
            self.scale.valueChanged.connect(self._apply_font)
        except Exception:
            pass
        try:
            self.font_combo.currentIndexChanged.connect(self._apply_font)
        except Exception:
            pass
        try:
            self.hinting_cb.toggled.connect(self._apply_font)
        except Exception:
            pass

    def _build_font(self, scale, font_family, hinting_off):
        font = self.QtGui.QFont(self.original_font)
        base_size = self.original_font.pointSizeF()
        if base_size <= 0:
            base_size = float(self.original_font.pointSize())
        if base_size > 0:
            font.setPointSizeF(base_size * scale)
        if font_family:
            font.setFamily(font_family)
        if hinting_off:
            font.setHintingPreference(self.QtGui.QFont.PreferNoHinting)
        return font

    def _apply_font_object(self, font):
        app = self.QtWidgets.QApplication.instance()
        if app is None:
            return
        app.setFont(font)
        for widget in app.allWidgets():
            _refresh_widget_font(widget, font)
        self._refresh_own_panel_font(font)

    def _apply_font(self):
        """Apply the current control values to the live UI without persisting."""
        state = self._current_state()
        font = self._build_font(state["scale"], state["family"], state["hinting"])
        self._apply_font_object(font)
        self._record_live_state()

    def _undo_live(self):
        """Revert the UI to the previous live-preview state (not saved state)."""
        if self._live_index <= 0:
            return
        self._live_index -= 1
        state = self._live_history[self._live_index]
        self._set_controls(state)
        font = self._build_font(state["scale"], state["family"], state["hinting"])
        self._apply_font_object(font)
        self._update_undo_enabled()

    def _revert_to_saved(self):
        """Discard unsaved live preview, restore to last saved state."""
        saved_scale = float(self.store.value("scale", 1.0))
        saved_family = self.store.value("font_family", "") or ""
        saved_hinting = _read_bool(self.store.value("hinting_off", True))
        self._set_controls(
            {"scale": saved_scale, "family": saved_family, "hinting": saved_hinting}
        )
        if saved_scale != 1.0 or saved_family or not saved_hinting:
            font = self._build_font(saved_scale, saved_family, saved_hinting)
        else:
            font = self.original_font
        self._apply_font_object(font)
        self._seed_history()

    def save(self):
        """Persist the current live state to QSettings."""
        self._apply_font()
        scale = float(self.scale.value())
        font_family = self.font_combo.currentData() or ""
        self.store.setValue("scale", scale)
        self.store.setValue("font_family", font_family)
        self.store.setValue("hinting_off", self.hinting_cb.isChecked())
        self.store.sync()
        self._show_save_feedback()

    def _show_save_feedback(self):
        """Show 'Saved' text briefly, then fade out."""
        label = getattr(self, "_save_feedback", None)
        if label is None:
            return
        QtGui = self.QtGui
        QtCore = self.QtCore
        label.setText(self._tr("saved"))
        # Use QGraphicsOpacityEffect for child widget fade (windowOpacity
        # only works on top-level windows).
        try:
            effect = QtGui.QGraphicsOpacityEffect(label)
            effect.setOpacity(1.0)
            label.setGraphicsEffect(effect)
        except Exception:
            effect = None
        label.show()
        if effect is not None:
            try:
                old_anim = getattr(self, "_save_feedback_anim", None)
                if old_anim is not None:
                    old_anim.stop()
            except Exception:
                pass
            anim = QtCore.QPropertyAnimation(effect, b"opacity", label)
            anim.setDuration(600)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            anim.finished.connect(label.hide)
            self._save_feedback_anim = anim
            QtCore.QTimer.singleShot(800, anim.start)
        else:
            QtCore.QTimer.singleShot(1400, label.hide)

    def reset(self):
        app = self.QtWidgets.QApplication.instance()
        if app is None:
            return

        self._set_controls({"scale": 1.0, "family": "", "hinting": True})
        self._apply_font_object(self.original_font)

        self._seed_history()

        self.store.setValue("scale", 1.0)
        self.store.setValue("font_family", "")
        self.store.setValue("hinting_off", True)
        self.store.sync()

    def close(self):
        self._restore_original_font()
        self._styled_rows.clear()

    def _tr(self, key):
        return _TEXT.get(self.language, _TEXT[_DEFAULT_LANGUAGE]).get(
            key, _TEXT[_DEFAULT_LANGUAGE][key]
        )

    def _font_scale(self):
        try:
            return max(0.75, float(self.scale.value()))
        except Exception:
            return 1.0

    def _label_width(self):
        if self.ui is not None:
            scale = self._font_scale()
            return self.ui.compact_label_width(
                [self._tr("size"), self._tr("font")],
                widget=self.widget,
                minimum=int(round(36 * scale)),
                maximum=int(round(116 * scale)),
                padding=14,
            )
        scale = self._font_scale()
        base = 44 if self.language in {"ja", "es"} else 28
        return int(round(base * scale))

    def _scale_control_width(self):
        if self.ui is None:
            return 66
        scale = self._font_scale()
        # Match prettierui preview's original formula (padding=78, min=120,
        # max=150) but scale all three with the font so proportions stay
        # consistent. This keeps the stepper hover margins identical to the
        # preview at scale 1.0 and scaled proportionally otherwise.
        return self.ui.compact_text_width(
            "2.00",
            widget=self.scale,
            minimum=int(round(120 * scale)),
            maximum=int(round(150 * scale)),
            padding=int(round(78 * scale)),
        )

    def _font_control_width(self):
        if self.ui is None:
            return 160

        labels = []
        try:
            labels.extend(str(item[0]) for item in self.font_combo._items)
        except Exception:
            pass
        try:
            current_text = self.font_combo.currentText()
        except Exception:
            current_text = ""
        if current_text:
            labels.append(current_text)
        if not labels:
            labels = [self._tr("system_default")]

        return max(
            self.ui.compact_text_width(
                text,
                widget=self.font_combo,
                minimum=0,
                padding=46,
            )
            for text in labels
        )

    def _apply_compact_heights(self, scale):
        """Scale row heights and layout spacing with the font so the panel
        keeps the same proportions as the default-size layout, just larger.
        Base values mirror the original fixed constants (row 32, footer 48,
        main spacing 10, margins 12/12/12/6, etc.)."""
        row_h = max(24, int(round(32 * scale)))
        footer_h = max(36, int(round(48 * scale)))
        try:
            if hasattr(self, "_main_layout"):
                self._main_layout.setContentsMargins(
                    int(round(12 * scale)),
                    int(round(12 * scale)),
                    int(round(12 * scale)),
                    int(round(6 * scale)),
                )
                self._main_layout.setSpacing(int(round(10 * scale)))
        except Exception:
            pass
        try:
            if hasattr(self, "_card_layout"):
                self._card_layout.setContentsMargins(0, 0, 0, int(round(8 * scale)))
        except Exception:
            pass
        for key in ("size", "font"):
            row = self._styled_rows.get(key)
            if row is None:
                continue
            try:
                row.setFixedHeight(row_h)
            except Exception:
                pass
            control = getattr(row, "_rizum_control", None)
            if control is not None:
                try:
                    if hasattr(control, "setCompactHeight"):
                        control.setCompactHeight(row_h)
                    else:
                        control.setFixedHeight(row_h)
                except Exception:
                    pass
        try:
            if hasattr(self, "_footer"):
                self._footer.setFixedHeight(footer_h)
        except Exception:
            pass
        # Icon buttons (folder/undo/refresh): stepper-size 32×32 frame, with
        # icon proportion (17px, ~53%) tuned for detailed SVG icons. 2px gap
        # matches stepper.
        icon_btn_size = max(21, int(round(32 * scale)))
        icon_px = max(12, int(round(17 * scale)))
        for attr in ("browse_btn", "undo_btn", "refresh_btn"):
            btn = getattr(self, attr, None)
            if btn is None:
                continue
            try:
                btn.setFixedSize(icon_btn_size, icon_btn_size)
            except Exception:
                pass
            try:
                btn.setPaintedIconSize(icon_px)
            except Exception:
                pass
        # Hint checkbox row margins scale with the font. Small right offset
        # aligns the checkbox with the combo's chevron.
        try:
            if hasattr(self, "hint_widget"):
                layout = self.hint_widget.layout()
                if layout is not None:
                    layout.setContentsMargins(
                        int(round(8 * scale)),
                        int(round(4 * scale)),
                        int(round((8 + 1) * scale)),
                        int(round(4 * scale)),
                    )
        except Exception:
            pass
        # Mock checkbox glyph scales with the font (default 14px).
        checkbox_px = max(11, int(round(14 * scale)))
        try:
            if hasattr(self, "hinting_cb") and hasattr(self.hinting_cb, "setSize"):
                self.hinting_cb.setSize(checkbox_px)
        except Exception:
            pass

    def _refresh_compact_metrics(self):
        if self.ui is None:
            return

        scale = self._font_scale()
        self._apply_compact_heights(scale)
        label_width = self._label_width()
        if hasattr(self, "tool_row"):
            self.tool_row.setContentsMargins(
                label_width + 8, int(round(-6 * scale)), 0, int(round(2 * scale))
            )
        if "size" in self._styled_rows:
            self.ui.update_compact_field_row(
                self._styled_rows["size"],
                label_width=label_width,
                control_width=self._scale_control_width(),
            )
        if "font" in self._styled_rows:
            self.ui.update_compact_field_row(
                self._styled_rows["font"],
                label_width=label_width,
            )
        if hasattr(self, "hint_widget"):
            self.ui.update_inline_checkbox_row(
                self.hint_widget,
                self._tr("no_hinting"),
                minimum=int(round(_HINT_ROW_MIN_WIDTH * scale)),
                maximum=int(round(_HINT_ROW_MAX_WIDTH * scale)),
            )
        footer_btn_h = max(20, int(round(26 * scale)))
        if hasattr(self, "reset_btn"):
            self.ui.set_compact_footer_button_width(
                self.reset_btn,
                self.ui.compact_footer_button_width(
                    self.reset_btn,
                    minimum=_RESET_BUTTON_WIDTH,
                    maximum=int(round(118 * scale)),
                ),
                height=footer_btn_h,
            )
        if hasattr(self, "save_btn"):
            self.ui.set_compact_footer_button_width(
                self.save_btn,
                self.ui.compact_footer_button_width(
                    self.save_btn,
                    minimum=_SAVE_BUTTON_WIDTH,
                    maximum=int(round(112 * scale)),
                ),
                height=footer_btn_h,
            )

        self.widget.setMinimumWidth(0)
        self.widget.setMinimumHeight(0)
        try:
            self.widget.updateGeometry()
        except Exception:
            pass
        hint_w = self.widget.minimumSizeHint().width()
        hint_h = self.widget.minimumSizeHint().height()
        min_width = max(_MIN_DOCK_WIDTH, hint_w)
        min_height = max(_DEFAULT_DOCK_HEIGHT, hint_h)
        self.widget.setMinimumWidth(min_width)
        self.widget.setMinimumHeight(min_height)
        try:
            if _DOCK is not None:
                _DOCK.setMinimumWidth(min_width)
                _DOCK.setMinimumHeight(min_height)
                if hasattr(_DOCK, "isFloating") and _DOCK.isFloating():
                    # Resize floating dock to fit content — grows when the
                    # font scales up, shrinks back when it scales down.
                    _DOCK.resize(min_width, min_height)
                    self.widget.resize(min_width, min_height)
        except Exception:
            pass

    def _refresh_own_panel_font(self, font):
        _refresh_widget_tree_font(self.widget, font)
        if _DOCK is not None:
            _refresh_widget_tree_font(_DOCK, font)
        if self.ui is not None:
            self.widget.setStyleSheet(
                self._base_panel_stylesheet + "\n" + _build_panel_font_override(font)
            )
            self._refresh_compact_metrics()

    def _restore_original_font(self):
        app = self.QtWidgets.QApplication.instance()
        if app is None:
            return
        try:
            app.setFont(self.original_font)
        except Exception:
            pass
        try:
            widgets = app.allWidgets()
        except Exception:
            widgets = []
        for widget in widgets:
            _refresh_widget_font(widget, self.original_font)


def start_plugin():
    import substance_painter as sp

    global _DOCK, _PANEL
    _PANEL = UiScalePanel()
    _DOCK = sp.ui.add_dock_widget(_PANEL.widget)
    _DOCK.setWindowTitle(_PANEL._tr("panel_title"))
    _connect_floating_resize()
    _connect_dock_visibility()
    _DOCK.show()
    _resize_floating_dock()

    saved_scale = float(_PANEL.store.value("scale", 1.0))
    saved_family = _PANEL.store.value("font_family", "")
    saved_hinting = _read_bool(_PANEL.store.value("hinting_off", True))
    if saved_scale != 1.0 or saved_family or not saved_hinting:
        _PANEL._apply_font()

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


def _connect_dock_visibility():
    """Revert unsaved live preview when the panel is closed (hidden)."""
    try:
        _DOCK.visibilityChanged.connect(_on_dock_visibility_changed)
    except Exception:
        pass


def _on_dock_visibility_changed(visible):
    if visible:
        return
    if _PANEL is not None and _is_qt_object_alive(_PANEL.widget):
        _PANEL._revert_to_saved()


def _effective_dock_width():
    if _PANEL is not None and _is_qt_object_alive(_PANEL.widget):
        try:
            return max(_DEFAULT_DOCK_WIDTH, _PANEL.widget.minimumWidth())
        except Exception:
            pass
    return _DEFAULT_DOCK_WIDTH


def _effective_dock_height():
    if _PANEL is not None and _is_qt_object_alive(_PANEL.widget):
        try:
            return max(_DEFAULT_DOCK_HEIGHT, _PANEL.widget.minimumHeight())
        except Exception:
            pass
    return _DEFAULT_DOCK_HEIGHT


def _resize_floating_dock():
    if not _is_qt_object_alive(_DOCK):
        return
    try:
        if hasattr(_DOCK, "isFloating") and not _DOCK.isFloating():
            return
    except Exception:
        pass
    width = _effective_dock_width()
    height = _effective_dock_height()
    try:
        _DOCK.resize(width, height)
    except Exception:
        pass
    try:
        if _PANEL is not None and _is_qt_object_alive(_PANEL.widget):
            _PANEL.widget.resize(width, height)
    except Exception:
        pass
    try:
        if _PANEL is not None:
            _PANEL.QtCore.QTimer.singleShot(0, _resize_floating_dock_later)
    except Exception:
        pass


def _resize_floating_dock_later():
    if not _is_qt_object_alive(_DOCK):
        return
    try:
        _DOCK.resize(_effective_dock_width(), _effective_dock_height())
    except Exception:
        pass


def _refresh_widget_font(widget, font):
    if not _is_qt_object_alive(widget):
        return
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
    if not _is_qt_object_alive(root):
        return
    _refresh_widget_font(root, font)
    try:
        from PySide6 import QtWidgets

        children = root.findChildren(QtWidgets.QWidget)
    except Exception:
        children = []
    for child in children:
        _refresh_widget_font(child, font)


def _is_qt_object_alive(obj):
    if obj is None:
        return False
    try:
        import shiboken6

        return shiboken6.isValid(obj)
    except Exception:
        try:
            obj.objectName()
        except RuntimeError:
            return False
        except Exception:
            return False
        return True


def _build_panel_font_override(font):
    family = font.family().replace('"', '\\"')
    point_size = font.pointSizeF()
    if point_size <= 0:
        point_size = float(font.pointSize())
    if point_size <= 0:
        point_size = 11.0
    label_size = point_size
    hint_size = max(7.0, point_size * 11.0 / 13.0)
    button_size = max(7.0, point_size * 12.0 / 13.0)
    return f"""
QWidget#RizumSurface,
QWidget#RizumSurface *,
QWidget#RizumCompactDockSurface,
QWidget#RizumCompactDockSurface *,
QMenu#RizumPopupMenu {{
    font-family: "{family}", Arial, sans-serif;
}}

QLabel#RizumFieldLabel,
QLabel#RizumMockText {{
    font-family: "{family}", Arial, sans-serif;
    font-size: {label_size:.2f}pt;
}}

QLabel#RizumHintLabel,
QMenu#RizumPopupMenu,
QPushButton[variant="dialog-secondary"],
QPushButton[variant="dialog-primary"] {{
    font-family: "{family}", Arial, sans-serif;
}}

QLabel#RizumHintLabel {{
    font-size: {hint_size:.2f}pt;
}}

QMenu#RizumPopupMenu,
QPushButton[variant="dialog-secondary"],
QPushButton[variant="dialog-primary"] {{
    font-size: {button_size:.2f}pt;
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
