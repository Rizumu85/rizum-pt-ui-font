"""Live font-preview session for the Painter UI Font panel."""

from __future__ import annotations

from dataclasses import dataclass

_UI_SCALE_PROPERTY = "rizumUiFontScale"
_BASELINE_FONT_PROPERTY = "rizumUiFontBaseline"
# How much of a widget's own size difference from the application font
# survives a preview: 0 makes every widget the same size (0.5.0), 1 keeps
# Painter's ratios unchanged. 0.5 keeps a softened hierarchy.
_HIERARCHY_STRENGTH = 0.5
_MIN_SIZE_RATIO = 0.6
_MAX_SIZE_RATIO = 1.8


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
    """Build and apply a font state to Painter's Qt application."""

    def __init__(self, QtGui, QtWidgets, original_font, refresh_widget, refresh_panel):
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self.original_font = original_font
        self.refresh_widget = refresh_widget
        self.refresh_panel = refresh_panel
        self._applied_state = FontState()

    def build_font(self, state):
        state = FontState.from_value(state)
        font = self.QtGui.QFont(self.original_font)
        base_size = self.original_font.pointSizeF()
        if base_size <= 0:
            base_size = float(self.original_font.pointSize())
        if base_size > 0:
            font.setPointSizeF(base_size * state.scale)
        else:
            pixel_size = self.original_font.pixelSize()
            if pixel_size > 0:
                font.setPixelSize(max(1, int(round(pixel_size * state.scale))))
        if state.family:
            font.setFamily(state.family)
        if state.hinting:
            font.setHintingPreference(self.QtGui.QFont.PreferNoHinting)
        return font

    def apply_state(self, state):
        state = FontState.from_value(state)
        return self.apply_font(self.build_font(state), state)

    def restore_original(self):
        return self.apply_font(self.original_font, FontState())

    def apply_font(self, font, state):
        """Apply ``font`` to the application and every existing widget.

        Painter sets fonts on its own widgets, so QApplication.setFont alone
        does not reach them. Every widget gets ``font``, keeping only its own
        style traits, and its original font is remembered for restore.
        """
        app = self.QtWidgets.QApplication.instance()
        if app is None:
            return False
        widgets = tuple(app.allWidgets())
        # Record baselines before setFont propagates into inheriting widgets.
        baselines = [self._baseline(widget) for widget in widgets]
        _set_application_scale(app, state.scale)
        app.setFont(font)
        for widget, baseline in zip(widgets, baselines):
            widget_font = font if baseline is None else self._widget_font(font, baseline, state)
            self.refresh_widget(widget, widget_font)
        self._applied_state = state
        self.refresh_panel(font)
        return True

    def _baseline(self, widget):
        """Return the widget's font as it would be with no preview applied."""
        try:
            stored = widget.property(_BASELINE_FONT_PROPERTY)
        except Exception:
            return None
        if isinstance(stored, self.QtGui.QFont):
            return stored
        try:
            baseline = self.QtGui.QFont(widget.font())
        except Exception:
            return None
        # A widget first seen while a preview is active already carries the
        # preview font; undo it so the next apply does not compound it.
        applied = self._applied_state
        if applied.scale and applied.scale != 1.0:
            _scale_font(baseline, 1.0 / applied.scale)
        if applied.family and baseline.family() == applied.family:
            baseline.setFamily(self.original_font.family())
        try:
            widget.setProperty(_BASELINE_FONT_PROPERTY, baseline)
        except Exception:
            return None
        return baseline

    def _widget_font(self, font, baseline, state):
        """Return ``font`` carrying the widget's own style traits.

        Family and hinting come from the applied font, so the whole UI uses
        the chosen font. Size starts from the applied font and keeps a
        softened share of the widget's own size difference, so headers stay
        larger and captions smaller without small text staying tiny. Weight,
        italic, decoration, capitalization, spacing, and a monospace family
        are kept from the widget's own font.
        """
        if state.is_default():
            return self.QtGui.QFont(baseline)
        widget_font = self.QtGui.QFont(font)
        _scale_font(widget_font, self._size_ratio(baseline) ** _HIERARCHY_STRENGTH)
        widget_font.setWeight(baseline.weight())
        widget_font.setItalic(baseline.italic())
        widget_font.setUnderline(baseline.underline())
        widget_font.setStrikeOut(baseline.strikeOut())
        widget_font.setCapitalization(baseline.capitalization())
        widget_font.setLetterSpacing(baseline.letterSpacingType(), baseline.letterSpacing())
        widget_font.setWordSpacing(baseline.wordSpacing())
        if self._is_monospace(baseline):
            widget_font.setFamily(baseline.family())
        return widget_font

    def _size_ratio(self, baseline):
        """Widget size relative to the application font, in points."""
        widget_size = self._point_size(baseline)
        app_size = self._point_size(self.original_font)
        if widget_size <= 0 or app_size <= 0:
            return 1.0
        return min(_MAX_SIZE_RATIO, max(_MIN_SIZE_RATIO, widget_size / app_size))

    def _point_size(self, font):
        # Pixel-sized fonts have no point size; ask Qt what they resolve to.
        size = font.pointSizeF()
        if size > 0:
            return size
        try:
            return self.QtGui.QFontInfo(font).pointSizeF()
        except Exception:
            return 0.0

    def _is_monospace(self, font):
        QFont = self.QtGui.QFont
        try:
            if font.fixedPitch() or font.styleHint() in (
                QFont.StyleHint.Monospace,
                QFont.StyleHint.TypeWriter,
                QFont.StyleHint.Courier,
            ):
                return True
            return bool(self.QtGui.QFontInfo(font).fixedPitch())
        except Exception:
            return False


def _scale_font(font, scale):
    if scale == 1.0:
        return
    size = font.pointSizeF()
    if size > 0:
        font.setPointSizeF(size * scale)
        return
    pixel_size = font.pixelSize()
    if pixel_size > 0:
        font.setPixelSize(max(1, int(round(pixel_size * scale))))


def _set_application_scale(app, scale):
    try:
        app.setProperty(_UI_SCALE_PROPERTY, float(scale))
    except Exception:
        pass


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
