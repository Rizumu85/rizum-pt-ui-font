"""Live font-preview session for the Painter UI Font panel."""

from __future__ import annotations

from dataclasses import dataclass

_UI_SCALE_PROPERTY = "rizumUiFontScale"
_BASELINE_FONT_PROPERTY = "rizumUiFontBaseline"
_TARGET_FONT_PROPERTY = "rizumUiFontTarget"
_PENDING_FONT_PROPERTY = "rizumUiFontPending"
# How much of a widget's own size difference from the application font
# survives a preview: 0 makes every widget the same size (0.5.0), 1 keeps
# Painter's ratios unchanged. The user chose 1.0 scale to mean "Painter's
# own sizes", so the softening ramps in from scale 1.0 and reaches
# _HIERARCHY_STRENGTH once the scale is _HIERARCHY_RAMP away from 1.0.
# Set to 1.0 (no softening) because the user prefers narrow panels: Painter
# clips content that outgrows a dock, and softened captions need more width.
_HIERARCHY_STRENGTH = 1.0
_HIERARCHY_RAMP = 0.25
_MIN_SIZE_RATIO = 0.6
_MAX_SIZE_RATIO = 1.8
# The user wants the menu bar and its menus at 1.25 while the rest of the UI
# is at 1.20, so menus move 25% further from 1.0 than the chosen scale.
_MENU_SCALE_GAIN = 1.25
# Painter's parameter panels (label + control forms) are laid out so their
# narrowest width holds the default font exactly, and Painter clips content
# that outgrows a dock. Text inside these docks keeps Painter's size (the
# family still changes); lists, grids and consoles reflow, so they scale.
# Names are the docks' Qt object names (Painter 12.1).
_FIT_DOCK_NAMES = frozenset({
    "Tool",                   # Properties
    "textureSetSettings",     # Texture Set Settings
    "displaySettings",        # Display Settings
    "ShaderSettings",         # Shader settings
    "irayParametersView",     # Renderer Settings
    "CommonSettingsPanel",    # Baking: common settings
    "MeshMapsSettingsPanel",  # Baking: mesh map settings
    "ExportServicePanel",     # Export
})


@dataclass(frozen=True)
class FontState:
    scale: float = 1.0
    family: str = ""
    hinting: bool = True

    @classmethod
    def from_value(cls, value):
        if isinstance(value, cls):
            return value
        if hasattr(value, "scale") and hasattr(value, "family"):
            # A state from a reloaded copy of this module (plugin reload).
            return cls(
                scale=_coerce_float(getattr(value, "scale", 1.0), 1.0),
                family=str(getattr(value, "family", "") or ""),
                hinting=_coerce_bool(getattr(value, "hinting", True)),
            )
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
        # True while this applier is setting fonts, so the live watcher can
        # tell its own FontChange events from Painter's.
        self.applying = False
        # Runs a callable on the next event-loop turn (set by the panel).
        self.defer = None

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

    def apply_to_widget(self, widget):
        """Bring one widget onto the live state (shown after the last apply)."""
        state = self._applied_state
        if state.is_default():
            return False
        try:
            target = widget.property(_TARGET_FONT_PROPERTY)
            if isinstance(target, self.QtGui.QFont) and widget.font() == target:
                return False
        except Exception:
            return False
        baseline = self._baseline(widget)
        if baseline is None:
            return False
        self.applying = True
        try:
            self._apply_widget(widget, baseline, self._fonts_by_role(state))
        finally:
            self.applying = False
        return True

    def widget_font_changed(self, widget):
        """React to a font change on a widget this applier manages.

        A Painter repolish puts the stylesheet size back, which is the
        widget's baseline size: re-apply at once. Any other size may be a
        transient (unpolish fires before polish) or a deliberate font from
        Painter or another plugin, so that decision waits one event-loop
        turn; a deliberate font is then respected until the next full
        apply re-reads it as the new baseline.
        """
        if self.applying:
            return False
        QFont = self.QtGui.QFont
        try:
            current = widget.font()
            target = widget.property(_TARGET_FONT_PROPERTY)
            baseline = widget.property(_BASELINE_FONT_PROPERTY)
        except Exception:
            return False
        if not isinstance(baseline, QFont):
            return False
        if isinstance(target, QFont) and _same_size(current, target):
            return False
        if _same_size(current, baseline):
            try:
                widget.setProperty(_TARGET_FONT_PROPERTY, None)
            except Exception:
                return False
            return self.apply_to_widget(widget)
        if self.defer is None:
            return False
        try:
            if widget.property(_PENDING_FONT_PROPERTY):
                return False
            widget.setProperty(_PENDING_FONT_PROPERTY, True)
        except Exception:
            return False
        self.defer(lambda: self._settle_foreign_font(widget))
        return False

    def _settle_foreign_font(self, widget):
        QFont = self.QtGui.QFont
        try:
            widget.setProperty(_PENDING_FONT_PROPERTY, None)
            current = widget.font()
            target = widget.property(_TARGET_FONT_PROPERTY)
            baseline = widget.property(_BASELINE_FONT_PROPERTY)
        except Exception:
            return
        if isinstance(target, QFont) and _same_size(current, target):
            return
        if isinstance(baseline, QFont) and _same_size(current, baseline):
            self.apply_to_widget(widget)
            return
        # Deliberate: forget our record so the next full apply starts from it.
        try:
            widget.setProperty(_BASELINE_FONT_PROPERTY, None)
            widget.setProperty(_TARGET_FONT_PROPERTY, None)
        except Exception:
            pass

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
        self.applying = True
        try:
            app.setFont(font)
            fonts = self._fonts_by_role(state, font)
            for widget, baseline in zip(widgets, baselines):
                if baseline is None:
                    self.refresh_widget(widget, fonts[self._role(widget)][1])
                else:
                    self._apply_widget(widget, baseline, fonts)
            self._applied_state = state
            self.refresh_panel(font)
        finally:
            self.applying = False
        return True

    def _fonts_by_role(self, state, font=None):
        """(state, font) for each widget role under the applied ``state``."""
        if font is None:
            font = self.build_font(state)
        menu_state = _menu_state(state)
        fit_state = FontState(scale=1.0, family=state.family, hinting=state.hinting)
        return {
            "menu": (menu_state, self.build_font(menu_state)),
            "fit": (fit_state, self.build_font(fit_state)),
            "text": (state, font),
        }

    def _role(self, widget):
        if self._is_menu(widget):
            return "menu"
        if self._in_fit_dock(widget):
            return "fit"
        return "text"

    def _in_fit_dock(self, widget):
        """True for content (not the title bar) of a parameter-panel dock."""
        QDockWidget = getattr(self.QtWidgets, "QDockWidget", None)
        if not isinstance(QDockWidget, type):
            return False
        node = widget
        try:
            for _ in range(32):
                parent = node.parent()
                if parent is None:
                    return False
                if isinstance(parent, QDockWidget):
                    return parent.objectName() in _FIT_DOCK_NAMES and node is parent.widget()
                node = parent
        except Exception:
            return False
        return False

    def _apply_widget(self, widget, baseline, fonts):
        state, font = fonts[self._role(widget)]
        widget_font = self._widget_font(font, baseline, state)
        try:
            widget.setProperty(_TARGET_FONT_PROPERTY, self.QtGui.QFont(widget_font))
        except Exception:
            pass
        self.refresh_widget(widget, widget_font)

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
        # A widget first seen while a preview is active may inherit the
        # preview font; undo that so the next apply does not compound it.
        # Widgets sized by Painter's stylesheet are still at their own size.
        # (Menus included: a new menu inherits the plain application font.)
        applied = self._applied_state
        if applied.scale and applied.scale != 1.0 and self._inherits_applied(baseline, applied):
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
        the chosen font. Size starts from the applied font and keeps the
        widget's own size difference, softened as the scale moves away from
        1.0 so small text does not stay tiny. Weight,
        italic, decoration, capitalization, spacing, and a monospace family
        are kept from the widget's own font.
        """
        if state.is_default():
            return self.QtGui.QFont(baseline)
        widget_font = self.QtGui.QFont(font)
        _scale_font(widget_font, self._size_factor(baseline, state.scale))
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

    def _size_factor(self, baseline, scale):
        ratio = self._size_ratio(baseline)
        if ratio is None:
            return 1.0
        softening = min(1.0, abs(scale - 1.0) / _HIERARCHY_RAMP)
        exponent = 1.0 - (1.0 - _HIERARCHY_STRENGTH) * softening
        # Clamp only as far as softening applies, so scale 1.0 is exact.
        clamped = min(_MAX_SIZE_RATIO, max(_MIN_SIZE_RATIO, ratio))
        ratio += (clamped - ratio) * softening
        return ratio ** exponent

    def _size_ratio(self, baseline):
        """Widget size relative to the application font, in points."""
        widget_size = self._point_size(baseline)
        app_size = self._point_size(self.original_font)
        if widget_size <= 0 or app_size <= 0:
            return None
        return widget_size / app_size

    def _point_size(self, font):
        # Pixel-sized fonts have no point size; ask Qt what they resolve to.
        size = font.pointSizeF()
        if size > 0:
            return size
        try:
            return self.QtGui.QFontInfo(font).pointSizeF()
        except Exception:
            return 0.0

    def _inherits_applied(self, font, state):
        applied_size = self._point_size(self.build_font(state))
        return abs(self._point_size(font) - applied_size) < 0.05

    def _is_menu(self, widget):
        types = tuple(
            cls for cls in (
                getattr(self.QtWidgets, "QMenuBar", None),
                getattr(self.QtWidgets, "QMenu", None),
            ) if isinstance(cls, type)
        )
        return bool(types) and isinstance(widget, types)

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


def _same_size(font, other):
    if font.pixelSize() > 0 or other.pixelSize() > 0:
        return font.pixelSize() == other.pixelSize()
    return abs(font.pointSizeF() - other.pointSizeF()) < 0.05


def _menu_state(state):
    """Menus grow faster than the rest of the UI (user preference)."""
    scale = 1.0 + (state.scale - 1.0) * _MENU_SCALE_GAIN
    return FontState(scale=scale, family=state.family, hinting=state.hinting)


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
