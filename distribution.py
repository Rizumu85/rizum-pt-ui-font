"""Validate standalone distribution invariants for this plugin."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED_PATHS = (
    ".gitignore",
    "distribution.py",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "__init__.py",
    "plugin.json",
    "fonts",
    "i18n",
    "icons",
    "rizum_ui",
    "rizum_ui_vendor_manifest.json",
    "ui_kit_loader.py",
)

ICON_PATTERN = re.compile(r"""["']([^"']+\.svg)["']""")
PLUGIN_VERSION_PATTERN = re.compile(r"""^PLUGIN_VERSION\s*=\s*["']([^"']+)["']""", re.MULTILINE)


@dataclass(frozen=True)
class DistributionIssue:
    code: str
    message: str
    path: str = ""

    def format(self):
        suffix = f" ({self.path})" if self.path else ""
        return f"[{self.code}] {self.message}{suffix}"


@dataclass(frozen=True)
class DistributionReport:
    root: Path
    issues: tuple[DistributionIssue, ...]

    @property
    def ok(self):
        return not self.issues

    def format(self):
        if self.ok:
            return f"OK: standalone distribution is complete at {self.root}"
        lines = [f"FAILED: standalone distribution has {len(self.issues)} issue(s) at {self.root}"]
        lines.extend(f"- {issue.format()}" for issue in self.issues)
        return "\n".join(lines)


class FilesystemAdapter:
    """Filesystem Adapter used by distribution validation."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def path(self, relative):
        return self.root / relative

    def exists(self, relative):
        return self.path(relative).exists()

    def read_text(self, relative):
        return self.path(relative).read_text(encoding="utf-8")

    def read_json(self, relative):
        return json.loads(self.read_text(relative))

    def iter_files(self):
        return (path for path in self.root.rglob("*") if path.is_file())


def validate_distribution(root=None, fs=None):
    """Return a report for the plugin's standalone distribution invariants."""
    root = Path(root or Path(__file__).resolve().parent).resolve()
    fs = FilesystemAdapter(root) if fs is None else fs
    issues = []

    _check_required_paths(fs, issues)
    _check_version_sync(fs, issues)
    _check_i18n_catalogs(fs, issues)
    _check_vendor_manifest(fs, issues)
    _check_referenced_icons(fs, issues)
    _check_misans_notice(fs, issues)
    _check_release_hygiene(fs, issues)

    return DistributionReport(root=root, issues=tuple(issues))


def _check_required_paths(fs, issues):
    for relative in REQUIRED_PATHS:
        if not fs.exists(relative):
            issues.append(DistributionIssue("missing-path", "Required distribution path is missing", relative))


def _check_version_sync(fs, issues):
    try:
        plugin_json = fs.read_json("plugin.json")
    except Exception as exc:
        issues.append(DistributionIssue("plugin-json", f"Cannot read plugin.json: {exc}", "plugin.json"))
        return

    try:
        init_text = fs.read_text("__init__.py")
    except Exception as exc:
        issues.append(DistributionIssue("plugin-version", f"Cannot read __init__.py: {exc}", "__init__.py"))
        return

    match = PLUGIN_VERSION_PATTERN.search(init_text)
    if not match:
        issues.append(DistributionIssue("plugin-version", "PLUGIN_VERSION is missing", "__init__.py"))
        return

    code_version = match.group(1)
    metadata_version = str(plugin_json.get("version", ""))
    if code_version != metadata_version:
        issues.append(
            DistributionIssue(
                "version-mismatch",
                f"PLUGIN_VERSION {code_version} does not match plugin.json {metadata_version}",
                "plugin.json",
            )
        )


def _check_i18n_catalogs(fs, issues):
    try:
        en_catalog = fs.read_json("i18n/en.json")
    except Exception as exc:
        issues.append(DistributionIssue("i18n", f"Cannot read English catalog: {exc}", "i18n/en.json"))
        return

    expected = set(en_catalog)
    i18n_dir = fs.path("i18n")
    for path in sorted(i18n_dir.glob("*.json")):
        try:
            catalog = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(DistributionIssue("i18n", f"Cannot read catalog: {exc}", str(path.relative_to(fs.root))))
            continue
        keys = set(catalog)
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        if missing:
            issues.append(DistributionIssue("i18n-missing", f"Missing keys: {', '.join(missing)}", str(path.relative_to(fs.root))))
        if extra:
            issues.append(DistributionIssue("i18n-extra", f"Extra keys: {', '.join(extra)}", str(path.relative_to(fs.root))))


def _check_vendor_manifest(fs, issues):
    try:
        manifest = fs.read_json("rizum_ui_vendor_manifest.json")
    except Exception as exc:
        issues.append(DistributionIssue("vendor-manifest", f"Cannot read vendor manifest: {exc}", "rizum_ui_vendor_manifest.json"))
        return

    for root in ("rizum_ui", "icons"):
        if root not in manifest.get("managed_roots", []):
            issues.append(DistributionIssue("vendor-root", "Managed root is missing from manifest", root))

    for relative in manifest.get("files", []):
        if not fs.exists(relative):
            issues.append(DistributionIssue("vendor-file", "Manifest file is missing", relative))

    if not manifest.get("source_git_head"):
        issues.append(DistributionIssue("vendor-source", "Manifest is missing source_git_head", "rizum_ui_vendor_manifest.json"))
    if manifest.get("source_git_status"):
        issues.append(DistributionIssue("vendor-source", "Manifest source_git_status is not clean", "rizum_ui_vendor_manifest.json"))


def _check_referenced_icons(fs, issues):
    try:
        init_text = fs.read_text("__init__.py")
    except Exception:
        return

    for icon_name in sorted(set(ICON_PATTERN.findall(init_text))):
        if icon_name.startswith("icons/"):
            relative = icon_name
        else:
            relative = f"icons/{icon_name}"
        if not fs.exists(relative):
            issues.append(DistributionIssue("missing-icon", "Referenced icon is missing", relative))


def _check_misans_notice(fs, issues):
    fonts_dir = fs.path("fonts")
    has_misans = any(path.name.lower().startswith("misans") for path in fonts_dir.glob("*") if path.is_file())
    if not has_misans:
        return
    if not fs.exists("THIRD_PARTY_NOTICES.md"):
        issues.append(DistributionIssue("misans-notice", "MiSans ships without third-party notices", "THIRD_PARTY_NOTICES.md"))
        return
    notice_text = fs.read_text("THIRD_PARTY_NOTICES.md")
    if "MiSans" not in notice_text:
        issues.append(DistributionIssue("misans-notice", "Third-party notice does not mention MiSans", "THIRD_PARTY_NOTICES.md"))


def _check_release_hygiene(fs, issues):
    if fs.exists("README.zh-CN.md"):
        issues.append(DistributionIssue("stale-readme", "Standalone Chinese README should not ship", "README.zh-CN.md"))

    try:
        gitignore = fs.read_text(".gitignore")
    except Exception:
        gitignore = ""
    if "build/" not in gitignore:
        issues.append(DistributionIssue("gitignore", "build/ is not ignored", ".gitignore"))

    for path in fs.iter_files():
        relative = path.relative_to(fs.root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            issues.append(DistributionIssue("cache-file", "Python cache file should not ship", str(relative)))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parent
    report = validate_distribution(root)
    print(report.format())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
