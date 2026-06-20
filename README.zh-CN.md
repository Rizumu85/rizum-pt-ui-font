# Rizum Painter UI Font

[English](README.md) | [中文](README.zh-CN.md)

Rizum Painter UI Font 是一个轻量的 Adobe Substance 3D Painter Python 插件，用来在当前 Painter 会话中调整软件界面字体。

## 用处

- 调整 Painter UI 字号，不影响系统字体设置。
- 从插件根目录的 `fonts` 文件夹加载字体。
- 在简洁的停靠面板里切换字体。
- 可选择关闭字体 hinting，让界面显示更干净。
- 使用 `QSettings` 记住字号比例、字体和 hinting 设置。

## 安装步骤

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

## 使用方式

用 `Size` 调整界面字号比例，用 `Font` 选择字体，然后点击 `Apply`。点击 `Reset` 可以恢复 Painter 原始字体。`..` 按钮会打开 `fonts` 文件夹，你可以放入新的 `.ttf` 或 `.otf` 字体文件，再点击刷新按钮更新列表。

## 内置字体

插件的 `fonts` 文件夹内包含 MiSans，作为开箱可用的默认字体选项。MiSans 由小米科技有限责任公司提供，仍受小米《MiSans 字体知识产权许可协议》约束。

MiSans Global 可免费商用，也可以作为嵌入式字体使用，但软件中应特别注明使用了 MiSans 字体。保留随仓库提供的第三方声明和授权链接，不要把 MiSans 字体文件作为独立字体软件单独再分发或售卖。完整声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
