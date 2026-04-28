# Rizum Painter UI Font

[English](README.md) | [中文](README.zh-CN.md)

Rizum Painter UI Font is a compact Adobe Substance 3D Painter Python plugin for adjusting the Painter interface font during the current session.

## What It Does

- Scales the Painter UI font size without changing the operating system settings.
- Loads bundled fonts from the plugin's `fonts` folder.
- Lets you switch font family from a small dock panel.
- Applies optional no-hinting font rendering for a cleaner UI look.
- Saves the selected scale, font, and hinting setting with `QSettings`.

## Installation

1. Download or clone this repository.
2. Copy the whole `rizum-pt-ui-font` folder into your Substance 3D Painter Python plugins folder:

   ```text
   Documents/Adobe/Adobe Substance 3D Painter/python/plugins/
   ```

3. The final structure should look like this:

   ```text
   python/plugins/rizum-pt-ui-font/
     __init__.py
     plugin.json
     fonts/
   ```

4. Start or restart Substance 3D Painter.
5. Enable the plugin from `Python > Plugins > rizum-pt-ui-font`.
6. Open the `UI Font` dock panel and press `Apply`.

## Usage

Use the `Size` control to scale the interface font, choose a font from the `Font` menu, and press `Apply`. Use `Reset` to return to Painter's original UI font. The `..` button opens the `fonts` folder so you can add more `.ttf` or `.otf` files, then press the refresh button to update the list.
