# Project Context

## Domain Terms

- **Painter UI Font Panel**: The Substance 3D Painter dock panel that lets users live-preview, save, reset, and undo UI font changes.
- **Font Session**: The stateful live-preview workflow behind the Painter UI Font Panel, including current font state, undo history, save/reset semantics, close-time revert, and application of font changes to Painter.
- **Bundled UI Kit**: The vendored `rizum_ui/` and `icons/` files shipped inside this plugin so the panel works without a separate `rizum-pt-ui-prettier` installation.
- **Sibling UI Kit Override**: The development-only path enabled by `RIZUM_UI_FONT_USE_SIBLING_PRETTIER=1`, which loads `../rizum-pt-ui-prettier/rizum_ui` instead of the bundled UI kit.
- **Standalone Distribution**: A plugin folder or zip that includes all runtime files needed by users: plugin entry code, metadata, fonts, i18n catalogs, icons, bundled UI kit files, and third-party notices.
- **Distribution Check**: The local validation command in `distribution.py` that verifies standalone distribution invariants before zipping or publishing.
