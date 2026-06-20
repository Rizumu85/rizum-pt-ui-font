# Rizum Painter UI Font

[English](#english) | [中文](#zh-cn)

<a id="english"></a>

## English

Rizum Painter UI Font is a lightweight Adobe Substance 3D Painter Python plugin for adjusting the application interface font during the current Painter session.

### Purpose

- Adjust the Painter UI font size without changing system font settings.
- Load fonts from the plugin root `fonts` folder.
- Switch font families from a compact dock panel.
- Optionally disable font hinting for cleaner UI rendering.
- Remember the font scale, font family, and hinting settings with `QSettings`.

### Installation

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

### Usage

Use `Size` to adjust the interface font scale, choose a font with `Font`, then click `Apply`. Click `Reset` to restore Painter's original font. The `..` button opens the `fonts` folder, where you can add new `.ttf` or `.otf` font files, then click the refresh button to update the list.

### Bundled Fonts

This plugin includes MiSans in the `fonts` folder for a ready-to-use default font option. MiSans is provided by Xiaomi Inc. and remains subject to Xiaomi's MiSans Font Intellectual Property License Agreement.

MiSans Global is free for commercial use, including embedded software, but software that embeds it should specifically state that it uses MiSans. Keep the bundled notice and license reference, and do not redistribute or sell MiSans font files as standalone font software. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the full project notice.

<a id="zh-cn"></a>

## 中文

[English](#english) | [中文](#zh-cn)

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

### 内置字体

插件的 `fonts` 文件夹内包含 MiSans，作为开箱可用的默认字体选项。MiSans 由小米科技有限责任公司提供，仍受小米《MiSans 字体知识产权许可协议》约束。

MiSans Global 可免费商用，也可以作为嵌入式字体使用，但软件中应特别注明使用了 MiSans 字体。保留随仓库提供的第三方声明和授权链接，不要把 MiSans 字体文件作为独立字体软件单独再分发或售卖。完整声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
