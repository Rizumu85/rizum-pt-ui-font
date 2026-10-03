# Painter UI Font i18n Notes

## Working Agreement

- Rizum Guidelines are active for this project/thread until the user says otherwise.

## Scope

This file records the localization approach used by `rizum-pt-ui-font`. UI resizing and text-fit behavior is intentionally left for `rizum-pt-ui-prettier`, because this plugin should not own shared layout primitives.

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

## Pending: Text-Fit Layout

Localized strings can be longer than the English source text. The current panel uses fixed label and footer button widths, so German, French, Italian, Spanish, and Portuguese can require more space. The layout adaptation should be fixed in `rizum-pt-ui-prettier` so all compact Painter panels benefit from the same text-fit behavior.
