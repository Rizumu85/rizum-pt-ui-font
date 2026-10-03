from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

import __init__ as plugin
import font_session


def _exponent(scale):
    softening = min(1.0, abs(scale - 1.0) / font_session._HIERARCHY_RAMP)
    return 1.0 - (1.0 - font_session._HIERARCHY_STRENGTH) * softening


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

    def test_preview_keeps_painters_size_hierarchy(self):
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
        # 0.8x of the base keeps its ratio to the configured strength.
        self.assertAlmostEqual(
            small.font().pointSizeF(), base_size * 1.25 * 0.8 ** _exponent(1.25), delta=0.05
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

        # Halfway through the ramp applies half of the configured softening.
        panel.session.preview(plugin.FontState(scale=1.125, family="MiSans"))
        self.app.processEvents()
        self.assertAlmostEqual(
            small.font().pointSizeF(), base_size * 1.125 * 0.8 ** _exponent(1.125), delta=0.05
        )

    def test_widgets_shown_after_the_preview_appear_on_the_live_font(self):
        # Painter builds panels after startup and after a project opens; the
        # Show event reaches them before their first paint.
        panel = self.panel
        applier = panel.session.applier
        panel.session.preview(plugin.FontState(scale=1.25, family="MiSans"))
        base_pt = panel.original_font.pointSizeF()

        # Sized by Painter's stylesheet: still at its own, unscaled size.
        styled = QtWidgets.QLabel("styled")
        self.addCleanup(styled.deleteLater)
        styled_font = QtGui.QFont(styled.font())
        styled_font.setPointSizeF(base_pt * 0.8)
        styled.setFont(styled_font)
        # Inherits the application font, which already carries the preview.
        inherited = QtWidgets.QLabel("inherited")
        self.addCleanup(inherited.deleteLater)
        window = QtWidgets.QMainWindow()
        self.addCleanup(window.deleteLater)
        menu_bar = window.menuBar()

        styled.show()
        inherited.show()
        window.show()

        expected = base_pt * 1.25 * applier._size_factor(styled_font, 1.25)
        self.assertAlmostEqual(styled.font().pointSizeF(), expected, delta=0.05)
        self.assertEqual(styled.font().family(), "MiSans")
        self.assertAlmostEqual(inherited.font().pointSizeF(), base_pt * 1.25, delta=0.05)
        menu_scale = 1.0 + 0.25 * 1.25
        self.assertAlmostEqual(menu_bar.font().pointSizeF(), base_pt * menu_scale, delta=0.05)

        # Showing again or changing nothing does not compound the scale.
        styled.hide()
        styled.show()
        self.assertAlmostEqual(styled.font().pointSizeF(), expected, delta=0.05)

        panel.session.restore_original()
        self.assertAlmostEqual(styled.font().pointSizeF(), base_pt * 0.8, delta=0.05)

    def test_host_repolish_is_corrected_without_a_loop(self):
        # Painter's QWidget { font-size } rule comes back on every repolish.
        host_qss = "QLabel { font-size: 11px; }"
        saved_qss = self.app.styleSheet()
        self.app.setStyleSheet(host_qss)
        self.addCleanup(self.app.setStyleSheet, saved_qss)
        panel = self.panel
        panel.session.preview(plugin.FontState(scale=1.25, family="MiSans"))

        label = QtWidgets.QLabel("late")
        self.addCleanup(label.deleteLater)
        label.show()
        scaled = QtGui.QFontInfo(label.font()).pixelSize()
        self.assertGreater(scaled, 11)

        label.style().unpolish(label)
        label.style().polish(label)
        self.assertEqual(QtGui.QFontInfo(label.font()).pixelSize(), scaled)

        # A font Painter sets itself becomes the new baseline, traits kept.
        bold = QtGui.QFont(label.font())
        bold.setBold(True)
        label.setFont(bold)
        self.assertTrue(label.font().bold())
        self.assertEqual(label.font().family(), "MiSans")

    def test_deliberate_fonts_from_others_are_respected(self):
        host_qss = "QLabel { font-size: 11px; }"
        saved_qss = self.app.styleSheet()
        self.app.setStyleSheet(host_qss)
        self.addCleanup(self.app.setStyleSheet, saved_qss)
        panel = self.panel
        panel.session.preview(plugin.FontState(scale=1.25, family="MiSans"))

        label = QtWidgets.QLabel("late")
        self.addCleanup(label.deleteLater)
        label.show()
        self.assertGreater(QtGui.QFontInfo(label.font()).pixelSize(), 11)

        # Another plugin sizes its own text; the watcher must not re-scale it.
        own = QtGui.QFont(label.font())
        own.setPixelSize(20)
        label.setFont(own)
        self.app.processEvents()
        self.assertEqual(QtGui.QFontInfo(label.font()).pixelSize(), 20)
        self.assertIsNone(label.property("rizumUiFontBaseline"))

    def test_sibling_plugin_panels_are_left_to_themselves(self):
        panel = self.panel
        panel.session.preview(plugin.FontState(scale=1.25, family="MiSans"))
        base_pt = panel.original_font.pointSizeF()

        root = QtWidgets.QWidget()
        root.setObjectName("RizumOtherPluginPanel")
        self.addCleanup(root.deleteLater)
        child = QtWidgets.QLabel("theirs", root)
        own = QtGui.QFont("Courier New")
        own.setPointSizeF(base_pt)
        child.setFont(own)
        dock = QtWidgets.QDockWidget("Other")
        dock.setObjectName("RizumOtherPluginDock")
        self.addCleanup(dock.deleteLater)
        title = QtWidgets.QLabel("title")
        dock.setTitleBarWidget(title)
        dock.setWidget(root)

        dock.show()

        self.assertEqual(child.font().family(), "Courier New")
        self.assertAlmostEqual(child.font().pointSizeF(), base_pt, delta=0.05)
        # The dock's own title bar is Painter's and still follows the host.
        self.assertEqual(title.font().family(), "MiSans")
        self.assertGreater(title.font().pointSizeF(), base_pt + 0.5)

    def test_closing_the_panel_stops_watching_new_widgets(self):
        panel = self.panel
        panel.session.preview(plugin.FontState(scale=1.25, family="MiSans"))
        base_pt = panel.original_font.pointSizeF()
        panel.close()

        label = QtWidgets.QLabel("after close")
        self.addCleanup(label.deleteLater)
        label.show()
        self.assertAlmostEqual(label.font().pointSizeF(), base_pt, delta=0.05)
        self.assertNotEqual(label.font().family(), "MiSans")


    def test_parameter_panel_content_keeps_painters_size(self):
        # Painter's Properties ("Tool") and Texture Set Settings docks fit
        # their narrowest width only at the default size; their content
        # changes family but not size. Their title bars still scale.
        panel = self.panel
        base_pt = panel.original_font.pointSizeF()
        dock = QtWidgets.QDockWidget("Properties - Paint")
        dock.setObjectName("Tool")
        self.addCleanup(dock.deleteLater)
        content = QtWidgets.QWidget()
        row = QtWidgets.QLabel("Position Jitter Distribution", content)
        combo = QtWidgets.QComboBox(content)
        dock.setWidget(content)
        title = QtWidgets.QLabel("PROPERTIES")
        dock.setTitleBarWidget(title)
        display = QtWidgets.QDockWidget("Display Settings")
        display.setObjectName("displaySettings")
        self.addCleanup(display.deleteLater)
        exposure = QtWidgets.QLabel("Exposure (EV)")
        display.setWidget(exposure)
        other = QtWidgets.QDockWidget("Layers")
        other.setObjectName("LayersStackView")
        self.addCleanup(other.deleteLater)
        layer = QtWidgets.QLabel("Layer 1")
        other.setWidget(layer)

        panel.session.preview(plugin.FontState(scale=1.5, family="MiSans"))
        for widget in (row, combo):
            self.assertEqual(widget.font().family(), "MiSans")
            self.assertAlmostEqual(widget.font().pointSizeF(), base_pt, delta=0.05)
        self.assertAlmostEqual(exposure.font().pointSizeF(), base_pt, delta=0.05)
        self.assertAlmostEqual(title.font().pointSizeF(), base_pt * 1.5, delta=0.05)
        self.assertAlmostEqual(layer.font().pointSizeF(), base_pt * 1.5, delta=0.05)

        # Content Painter builds later (shown after the preview) follows too.
        late = QtWidgets.QLabel("Backface culling", content)
        late.show()
        self.assertEqual(late.font().family(), "MiSans")
        self.assertAlmostEqual(late.font().pointSizeF(), base_pt, delta=0.05)

        panel.session.restore_original()
        self.assertNotEqual(row.font().family(), "MiSans")
        self.assertAlmostEqual(layer.font().pointSizeF(), base_pt, delta=0.05)


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
