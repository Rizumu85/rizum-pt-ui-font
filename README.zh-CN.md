# Rizum Painter UI Font

[English](README.md) | [中文](README.zh-CN.md)

Rizum Painter UI Font 是一个Adobe Substance 3D Painter 的 Python 插件，用来调整软件界面字体。

## 用处

- 调整 Painter UI 字号
- 从插件根目录的 `fonts` 文件夹加载字体。
- 切换字体
- 可选择关闭字体 hinting，让渲染更舒服

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
