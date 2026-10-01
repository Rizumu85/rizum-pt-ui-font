"""Tests for bundled font discovery."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from font_catalog import FontCatalog


class _Database:
    def __init__(self):
        self.calls = []

    def families_for_file(self, path):
        self.calls.append(Path(path).name)
        return (Path(path).stem.split("-")[0],)


class FontCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        for name in ("B-Regular.ttf", "A-Bold.otf", "A-Regular.ttf", "notes.txt"):
            (self.root / name).write_bytes(b"")
        self.database = _Database()
        self.catalog = FontCatalog(self.root, self.database)

    def test_options_start_with_system_default_and_dedupe_families(self):
        options = self.catalog.options("System Default")

        self.assertEqual([o.label for o in options], ["System Default", "A", "B"])
        self.assertTrue(options[0].is_system_default)
        self.assertEqual(self.database.calls, ["A-Bold.otf", "A-Regular.ttf", "B-Regular.ttf"])

    def test_discovery_is_cached_until_refresh(self):
        self.catalog.options("x")
        self.assertTrue(self.catalog.contains_family("A"))
        self.assertFalse(self.catalog.contains_family("Missing"))
        self.assertTrue(self.catalog.contains_family(""))
        self.assertEqual(len(self.database.calls), 3)

        (self.root / "C-Regular.ttf").write_bytes(b"")
        self.assertFalse(self.catalog.contains_family("C"))
        self.catalog.options("x", refresh=True)
        self.assertTrue(self.catalog.contains_family("C"))
        self.assertEqual(len(self.database.calls), 7)

    def test_missing_folder_yields_only_system_default(self):
        catalog = FontCatalog(self.root / "nope", self.database)
        self.assertEqual(len(catalog.options("x")), 1)


if __name__ == "__main__":
    unittest.main()
