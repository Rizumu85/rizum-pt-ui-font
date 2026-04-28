# Rizum Painter UI Font

[English](#english) | [中文](#中文)

## English

Rizum Painter UI Font is a compact Adobe Substance 3D Painter Python plugin for adjusting the Painter interface font during the current session.

### What It Does

- Scales the Painter UI font size without changing the operating system settings.
- Loads bundled fonts from the plugin's `fonts` folder.
- Lets you switch font family from a small dock panel.
- Applies optional no-hinting font rendering for a cleaner UI look.
- Saves the selected scale, font, and hinting setting with `QSettings`.

### Installation

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

### Usage

Use the `Size` control to scale the interface font, choose a font from the `Font` menu, and press `Apply`. Use `Reset` to return to Painter's original UI font. The `..` button opens the `fonts` folder so you can add more `.ttf` or `.otf` files, then press the refresh button to update the list.

## 中文

Rizum Painter UI Font 是一个轻量的 Adobe Substance 3D Painter Python 插件，用来在当前 Painter 会话中调整软件界面字体。

### 用处

- 调整 Painter UI 字号，不影响系统字体设置。
- 从插件根目录的 `fonts` 文件夹加载字体。
- 在简洁的停靠面板里切换字体。
- 可选择关闭字体 hinting，让界面显示更干净。
- 使用 `QSettings` 记住字号比例、字体和 hinting 设置。

### 安装步骤

1. 下载或克隆这个仓库。
2. 把整个 `rizum-pt-ui-font` 文件夹复制到 Substance 3D Painter 的 Python 插件目录：

   ```text
   Documents/Adobe/Adobe Substance 3D Painter/python/plugins/
   ```

3. 最终目录结构应类似：

   ```text
   python/plugins/rizum-pt-ui-font/
     __init__.py
     plugin.json
     fonts/
   ```

4. 启动或重启 Substance 3D Painter。
5. 在 `Python > Plugins > rizum-pt-ui-font` 中启用插件。
6. 打开 `UI Font` 面板，点击 `Apply` 应用设置。

### 使用方式

用 `Size` 调整界面字号比例，用 `Font` 选择字体，然后点击 `Apply`。点击 `Reset` 可以恢复 Painter 原始字体。`..` 按钮会打开 `fonts` 文件夹，你可以放入新的 `.ttf` 或 `.otf` 字体文件，再点击刷新按钮更新列表。
