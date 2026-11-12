"""Tests for loading the bundled UI kit and saying why it could not be used."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import ui_kit_loader

ROOT = Path(__file__).resolve().parents[1]


class UiKitLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.plugin_root = Path(self.temp_dir.name)
        # The loader puts the kit's root first on sys.path and replaces the
        # loaded kit; leave both as the other tests expect them.
        saved_path = list(sys.path)
        self.addCleanup(ui_kit_loader.load_ui_kit, ROOT, {})
        self.addCleanup(sys.path.__setitem__, slice(None), saved_path)

    def _write_kit(self, source):
        kit = self.plugin_root / "rizum_ui"
        kit.mkdir()
        (kit / "__init__.py").write_text(source, encoding="utf-8")

    def test_the_bundled_kit_has_every_feature_the_panel_uses(self):
        module = ui_kit_loader.load_ui_kit(ROOT, {})

        self.assertEqual(ui_kit_loader.missing_ui_kit_features(module), ())

    def test_a_kit_without_a_required_feature_is_named_with_what_it_lacks(self):
        self._write_kit("apply_theme = None\n")

        with self.assertRaises(ImportError) as raised:
            ui_kit_loader.load_ui_kit(self.plugin_root, {})

        message = str(raised.exception)
        self.assertIn("lacks", message)
        self.assertIn("make_spin_input", message)
        self.assertNotIn("apply_theme", message)

    def test_a_kit_that_fails_to_import_is_reported_with_its_error(self):
        self._write_kit("raise RuntimeError('broken kit')\n")

        with self.assertRaises(ImportError) as raised:
            ui_kit_loader.load_ui_kit(self.plugin_root, {})

        self.assertIn("broken kit", str(raised.exception))

    def test_a_plugin_folder_without_a_kit_is_reported(self):
        with self.assertRaises(ImportError) as raised:
            ui_kit_loader.load_ui_kit(self.plugin_root, {})

        self.assertIn("no rizum_ui folder", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
