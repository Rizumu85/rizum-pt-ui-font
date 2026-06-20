# Rizum Painter UI Font

[English](README.md) | [中文](README.zh-CN.md)

Rizum Painter UI Font is a lightweight Adobe Substance 3D Painter Python plugin for adjusting the application interface font during the current Painter session.

## Purpose

- Adjust the Painter UI font size without changing system font settings.
- Load fonts from the plugin root `fonts` folder.
- Switch font families from a compact dock panel.
- Optionally disable font hinting for cleaner UI rendering.
- Remember the font scale, font family, and hinting settings with `QSettings`.

## Installation

1. Download or clone this repository.
2. Copy the entire `rizum-pt-ui-font` folder into the Substance 3D Painter Python plugins directory:

   ```text
   Documents/Adobe/Adobe Substance 3D Painter/python/plugins/
   ```

3. The final folder structure should look like this:

   ```text
   python/plugins/rizum-pt-ui-font/
     __init__.py
     plugin.json
     fonts/
   ```

4. Start or restart Substance 3D Painter.
5. Enable the plugin from `Python > Plugins > rizum-pt-ui-font`.
6. Open the `UI Font` panel and click `Apply` to apply the settings.

## Usage

Use `Size` to adjust the interface font scale, choose a font with `Font`, then click `Apply`. Click `Reset` to restore Painter's original font. The `..` button opens the `fonts` folder, where you can add new `.ttf` or `.otf` font files, then click the refresh button to update the list.

## Bundled Fonts

This plugin includes MiSans in the `fonts` folder for a ready-to-use default font option. MiSans is provided by Xiaomi Inc. and remains subject to Xiaomi's MiSans Font Intellectual Property License Agreement.

MiSans Global is free for commercial use, including embedded software, but software that embeds it should specifically state that it uses MiSans. Keep the bundled notice and license reference, and do not redistribute or sell MiSans font files as standalone font software. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the full project notice.
