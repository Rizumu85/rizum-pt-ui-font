# Agent Guidelines

## Project Rules

These rules come from the user.

1. **Run the close check before a release that touches Painter's
   widgets, signal connections, or the plugin's close.**
   `python ../rizum-pt-ui-prettier/tools/painter_close_check.py`, from
   PowerShell or a normal terminal. It starts a temporary Painter, closes the
   plugins and fails if one of them still holds something of Painter's. What
   is held then crashes Painter when it exits, on some exits only, and no
   unit test shows it: an exit crash shipped that way in October 2026, and
   the user asked for this check so it does not happen again. The rule behind
   it is in the UI kit's `docs/integration.md`, "Painter's Widgets And
   Painter's Exit".
