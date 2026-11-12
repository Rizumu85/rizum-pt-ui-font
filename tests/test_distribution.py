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
            self.assertTrue((staged / "LICENSE").exists())
            # Both READMEs ship with the one image they show, nothing else
            # from assets/.
            self.assertTrue((staged / "README.zh-CN.md").exists())
            self.assertEqual(
                [path.name for path in (staged / "assets").rglob("*") if path.is_file()],
                ["hero.png"],
            )
            for name in ("tests", ".gitignore", "CONTEXT.md", "distribution.py"):
                self.assertFalse((staged / name).exists(), name)
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
            self.assertIn("rizum-pt-ui-font/plugin.json", names)
            self.assertFalse(any("__pycache__" in name for name in names))

    def test_a_shipped_readme_may_only_link_to_shipped_files(self):
        with tempfile.TemporaryDirectory() as out_dir:
            _report, staged, _zip_path = distribution.build_distribution(ROOT, out_dir)
            (staged / "assets" / "readme" / "hero.png").unlink()

            report = distribution.validate_distribution(staged, release=True)

        self.assertEqual(
            [(issue.code, issue.path) for issue in report.issues],
            [
                ("missing-path", "assets/readme/hero.png"),
                ("broken-link", "assets/readme/hero.png"),
                ("broken-link", "assets/readme/hero.png"),
            ],
        )

    def test_a_staged_folder_holds_nothing_but_shipped_files(self):
        with tempfile.TemporaryDirectory() as out_dir:
            _report, staged, _zip_path = distribution.build_distribution(ROOT, out_dir)
            (staged / "assets" / "readme" / "panel.png").write_bytes(b"")
            (staged / "CONTEXT.md").write_text("notes", encoding="utf-8")

            report = distribution.validate_distribution(staged, release=True)

        self.assertEqual(
            [(issue.code, issue.path) for issue in report.issues],
            [("dev-only-file", "CONTEXT.md"), ("dev-only-file", "assets")],
        )


if __name__ == "__main__":
    unittest.main()
