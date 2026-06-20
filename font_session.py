"""Live font-preview session for the Painter UI Font panel."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FontState:
    scale: float = 1.0
    family: str = ""
    hinting: bool = True

    @classmethod
    def from_value(cls, value):
        if isinstance(value, cls):
            return value
        value = value or {}
        return cls(
            scale=_coerce_float(value.get("scale", 1.0), 1.0),
            family=str(value.get("family", "") or ""),
            hinting=_coerce_bool(value.get("hinting", True)),
        )

    def is_default(self):
        return self.scale == 1.0 and not self.family and self.hinting


class QSettingsFontSettings:
    """QSettings Adapter for saved font-session state."""

    def __init__(self, settings):
        self.settings = settings

    def load(self):
        return FontState(
            scale=_coerce_float(self.settings.value("scale", 1.0), 1.0),
            family=str(self.settings.value("font_family", "") or ""),
            hinting=_coerce_bool(self.settings.value("hinting_off", True)),
        )

    def save(self, state):
        state = FontState.from_value(state)
        self.settings.setValue("scale", state.scale)
        self.settings.setValue("font_family", state.family)
        self.settings.setValue("hinting_off", state.hinting)
        self.settings.sync()


class QtFontApplier:
    """Qt Adapter that builds and applies a FontState to QApplication."""

    def __init__(self, QtGui, QtWidgets, original_font, refresh_widget, refresh_panel):
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self.original_font = original_font
        self.refresh_widget = refresh_widget
        self.refresh_panel = refresh_panel

    def build_font(self, state):
        state = FontState.from_value(state)
        font = self.QtGui.QFont(self.original_font)
        base_size = self.original_font.pointSizeF()
        if base_size <= 0:
            base_size = float(self.original_font.pointSize())
        if base_size > 0:
            font.setPointSizeF(base_size * state.scale)
        if state.family:
            font.setFamily(state.family)
        if state.hinting:
            font.setHintingPreference(self.QtGui.QFont.PreferNoHinting)
        return font

    def apply_state(self, state):
        return self.apply_font(self.build_font(state))

    def restore_original(self):
        return self.apply_font(self.original_font)

    def apply_font(self, font):
        app = self.QtWidgets.QApplication.instance()
        if app is None:
            return False
        app.setFont(font)
        for widget in app.allWidgets():
            self.refresh_widget(widget, font)
        self.refresh_panel(font)
        return True


class FontSession:
    """Owns live-preview history, persistence, and font application."""

    def __init__(self, settings, applier):
        self.settings = settings
        self.applier = applier
        self._history = []
        self._index = -1

    @property
    def can_undo(self):
        return self._index > 0

    def saved_state(self):
        return self.settings.load()

    def saved_needs_apply(self):
        return not self.saved_state().is_default()

    def seed(self, state):
        state = FontState.from_value(state)
        self._history = [state]
        self._index = 0
        return state

    def preview(self, state):
        state = FontState.from_value(state)
        self.applier.apply_state(state)
        self._record(state)
        return state

    def undo(self, before_apply=None):
        if not self.can_undo:
            return None
        self._index -= 1
        state = self._history[self._index]
        if before_apply is not None:
            before_apply(state)
        self.applier.apply_state(state)
        return state

    def revert_to_saved(self):
        return self.revert_to(self.saved_state())

    def revert_to(self, state, before_apply=None):
        state = FontState.from_value(state)
        if before_apply is not None:
            before_apply(state)
        self._apply_saved_or_original(state)
        self.seed(state)
        return state

    def save(self, state):
        state = self.preview(state)
        self.settings.save(state)
        return state

    def reset(self, before_apply=None):
        state = FontState()
        if before_apply is not None:
            before_apply(state)
        self.applier.restore_original()
        self.settings.save(state)
        self.seed(state)
        return state

    def restore_original(self):
        return self.applier.restore_original()

    def _record(self, state):
        if self._history and self._history[self._index] == state:
            return
        self._history = self._history[: self._index + 1]
        self._history.append(state)
        self._index = len(self._history) - 1

    def _apply_saved_or_original(self, state):
        if state.is_default():
            self.applier.restore_original()
        else:
            self.applier.apply_state(state)


def _coerce_float(value, default):
    try:
        return float(value)
    except Exception:
        return float(default)


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
