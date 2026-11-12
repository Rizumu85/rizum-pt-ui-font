# Painter UI Font i18n Notes

## Working Agreement

- Rizum Guidelines are active for this project/thread until the user says otherwise.

## Scope

This file records the localization approach used by `rizum-pt-ui-font`. Fitting the panel to longer translations is done by the shared primitives of `rizum-pt-ui-prettier` (`compact_label_width`, `compact_footer_button_width`, `update_inline_checkbox_row`), which the panel calls on every font or scale change; this plugin does not own layout primitives.

## Supported Languages

The plugin ships UI strings for the language set exposed by Substance 3D Painter:

- `en`: American English / fallback
- `de`: Deutsch
- `es`: Espanol de Espana
- `fr`: Francais
- `it`: Italiano
- `ja`: Japanese
- `ko`: Korean
- `pt`: Portugues
- `zh-CN`: Simplified Chinese

Translations live in `i18n/*.json`. File names are normalized internally by replacing `-` with `_` and lowercasing, so `zh-CN.json` maps to `zh_cn` and also registers the `zh` root fallback.

## Effective Language Detection

The plugin follows the Painter Languages standard in
`rizum-pt-ui-prettier/docs/integration.md`: it reads Painter's Language
preference (`General/UI_LANGUAGE` in Painter's own settings) and, while that
preference is "Default (System Language)", the system locale. The result is
resolved against the available `i18n/*.json` files, falling back to English.

## Removed Failed Approaches

- Painter's `log.txt` (`Using locale: zh_CN`). The line is written after the
  plugins have started, so a freshly started Painter always gave English.
- `QtCore.QLocale().name()`: Painter does not set Qt's default locale to its
  UI language.
- `QtCore.QLocale.system().name()` as the only source: it ignores a language
  picked in Painter's preferences. It is kept as the second candidate only.
- A plugin-owned `QSettings("Rizum", "PainterUiFont").value("language")` override
- Environment-variable language overrides
- A local `language.txt` override file
