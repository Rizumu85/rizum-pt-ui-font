"""Compose the README banner from editable SVG and a panel screenshot."""

import os
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtSvg, QtWidgets


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = Path(__file__).resolve().parent
    layout = source / "hero-layout.svg"
    # Resolve the editable layout's raster layer for the PNG export only.
    svg = layout.read_text(encoding="utf-8")
    document = ET.fromstring(svg)
    text_nodes = []
    image_nodes = []
    for parent in document.iter():
        for node in list(parent):
            if node.tag.endswith("}text"):
                text_nodes.append(node)
                parent.remove(node)
            elif node.tag.endswith("}image"):
                image_nodes.append(node)
                parent.remove(node)
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(ET.tostring(document)))
    if not renderer.isValid():
        raise RuntimeError("Invalid hero layout")
    output = QtGui.QImage(2400, 840, QtGui.QImage.Format.Format_ARGB32)
    output.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(output)
    renderer.render(painter)
    font_id = QtGui.QFontDatabase.addApplicationFont(
        str(source.parents[2] / "fonts" / "MiSans-Regular.ttf")
    )
    family = QtGui.QFontDatabase.applicationFontFamilies(font_id)[0]
    painter.scale(2, 2)
    painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
    for node in image_nodes:
        target = QtCore.QRectF(*(float(node.attrib[key]) for key in ("x", "y", "width", "height")))
        painter.drawImage(target, QtGui.QImage(str(source.parent / "panel.png")))
    painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
    for node in text_nodes:
        font = QtGui.QFont(family)
        font.setPixelSize(int(node.attrib["font-size"]))
        if node.attrib.get("font-weight") == "600":
            font.setWeight(QtGui.QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(node.attrib["fill"]))
        painter.drawText(
            QtCore.QPointF(float(node.attrib["x"]), float(node.attrib["y"])),
            node.text,
        )
    painter.end()
    if not output.save(str(source.parent / "hero.png")):
        raise RuntimeError("Could not save hero")
    print("Rendered hero.png")


if __name__ == "__main__":
    main()
