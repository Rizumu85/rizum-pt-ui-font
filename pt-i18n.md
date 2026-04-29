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

The effective approach is to read Painter's runtime log:

```text
%LOCALAPPDATA%/Adobe/Adobe Substance 3D Painter/log.txt
```

Painter writes lines like:

```text
[INFO] <Qt> "[DBG INFO][NGL Integration]" Using locale: zh_CN
```

The plugin reads the tail of `log.txt`, extracts the latest `Using locale: xx_XX`, then resolves that language against the available `i18n/*.json` files. If the locale is missing or unsupported, it falls back to English.

## Removed Failed Approaches

The following approaches were tested or considered but removed from the runtime path because they did not follow Painter's language setting reliably on the target Windows machine:

- `QtCore.QLocale().name()`
- `QtCore.QLocale.system().name()`
- A plugin-owned `QSettings("Rizum", "PainterUiFont").value("language")` override
- Environment-variable language overrides
- A local `language.txt` override file

Keeping only the Painter log path avoids hidden state and makes localization behavior match the host application.

## Pending: Text-Fit Layout

Localized strings can be longer than the English source text. The current panel uses fixed label and footer button widths, so German, French, Italian, Spanish, and Portuguese can require more space. The layout adaptation should be fixed in `rizum-pt-ui-prettier` so all compact Painter panels benefit from the same text-fit behavior.
