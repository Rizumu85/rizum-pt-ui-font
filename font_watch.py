"""Keeps the widgets Painter builds or restyles later on the live size.

Painter's style sheet gives every widget its size when the widget is
polished (``QWidget { font-size: 11px }`` and some twenty rules like it), so
a new widget comes out at Painter's size whatever its parent's font is, and
so does one Painter restyles. Family and hinting it inherits by itself.
Putting it on the live size takes its Show or FontChange event, and only a
filter on the application sees those.

A filter on the application is called for every event Painter sends: about
400 a second when nothing happens, 3,000 to 5,000 while a stroke is painted.
With the filter always installed that took 4 to 15 ms of each second on the
user's project and put this plugin over the budget for a plugin
(2026-11-13, the UI kit's ``tools/painter_perf_check.py``). The user's rule
is that a plugin has to be fast, so the filter is installed only for a
short while after something that can make Painter build widgets:

- a key other than a modifier;
- a mouse button or a wheel turn in a panel, for as long as the button is
  held (dragging a panel's edge rebuilds what no longer fits);
- in a view only a plain right click, which opens the tool's popup (348
  widgets the first time). Strokes, camera drags and brush-size drags are
  thousands of events a second, and Painter builds no widget for them;
- a window being resized, or taking the focus;
- what the plugin's entry tells it of Painter: being busy (a project
  loading, a bake, an export), reading its shelves (for some twenty seconds
  after it starts Painter rebuilds the Assets path bar several times a
  second), and a change of the layer stack. A layer a script adds is
  already built when Painter says so, so the entry also puts the Layers
  panel on the live font then;
- a font being applied, and each widget the filter itself had to change.

Measured in Painter 12.2 before choosing this (2026-11-14): with the filter
always on it changed nothing while idle, while the pointer moved over the
view or over the panels, during strokes and during camera turns; all of its
work followed a click, a key, a layer change, a project opening or Painter
reading its shelves.

Letting the style sheet do it was measured first and is not an option:
replacing Painter's sheet repolishes every widget and takes 40 s with a
project open, a sheet on the main window 17 s (4 s at startup), about 3 ms
a widget, while ``setFont`` on a widget takes 0.01 ms.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

# How long the filter stays after the last thing that woke it. Painter
# builds a panel over several turns of its event loop; each widget the
# filter changes starts the time again, so a longer build keeps it awake.
HOLD_MS = 2000
# The windows of the 3D and 2D views (Qt names a widget's window after the
# widget). A view that is missing here only costs time: the filter is awake
# during its strokes.
VIEW_WINDOWS = frozenset({"Viewer3DWindow", "TextureViewerWindow"})

_Type = QtCore.QEvent.Type
_SHOW = _Type.Show
_FONT_CHANGE = _Type.FontChange
_KEY_PRESS = _Type.KeyPress
# A key that fires a shortcut sends this and no key press.
_SHORTCUT_OVERRIDE = _Type.ShortcutOverride
_MOUSE_PRESS = _Type.MouseButtonPress
_MOUSE_RELEASE = _Type.MouseButtonRelease
_TABLET_PRESS = _Type.TabletPress
_TABLET_RELEASE = _Type.TabletRelease
_WHEEL = _Type.Wheel
_DROP = _Type.Drop
_RESIZE = _Type.Resize
_RIGHT = QtCore.Qt.MouseButton.RightButton
_NO_MODIFIER = QtCore.Qt.KeyboardModifier.NoModifier
# The hold of a mouse button that went down in a panel.
_BUTTON = "button"
# Held for every camera drag and many strokes (Alt turns the view, Shift
# draws a line, Ctrl sizes the brush): on their own they must not wake the
# filter, or it would be awake for most of the painting.
_MODIFIER_KEYS = frozenset(
    int(key)
    for key in (
        QtCore.Qt.Key.Key_Shift,
        QtCore.Qt.Key.Key_Control,
        QtCore.Qt.Key.Key_Alt,
        QtCore.Qt.Key.Key_AltGr,
        QtCore.Qt.Key.Key_Meta,
    )
)


class _WidgetEvents(QtCore.QObject):
    """The application filter: a shown or restyled widget goes on the live font.

    Show arrives after the style polished the widget and before its first
    paint, so a new panel or dialog appears already at the right size.
    FontChange catches Painter repolishing a widget back to its stylesheet
    size; the applier ignores the events it raises itself.
    """

    def __init__(self, applier, is_host_widget, changed):
        super().__init__()
        self._applier = applier
        self._is_host_widget = is_host_widget
        self._changed = changed

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind is _SHOW:
            if self._is_host_widget(obj) and self._applier.apply_to_widget(obj):
                self._changed()
        elif kind is _FONT_CHANGE:
            # Each preview step raises one FontChange per widget while the
            # applier is at work, and it ignores those: skip the ancestor
            # walk for them.
            if (
                not self._applier.applying
                and self._is_host_widget(obj)
                and self._applier.widget_font_changed(obj)
            ):
                self._changed()
        return False


class LiveFontWatch(QtCore.QObject):
    """Has the application filter installed only while Painter may build widgets.

    Its own event filter sits on the application's windows, where input
    arrives once and nothing else does (the UI kit's ``WindowInputWatch``).
    """

    def __init__(self, applier, is_host_widget, window_watch):
        super().__init__()
        self._widgets = _WidgetEvents(applier, is_host_widget, self.wake)
        self._windows = window_watch(self)
        # Owned, so it dies with the watch: nothing runs after the close.
        self._hold = QtCore.QTimer(self)
        self._hold.setSingleShot(True)
        self._hold.setInterval(HOLD_MS)
        self._hold.timeout.connect(self._rest)
        self._running = False
        self._awake = False
        # What keeps the filter past the hold time, by name.
        self._holds = set()

    @property
    def awake(self):
        return self._awake

    @property
    def resting(self):
        """Watching, with the filter off: what Painter builds now goes unseen."""
        return self._running and not self._awake

    def start(self):
        """Watch from now on; awake at first, for what the apply left behind."""
        if not self._running:
            self._running = True
            self._windows.start()
            QtGui.QGuiApplication.instance().focusWindowChanged.connect(self.wake)
        self.wake()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._windows.stop()
        self._hold.stop()
        self._holds.discard(_BUTTON)
        self._remove_filter()
        app = QtGui.QGuiApplication.instance()
        if app is not None:
            app.focusWindowChanged.disconnect(self.wake)

    @QtCore.Slot()
    def wake(self, *_arguments):
        if not self._running:
            return
        if not self._awake:
            self._awake = True
            QtWidgets.QApplication.instance().installEventFilter(self._widgets)
        self._hold.start()

    def hold(self, reason, held):
        """Keeps the filter for as long as ``reason`` lasts, and the hold time after."""
        if held:
            self._holds.add(reason)
        else:
            self._holds.discard(reason)
        self.wake()

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind is _KEY_PRESS or kind is _SHORTCUT_OVERRIDE:
            if event.key() not in _MODIFIER_KEYS:
                self.wake()
        elif kind is _MOUSE_PRESS or kind is _TABLET_PRESS:
            if watched.objectName() not in VIEW_WINDOWS:
                self.hold(_BUTTON, True)
            elif event.button() is _RIGHT and event.modifiers() == _NO_MODIFIER:
                # With Ctrl it sizes the brush, with Alt it moves the camera.
                self.wake()
        elif kind is _MOUSE_RELEASE or kind is _TABLET_RELEASE:
            # Whichever window gets it: a drag that began in a panel can end
            # over a view.
            if _BUTTON in self._holds or watched.objectName() not in VIEW_WINDOWS:
                self.hold(_BUTTON, False)
        elif kind is _WHEEL:
            if watched.objectName() not in VIEW_WINDOWS:
                self.wake()
        elif kind is _RESIZE or kind is _DROP:
            self.wake()
        return False

    def _rest(self):
        if self._holds:
            self._hold.start()
            return
        self._remove_filter()

    def _remove_filter(self):
        if not self._awake:
            return
        self._awake = False
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.removeEventFilter(self._widgets)
