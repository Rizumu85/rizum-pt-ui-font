"""Tests for the standalone distribution checks and build command."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

import distribution

ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def test_source_checkout_validates(self):
        report = distribution.validate_distribution(ROOT)
        self.assertTrue(report.ok, report.format())

    def test_release_checks_reject_development_files(self):
        report = distribution.validate_distribution(ROOT, release=True)
        codes = {issue.code for issue in report.issues}
        self.assertIn("dev-only-file", codes)

    def test_build_stages_runtime_files_and_zips_them(self):
        with tempfile.TemporaryDirectory() as out_dir:
            report, staged, zip_path = distribution.build_distribution(ROOT, out_dir)

            self.assertTrue(report.ok, report.format())
            self.assertIsNotNone(zip_path)
            self.assertTrue((staged / "__init__.py").exists())
            self.assertTrue((staged / "fonts" / "MiSans-Regular.ttf").exists())
            self.assertFalse((staged / "README.zh-CN.md").exists())
            self.assertFalse((staged / "tests").exists())
            self.assertFalse((staged / "assets").exists())
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
            self.assertIn("rizum-pt-ui-font/plugin.json", names)
            self.assertFalse(any("__pycache__" in name for name in names))


if __name__ == "__main__":
    unittest.main()
