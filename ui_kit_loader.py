"""Load the compact UI kit used by the Painter UI Font panel."""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

UI_KIT_MODULE = "rizum_ui"
SIBLING_OVERRIDE_ENV = "RIZUM_UI_FONT_USE_SIBLING_PRETTIER"

REQUIRED_UI_KIT_FEATURES = (
    "ActionButton",
    "apply_compact_dock_surface",
    "apply_theme",
    "compact_footer_button_width",
    "compact_label_width",
    "compact_text_width",
    "make_combo_input",
    "make_compact_dock_card",
    "make_compact_dock_layout",
    "make_field_row",
    "make_icon_button",
    "make_inline_checkbox_row",
    "make_mock_checkbox",
    "make_spin_input",
    "set_compact_footer_button_width",
    "update_compact_field_row",
    "update_inline_checkbox_row",
)


@dataclass(frozen=True)
class UiKitCandidate:
    root: Path
    reason: str


def load_ui_kit(plugin_root, env=None):
    """Load the bundled UI kit, with an opt-in sibling source override."""
    env = os.environ if env is None else env
    plugin_root = Path(plugin_root).resolve()

    for candidate in candidate_roots(plugin_root, env):
        if not (candidate.root / UI_KIT_MODULE).exists():
            continue
        _prefer_root(candidate.root)
        _clear_loaded_ui_kit()
        try:
            module = importlib.import_module(UI_KIT_MODULE)
        except Exception:
            continue
        if missing_ui_kit_features(module):
            continue
        return module
    return None


def candidate_roots(plugin_root, env=None):
    """Return UI-kit roots in load order."""
    env = os.environ if env is None else env
    plugin_root = Path(plugin_root).resolve()
    roots = []
    if _truthy(env.get(SIBLING_OVERRIDE_ENV, "")):
        roots.append(UiKitCandidate(plugin_root.parent / "rizum-pt-ui-prettier", "sibling-dev"))
    roots.append(UiKitCandidate(plugin_root, "bundled"))
    return roots


def missing_ui_kit_features(module):
    """Return required compact UI features absent from a loaded module."""
    return tuple(name for name in REQUIRED_UI_KIT_FEATURES if not hasattr(module, name))


def _truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _prefer_root(root):
    root_path = str(Path(root).resolve())
    while root_path in sys.path:
        sys.path.remove(root_path)
    sys.path.insert(0, root_path)


def _clear_loaded_ui_kit():
    for module_name in list(sys.modules):
        if module_name == UI_KIT_MODULE or module_name.startswith(f"{UI_KIT_MODULE}."):
            del sys.modules[module_name]
