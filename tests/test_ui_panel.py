from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

import __init__ as plugin


class UiScalePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.settings = QtCore.QSettings(
            os.path.join(self.temp_dir.name, "settings.ini"),
            QtCore.QSettings.Format.IniFormat,
        )
        with mock.patch.object(QtCore, "QSettings", return_value=self.settings):
            self.panel = plugin.UiScalePanel()
        self.addCleanup(self._close_panel)
        self.panel.widget.show()
        self.app.processEvents()

    def _close_panel(self):
        self.panel.close()
        self.panel.widget.close()
        self.panel.widget.deleteLater()
        self.app.processEvents()

    def test_live_panel_uses_the_approved_shared_layout(self):
        panel = self.panel

        self.assertIsInstance(panel.reset_btn, panel.ui.SecondaryActionButton)
        self.assertIsInstance(panel.save_btn, panel.ui.AnimatedSaveButton)
        self.assertEqual(panel.widget.minimumWidth(), 250)
        self.assertEqual(panel._card_layout.getContentsMargins(), (0, 0, 0, 8))
        self.assertEqual(panel._main_layout.getContentsMargins(), (12, 12, 12, 6))
        self.assertEqual(panel._main_layout.spacing(), 10)
        self.assertEqual(panel.browse_btn.size(), QtCore.QSize(22, 22))
        self.assertEqual(panel.refresh_btn.size(), QtCore.QSize(22, 22))
        self.assertEqual(panel.undo_btn.size(), QtCore.QSize(32, 32))
        self.assertEqual(
            panel.hint_widget.layout().getContentsMargins(),
            (8, 4, 8, 4),
        )
        self.assertEqual(panel.hint_widget.layout().spacing(), 10)
        self.assertEqual(panel._footer.height(), 48)
        self.assertEqual(panel._footer_layout.getContentsMargins(), (10, 0, 10, 0))
        self.assertEqual(panel._footer_layout.spacing(), 8)
        self.assertEqual(panel.reset_btn.size(), QtCore.QSize(68, 26))
        self.assertEqual(panel.save_btn.size(), QtCore.QSize(72, 26))
        self.assertFalse(panel.undo_btn.isEnabled())
        self.assertFalse(panel.save_btn.isEnabled())

    def test_save_state_and_hinting_feedback_are_local_to_the_actions(self):
        panel = self.panel

        panel.scale.setValue(1.1)
        self.app.processEvents()
        self.assertTrue(panel.undo_btn.isEnabled())
        self.assertTrue(panel.save_btn.isDirty())

        QtTest.QTest.mouseClick(panel.save_btn, QtCore.Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertTrue(panel.save_btn.feedbackActive())
        self.assertFalse(panel.save_btn.isEnabled())
        self.assertEqual(float(self.settings.value("scale")), 1.1)

        was_checked = panel.hinting_cb.isChecked()
        QtTest.QTest.mouseClick(panel.hinting_cb, QtCore.Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertNotEqual(panel.hinting_cb.isChecked(), was_checked)
        self.assertTrue(panel.save_btn.isDirty())

    def test_reset_previews_defaults_without_persisting_them(self):
        panel = self.panel
        panel.scale.setValue(1.1)
        panel.save()
        panel.scale.setValue(1.2)
        self.app.processEvents()

        panel.reset()
        self.app.processEvents()

        self.assertEqual(panel.scale.value(), 1.0)
        self.assertEqual(float(self.settings.value("scale")), 1.1)
        self.assertTrue(panel.save_btn.isDirty())
        self.assertFalse(panel.undo_btn.isEnabled())

    def test_first_run_until_visibility_is_recorded(self):
        self.assertTrue(self.panel.is_first_run())
        self.assertTrue(self.panel.panel_should_start_visible())

        self.panel.save_panel_visibility(False)

        self.assertFalse(self.panel.is_first_run())
        self.assertFalse(self.panel.panel_should_start_visible())

    def test_missing_saved_font_does_not_open_dirty(self):
        self.settings.setValue("font_family", "Font That Was Deleted")
        self.settings.setValue("scale", 1.0)
        self.settings.sync()

        with mock.patch.object(QtCore, "QSettings", return_value=self.settings):
            panel = plugin.UiScalePanel()
        self.addCleanup(panel.close)

        self.assertEqual(panel.font_combo.currentText(), panel._tr("system_default"))
        self.assertFalse(panel.save_btn.isDirty())
        self.assertEqual(panel._saved_state.family, "")
        # The stored value is left alone so the font comes back once re-added.
        self.assertEqual(self.settings.value("font_family"), "Font That Was Deleted")

    def test_preview_keeps_other_widgets_own_fonts(self):
        panel = self.panel
        bold_label = QtWidgets.QLabel("bold")
        bold_font = bold_label.font()
        bold_font.setBold(True)
        bold_label.setFont(bold_font)
        self.addCleanup(bold_label.deleteLater)
        plain_label = QtWidgets.QLabel("plain")
        self.addCleanup(plain_label.deleteLater)
        base_size = self.app.font().pointSizeF()

        panel.scale.setValue(1.5)
        self.app.processEvents()
        self.assertTrue(bold_label.font().bold())
        self.assertAlmostEqual(plain_label.font().pointSizeF(), base_size * 1.5, places=2)

        panel.session.restore_original()
        self.app.processEvents()
        self.assertTrue(bold_label.font().bold())
        self.assertAlmostEqual(plain_label.font().pointSizeF(), base_size, places=2)

    def test_preview_keeps_a_softened_size_hierarchy(self):
        panel = self.panel
        small = QtWidgets.QLabel("small")
        self.addCleanup(small.deleteLater)
        small_font = QtGui.QFont(small.font())
        small_font.setPointSizeF(self.app.font().pointSizeF() * 0.8)
        small.setFont(small_font)
        mono = QtWidgets.QLabel("mono")
        self.addCleanup(mono.deleteLater)
        mono_font = QtGui.QFont("Courier New")
        mono_font.setStyleHint(QtGui.QFont.StyleHint.TypeWriter)
        mono.setFont(mono_font)
        mono_family = mono.font().family()
        caps = QtWidgets.QLabel("caps")
        self.addCleanup(caps.deleteLater)
        caps_font = QtGui.QFont(caps.font())
        caps_font.setCapitalization(QtGui.QFont.Capitalization.AllUppercase)
        caps.setFont(caps_font)
        base_size = panel.original_font.pointSizeF()

        panel.scale.setValue(1.25)
        self.app.processEvents()
        # 0.8x of the base keeps half its difference: sqrt(0.8) ~= 0.894x.
        self.assertAlmostEqual(
            small.font().pointSizeF(), base_size * 1.25 * 0.8 ** 0.5, delta=0.05
        )
        self.assertEqual(mono.font().family(), mono_family)
        self.assertEqual(
            caps.font().capitalization(), QtGui.QFont.Capitalization.AllUppercase
        )

        panel.session.restore_original()
        self.app.processEvents()
        self.assertAlmostEqual(small.font().pointSizeF(), small_font.pointSizeF(), places=2)

    def test_scale_one_keeps_painter_sizes_and_softening_ramps_in(self):
        panel = self.panel
        small = QtWidgets.QLabel("small")
        self.addCleanup(small.deleteLater)
        small_font = QtGui.QFont(small.font())
        small_font.setPointSizeF(self.app.font().pointSizeF() * 0.8)
        small.setFont(small_font)
        base_size = panel.original_font.pointSizeF()

        # Changing only the family at 1.0 must not resize Painter's text.
        panel.session.preview(plugin.FontState(scale=1.0, family="MiSans"))
        self.app.processEvents()
        self.assertAlmostEqual(small.font().pointSizeF(), base_size * 0.8, delta=0.05)

        # Halfway through the ramp keeps 0.75 of the size difference.
        panel.session.preview(plugin.FontState(scale=1.125, family="MiSans"))
        self.app.processEvents()
        self.assertAlmostEqual(
            small.font().pointSizeF(), base_size * 1.125 * 0.8 ** 0.75, delta=0.05
        )

    def test_menus_scale_ahead_of_the_rest(self):
        # The user wants menus at 1.25 while the rest of the UI is at 1.20.
        panel = self.panel
        window = QtWidgets.QMainWindow()
        self.addCleanup(window.deleteLater)
        menu_bar = window.menuBar()
        menu = menu_bar.addMenu("File")
        label = QtWidgets.QLabel("rest")
        self.addCleanup(label.deleteLater)

        panel.session.preview(plugin.FontState(scale=1.25, family="MiSans"))
        rest_at_125 = label.font().pointSizeF()
        panel.session.preview(plugin.FontState(scale=1.2, family="MiSans"))
        self.assertAlmostEqual(menu_bar.font().pointSizeF(), rest_at_125, delta=0.05)
        self.assertAlmostEqual(menu.font().pointSizeF(), rest_at_125, delta=0.05)
        self.assertLess(label.font().pointSizeF(), rest_at_125 - 0.2)

        panel.session.restore_original()
        self.assertAlmostEqual(
            menu_bar.font().pointSizeF(), label.font().pointSizeF(), delta=0.05
        )

    def test_preview_keeps_painter_dock_title_style(self):
        panel = self.panel
        dock = QtWidgets.QDockWidget("UI Font")
        self.addCleanup(dock.deleteLater)
        dock.setWidget(panel.widget)
        title = QtWidgets.QLabel("UI Font")
        title_font = QtGui.QFont(title.font())
        title_font.setBold(True)
        title_font.setCapitalization(QtGui.QFont.Capitalization.AllUppercase)
        title.setFont(title_font)
        dock.setTitleBarWidget(title)
        saved_dock = plugin._DOCK
        plugin._DOCK = dock
        self.addCleanup(setattr, plugin, "_DOCK", saved_dock)

        panel.scale.setValue(1.25)
        self.app.processEvents()

        self.assertTrue(title.font().bold())
        self.assertEqual(
            title.font().capitalization(), QtGui.QFont.Capitalization.AllUppercase
        )

    def test_preview_reaches_widgets_under_an_explicit_host_font(self):
        # Painter sets fonts on its own windows, which blocks QApplication.setFont.
        panel = self.panel
        window = QtWidgets.QWidget()
        self.addCleanup(window.deleteLater)
        window.setFont(QtGui.QFont(self.app.font()))
        child = QtWidgets.QLabel("child", window)
        base_size = window.font().pointSizeF()

        panel.scale.setValue(1.5)
        self.app.processEvents()
        self.assertAlmostEqual(window.font().pointSizeF(), base_size * 1.5, places=2)
        self.assertAlmostEqual(child.font().pointSizeF(), base_size * 1.5, places=2)

        late = QtWidgets.QLabel("late")
        self.addCleanup(late.deleteLater)
        panel.scale.setValue(1.6)
        self.app.processEvents()
        self.assertAlmostEqual(late.font().pointSizeF(), base_size * 1.6, places=2)

        panel.session.restore_original()
        self.app.processEvents()
        self.assertAlmostEqual(window.font().pointSizeF(), base_size, places=2)
        self.assertAlmostEqual(late.font().pointSizeF(), base_size, places=2)


class DockVisibilityTests(unittest.TestCase):
    """The unsaved preview must survive tab switches and only revert on a real close."""

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.settings = QtCore.QSettings(
            os.path.join(self.temp_dir.name, "settings.ini"),
            QtCore.QSettings.Format.IniFormat,
        )
        with mock.patch.object(QtCore, "QSettings", return_value=self.settings):
            self.panel = plugin.UiScalePanel()

        self.window = QtWidgets.QMainWindow()
        self.dock = QtWidgets.QDockWidget("UI Font")
        self.dock.setWidget(self.panel.widget)
        self.other = QtWidgets.QDockWidget("Other")
        self.other.setWidget(QtWidgets.QLabel("other"))
        area = QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        self.window.addDockWidget(area, self.dock)
        self.window.addDockWidget(area, self.other)
        self.window.tabifyDockWidget(self.dock, self.other)

        self._saved_globals = (
            plugin._PANEL,
            plugin._DOCK,
            plugin._STARTUP_SURFACE_READY,
            plugin._STARTUP_SURFACE_PREPARING,
            plugin._STARTUP_VISIBILITY_SETTLING,
        )
        plugin._PANEL = self.panel
        plugin._DOCK = self.dock
        plugin._STARTUP_SURFACE_READY = True
        plugin._STARTUP_SURFACE_PREPARING = False
        plugin._STARTUP_VISIBILITY_SETTLING = False
        plugin._connect_dock_visibility()

        self.window.show()
        self.dock.raise_()
        self.app.processEvents()

    def tearDown(self):
        self.panel.close()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        (
            plugin._PANEL,
            plugin._DOCK,
            plugin._STARTUP_SURFACE_READY,
            plugin._STARTUP_SURFACE_PREPARING,
            plugin._STARTUP_VISIBILITY_SETTLING,
        ) = self._saved_globals

    def test_switching_dock_tabs_keeps_the_live_preview(self):
        self.panel.scale.setValue(1.3)
        self.app.processEvents()

        self.other.raise_()
        self.app.processEvents()
        self.dock.raise_()
        self.app.processEvents()

        self.assertEqual(self.panel.scale.value(), 1.3)
        self.assertTrue(self.panel.save_btn.isDirty())
        self.assertNotEqual(self.settings.value("panel_visible"), "false")

    def test_minimizing_the_window_keeps_the_live_preview(self):
        self.panel.scale.setValue(1.3)
        self.app.processEvents()

        self.window.showMinimized()
        self.app.processEvents()
        self.window.showNormal()
        self.app.processEvents()

        self.assertEqual(self.panel.scale.value(), 1.3)
        self.assertNotEqual(self.settings.value("panel_visible"), "false")

    def test_closing_the_dock_reverts_to_saved_state(self):
        self.panel.scale.setValue(1.3)
        self.app.processEvents()

        self.dock.close()
        self.app.processEvents()

        self.assertEqual(self.panel.scale.value(), 1.0)
        self.assertFalse(self.panel.save_btn.isDirty())
        self.assertEqual(plugin._setting_bool(self.settings.value("panel_visible"), True), False)


if __name__ == "__main__":
    unittest.main()
