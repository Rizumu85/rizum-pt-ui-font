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

2. **Commit and push every session.** Every conversation's changes are
   committed and pushed to `origin` as a backup, split by concern (cleanup,
   refactor, fix, feature, docs) instead of one combined commit. This is the
   user's rule in the other Rizum plugin repositories; it was written down
   here on 2026-11-12, when the user let the agent align the rules across
   the plugins. A release (version bump, package, update manifest) is a
   separate step and waits for the user.

3. **Run the performance check before a release that touches a timer, an
   event filter, or a search of Painter's widgets.**
   `python ../rizum-pt-ui-prettier/tools/painter_perf_check.py`, from
   PowerShell or a normal terminal. It starts a temporary Painter, plays
   idle, pointer, key, camera, stroke and tool-switch scenarios and fails if
   a plugin takes more of Painter's main thread than the budget. The user's
   rule (2026-11-13): a plugin has to be fast. What a plugin costs the
   thread that paints does not show in its own panel or in a unit test; it
   showed as View Roll's rotation hitching, caused by other plugins' timers
   and event filters. The rules and the budget are in the UI kit's
   `docs/integration.md`, "Performance On Painter's Main Thread".
