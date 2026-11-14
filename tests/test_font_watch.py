"""The live font watch: awake only while Painter may be building widgets."""

from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

import font_watch
import ui_kit_loader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WindowInputWatch = ui_kit_loader.load_window_input(ROOT).WindowInputWatch
LEFT = QtCore.Qt.MouseButton.LeftButton
RIGHT = QtCore.Qt.MouseButton.RightButton
NO_MODIFIER = QtCore.Qt.KeyboardModifier.NoModifier


class FakeApplier:
    """Changes every widget it is shown, unless told the widget is fine."""

    def __init__(self):
        self.applying = False
        self.shown = []
        self.restyled = []
        self.changes = True

    def apply_to_widget(self, widget):
        self.shown.append(widget)
        return self.changes

    def widget_font_changed(self, widget):
        self.restyled.append(widget)
        return self.changes


def mouse(kind, button, modifiers=NO_MODIFIER):
    point = QtCore.QPointF(5, 5)
    held = button if kind == QtCore.QEvent.Type.MouseButtonPress else QtCore.Qt.MouseButton.NoButton
    return QtGui.QMouseEvent(kind, point, point, button, held, modifiers)


def key(kind, which=QtCore.Qt.Key.Key_B):
    return QtGui.QKeyEvent(kind, which, NO_MODIFIER)


def wheel():
    point = QtCore.QPointF(5, 5)
    return QtGui.QWheelEvent(
        point, point, QtCore.QPoint(), QtCore.QPoint(0, 120), QtCore.Qt.MouseButton.NoButton,
        NO_MODIFIER, QtCore.Qt.ScrollPhase.NoScrollPhase, False,
    )


class LiveFontWatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        hold = mock.patch.object(font_watch, "HOLD_MS", 40)
        hold.start()
        self.addCleanup(hold.stop)
        self.applier = FakeApplier()
        self.watch = font_watch.LiveFontWatch(
            self.applier, lambda obj: obj.isWidgetType(), WindowInputWatch
        )
        self.addCleanup(self.watch.stop)
        self.panel_window = QtGui.QWindow()
        self.panel_window.setObjectName("S4MainWindowWindow")
        self.view_window = QtGui.QWindow()
        self.view_window.setObjectName("Viewer3DWindow")
        for window in (self.panel_window, self.view_window):
            self.addCleanup(window.deleteLater)
        self.label = QtWidgets.QLabel("late")
        self.addCleanup(self.label.deleteLater)

    def rest(self):
        """Let the hold run out."""
        deadline = QtCore.QDeadlineTimer(1000)
        while self.watch.awake and not deadline.hasExpired():
            self.app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        self.assertFalse(self.watch.awake)

    def started_and_resting(self):
        self.watch.start()
        self.rest()
        self.applier.shown.clear()

    def send(self, window, event):
        QtCore.QCoreApplication.sendEvent(window, event)

    def show_event(self):
        QtCore.QCoreApplication.sendEvent(self.label, QtGui.QShowEvent())

    def test_nothing_is_watched_before_the_start(self):
        self.send(self.panel_window, key(QtCore.QEvent.Type.KeyPress))
        self.show_event()
        self.assertFalse(self.watch.awake)
        self.assertEqual(self.applier.shown, [])

    def test_the_start_is_awake_and_rests_after_the_hold(self):
        self.assertFalse(self.watch.resting)
        self.watch.start()
        self.assertTrue(self.watch.awake)
        self.assertFalse(self.watch.resting)
        self.show_event()
        self.assertEqual(self.applier.shown, [self.label])
        self.applier.changes = False
        self.rest()
        self.assertTrue(self.watch.resting)
        self.applier.shown.clear()
        self.show_event()
        self.assertEqual(self.applier.shown, [])

    def test_a_resting_watch_gets_no_event_of_the_application(self):
        self.started_and_resting()
        calls = []
        widgets = self.watch._widgets
        original = widgets.eventFilter
        widgets.eventFilter = lambda obj, event: calls.append(event.type()) or original(obj, event)
        QtCore.QCoreApplication.sendEvent(self.label, QtCore.QEvent(QtCore.QEvent.Type.User))
        self.assertEqual(calls, [])
        self.watch.wake()
        QtCore.QCoreApplication.sendEvent(self.label, QtCore.QEvent(QtCore.QEvent.Type.User))
        self.assertEqual(calls, [QtCore.QEvent.Type.User])

    def test_a_key_wakes_it_in_any_window(self):
        for window in (self.panel_window, self.view_window):
            for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.ShortcutOverride):
                with self.subTest(window=window.objectName(), kind=kind):
                    self.started_and_resting()
                    self.send(window, key(kind))
                    self.assertTrue(self.watch.awake)
                    self.show_event()
                    self.assertEqual(self.applier.shown, [self.label])

    def test_a_modifier_alone_does_not_wake_it(self):
        # Alt is held for every camera drag, Shift and Ctrl for many strokes.
        self.started_and_resting()
        for which in (QtCore.Qt.Key.Key_Alt, QtCore.Qt.Key.Key_Shift, QtCore.Qt.Key.Key_Control):
            for kind in (QtCore.QEvent.Type.ShortcutOverride, QtCore.QEvent.Type.KeyPress):
                self.send(self.view_window, key(kind, which))
        self.assertFalse(self.watch.awake)

    def test_a_click_in_a_panel_wakes_it(self):
        for kind in (QtCore.QEvent.Type.MouseButtonPress, QtCore.QEvent.Type.MouseButtonRelease):
            with self.subTest(kind=kind):
                self.started_and_resting()
                self.send(self.panel_window, mouse(kind, LEFT))
                self.assertTrue(self.watch.awake)
                self.send(self.panel_window, mouse(QtCore.QEvent.Type.MouseButtonRelease, LEFT))

    def test_strokes_and_camera_drags_in_a_view_do_not_wake_it(self):
        self.started_and_resting()
        alt = QtCore.Qt.KeyboardModifier.AltModifier
        control = QtCore.Qt.KeyboardModifier.ControlModifier
        drags = (
            (LEFT, NO_MODIFIER), (LEFT, alt), (QtCore.Qt.MouseButton.MiddleButton, alt),
            (RIGHT, alt), (RIGHT, control),
        )
        for button, modifiers in drags:
            self.send(self.view_window, mouse(QtCore.QEvent.Type.MouseButtonPress, button, modifiers))
            for _ in range(20):
                self.send(self.view_window, mouse(QtCore.QEvent.Type.MouseMove, button, modifiers))
            self.send(self.view_window, mouse(QtCore.QEvent.Type.MouseButtonRelease, button, modifiers))
        self.send(self.view_window, wheel())
        self.assertFalse(self.watch.awake)

    def test_a_plain_right_click_in_a_view_wakes_it(self):
        # It opens the tool's popup.
        self.started_and_resting()
        self.send(self.view_window, mouse(QtCore.QEvent.Type.MouseButtonPress, RIGHT))
        self.assertTrue(self.watch.awake)

    def test_a_drag_in_a_panel_keeps_it_awake_until_the_button_is_up(self):
        # Dragging a panel's edge rebuilds what no longer fits, for as long
        # as the drag lasts, and the drag may end over a view.
        self.started_and_resting()
        self.send(self.panel_window, mouse(QtCore.QEvent.Type.MouseButtonPress, LEFT))
        deadline = QtCore.QDeadlineTimer(200)
        while not deadline.hasExpired():
            self.app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)
        self.assertTrue(self.watch.awake)
        self.send(self.view_window, mouse(QtCore.QEvent.Type.MouseButtonRelease, LEFT))
        self.assertTrue(self.watch.awake)
        self.rest()

    def test_a_resized_window_wakes_it(self):
        self.started_and_resting()
        self.send(self.view_window, QtGui.QResizeEvent(QtCore.QSize(300, 200), QtCore.QSize(200, 200)))
        self.assertTrue(self.watch.awake)

    def test_the_pointer_moving_over_a_panel_does_not_wake_it(self):
        self.started_and_resting()
        for _ in range(20):
            self.send(self.panel_window, mouse(QtCore.QEvent.Type.MouseMove, QtCore.Qt.MouseButton.NoButton))
        self.assertFalse(self.watch.awake)

    def test_the_wheel_over_a_panel_wakes_it(self):
        self.started_and_resting()
        self.send(self.panel_window, wheel())
        self.assertTrue(self.watch.awake)

    def test_a_widget_it_changed_keeps_it_awake(self):
        self.watch.start()
        deadline = QtCore.QDeadlineTimer(200)
        while not deadline.hasExpired():
            self.show_event()
            self.app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)
        self.assertTrue(self.watch.awake)
        self.applier.changes = False
        self.rest()

    def test_it_stays_awake_while_painter_is_busy_or_reads_its_shelves(self):
        self.started_and_resting()
        self.watch.hold("busy", True)
        self.watch.hold("shelves", True)
        self.watch.hold("busy", False)
        deadline = QtCore.QDeadlineTimer(200)
        while not deadline.hasExpired():
            self.app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)
        self.assertTrue(self.watch.awake)
        self.watch.hold("shelves", False)
        self.assertTrue(self.watch.awake)
        self.rest()

    def test_a_restyled_widget_is_handed_to_the_applier(self):
        self.watch.start()
        QtCore.QCoreApplication.sendEvent(self.label, QtCore.QEvent(QtCore.QEvent.Type.FontChange))
        self.assertEqual(self.applier.restyled, [self.label])
        self.applier.restyled.clear()
        self.applier.applying = True
        QtCore.QCoreApplication.sendEvent(self.label, QtCore.QEvent(QtCore.QEvent.Type.FontChange))
        self.assertEqual(self.applier.restyled, [])

    def test_the_stop_leaves_nothing_behind(self):
        self.watch.start()
        self.watch.stop()
        self.assertFalse(self.watch.awake)
        self.assertFalse(self.watch._hold.isActive())
        self.send(self.panel_window, key(QtCore.QEvent.Type.KeyPress))
        self.watch.hold("busy", True)
        self.show_event()
        self.assertFalse(self.watch.awake)
        self.assertEqual(self.applier.shown, [])


if __name__ == "__main__":
    unittest.main()
