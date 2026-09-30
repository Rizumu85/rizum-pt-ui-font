# Rizum Painter UI Font


实时预览 Adobe Substance 3D Painter 的界面字体并保存。

[下载插件](https://github.com/Rizumu85/rizum-pt-ui-font/releases/latest) · [安装](#安装) · [English](README.md)

<p align="center">
  <img src="assets/readme/hero.png" width="100%" alt="Rizum UI Font 横幅：在 Painter 中调整字体和字号，面板展示 MiSans、1.10 字号比例，以及撤销、重置和保存控件。">
</p>

<p align="center"><sub>从当前插件代码在 Painter 外渲染的真实面板，使用 MiSans 和 1.10 字号比例。</sub></p>

## 界面

- **字号**：调整界面字体比例。
- **字体**：选择内置 MiSans，也可以添加自己的 `.ttf` 或 `.otf` 字体。
- **No hinting**：切换字体抗锯齿的渲染效果。
- **撤销、Reset、Save**：撤销上一步修改、预览 Painter 原始字体，或保存当前效果。

保存的字体设置会在后续会话中继续使用。

## 安装

1. 从[最新发布页](https://github.com/Rizumu85/rizum-pt-ui-font/releases/latest)下载插件 ZIP 并解压。
2. 把 `rizum-pt-ui-font` 文件夹放进 Painter 的 Python 插件目录：

   ```text
   Documents/Adobe/Adobe Substance 3D Painter/python/plugins/rizum-pt-ui-font/
   ```

   `__init__.py` 和 `plugin.json` 应直接位于这个文件夹内，与 `fonts/`、`i18n/`、`icons/`、`rizum_ui/` 同级。

3. 重启 Painter，在 `Python > Plugins > rizum-pt-ui-font` 中启用插件。
4. 打开 **UI Font**，调整 **Size** 或 **Font**，点击 **Save** 保存。

## 先试，再保存

修改会立即应用到界面。**Save** 保存当前设置；关闭面板会放弃尚未保存的修改，恢复到上次保存的效果。

底部的**撤销箭头**可以撤销上一步实时修改。**Reset** 会预览 Painter 原始字体设置，点击 **Save** 才会保存这次重置。

想添加字体时，点击**文件夹图标**，把 `.ttf` 或 `.otf` 文件放进 `fonts/`，再点击**刷新图标**。从 **Font** 中选择新字体，预览满意后保存。

## 兼容性与字体授权

插件使用 Painter 的 Qt6 / PySide6 界面，调整的是软件 UI 字体。

**内置 MiSans。** 字体由小米科技有限责任公司提供，受《MiSans 字体知识产权许可协议》约束。再分发插件时请保留[第三方声明](THIRD_PARTY_NOTICES.md)；字体授权与插件的 MIT 授权分别适用。

发布前的检查命令与面板截图生成方式见[英文版维护说明](README.md#compatibility--fonts)。
