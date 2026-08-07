from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtTest, QtWidgets

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


if __name__ == "__main__":
    unittest.main()
