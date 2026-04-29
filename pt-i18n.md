# Painter UI Font i18n Notes

## Working Agreement

- Rizum Guidelines are active for this project/thread until the user says otherwise.

## Scope

This file records the localization approach used by `rizum-pt-ui-font`. UI resizing and text-fit behavior is intentionally left for `rizum-pt-ui-prettier`, because this plugin should not own shared layout primitives.

## Supported Languages

The plugin currently ships UI strings for the language set exposed by Substance 3D Painter:

- `en`: American English / fallback
- `de`: Deutsch
- `es`: Español de España
- `fr`: Français
- `it`: Italiano
- `ja`: 日本語
- `ko`: 한국어
- `pt`: Português
- `zh-CN`: 简体中文

Translations live in `i18n/*.json`. File names are normalized internally by replacing `-` with `_` and lowercasing, so `zh-CN.json` maps to `zh_cn` and also registers the `zh` root fallback.

## Language Detection

Qt locale APIs did not reliably follow the Painter language setting on the target Windows machine. The working detection stack is:

1. Environment override: `RIZUM_PT_UI_FONT_LANGUAGE` or `RIZUM_PT_UI_FONT_LANG`
2. Local plugin override: `language.txt`
3. Plugin QSettings override: `QSettings("Rizum", "PainterUiFont").value("language")`
4. Painter runtime log: `%LOCALAPPDATA%/Adobe/Adobe Substance 3D Painter/log.txt`
5. Qt app locale: `QtCore.QLocale().name()`
6. Qt system locale: `QtCore.QLocale.system().name()`
7. English fallback

The successful production path was the Painter log. Painter writes lines like:

```text
[INFO] <Qt> "[DBG INFO][NGL Integration]" Using locale: zh_CN
```

The plugin reads the tail of `log.txt`, extracts the latest `Using locale: xx_XX`, then resolves that language against the available `i18n/*.json` files.

## Manual Override Without UI

No language picker is shown in the plugin UI. For local testing or emergency override, create:

```text
language.txt
```

in the plugin root and put one language code in it, for example:

```text
zh-CN
```

`language.txt` is ignored by Git.

## Pending: Text-Fit Layout

Localized strings can be longer than the English source text. The current panel uses fixed label and footer button widths, so German, French, Italian, Spanish, and Portuguese can require more space. The layout adaptation should be fixed in `rizum-pt-ui-prettier` so all compact Painter panels benefit from the same text-fit behavior.
