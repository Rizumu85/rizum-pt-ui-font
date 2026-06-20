"""Font discovery for the Painter UI Font panel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FONT_EXTENSIONS = frozenset({".otf", ".ttf"})


@dataclass(frozen=True)
class FontOption:
    label: str
    family: str = ""

    @property
    def is_system_default(self):
        return not self.family


class QtFontDatabaseAdapter:
    """Qt font database Adapter used by FontCatalog."""

    def __init__(self, QtGui):
        self.QtGui = QtGui

    def families_for_file(self, path):
        font_id = self.QtGui.QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            return ()
        try:
            return tuple(self.QtGui.QFontDatabase.applicationFontFamilies(font_id))
        except Exception:
            return ()


class FontCatalog:
    """Discover font choices from the plugin font folder."""

    def __init__(self, font_dir, database):
        self.font_dir = Path(font_dir)
        self.database = database

    def options(self, system_label):
        seen = set()
        choices = [FontOption(str(system_label), "")]
        for family in self._discover_families():
            if family in seen:
                continue
            seen.add(family)
            choices.append(FontOption(family, family))
        return tuple(choices)

    def contains_family(self, family):
        family = str(family or "")
        if not family:
            return True
        return any(option.family == family for option in self.options(""))

    def _discover_families(self):
        if not self.font_dir.exists():
            return ()

        families = []
        for font_path in sorted(self.font_dir.iterdir()):
            if not font_path.is_file() or font_path.suffix.lower() not in FONT_EXTENSIONS:
                continue
            families.extend(str(family) for family in self.database.families_for_file(font_path))
        return tuple(families)
