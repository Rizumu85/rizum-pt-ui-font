"""Capture the actual plugin panel with isolated settings, outside Painter."""

from pathlib import Path
import os
import sys
import tempfile
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "2")
os.environ.pop("RIZUM_UI_FONT_USE_SIBLING_PRETTIER", None)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from PySide6 import QtCore, QtGui, QtWidgets
import __init__ as plugin


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyle("Fusion")
    app.setFont(QtGui.QFont("Segoe UI", 10))
    with tempfile.TemporaryDirectory() as temporary:
        settings = QtCore.QSettings(
            str(Path(temporary) / "settings.ini"), QtCore.QSettings.Format.IniFormat
        )
        with (
            mock.patch.object(QtCore, "QSettings", return_value=settings),
            mock.patch.object(plugin, "_read_painter_log_language", return_value="en"),
        ):
            panel = plugin.UiScalePanel()
        panel.scale.setValue(1.10)
        index = panel.font_combo.findData("MiSans")
        if index >= 0:
            panel.font_combo.setCurrentIndex(index)
        panel.widget.resize(360, panel.widget.minimumSizeHint().height())
        panel.widget.show()
        app.processEvents()
        destination = ROOT / "assets" / "readme" / "panel.png"
        card = panel._card_layout.parentWidget()
        ratio = card.devicePixelRatioF()
        capture = QtGui.QImage(
            round(card.width() * ratio), round(card.height() * ratio),
            QtGui.QImage.Format.Format_ARGB32_Premultiplied,
        )
        capture.setDevicePixelRatio(ratio)
        capture.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(capture)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        mask = QtGui.QPainterPath()
        radius = panel.ui.components.COMPACT_DOCK_CARD_RADIUS
        mask.addRoundedRect(QtCore.QRectF(card.rect()), radius, radius)
        painter.setClipPath(mask)
        card.render(painter, QtCore.QPoint())
        painter.end()
        if not capture.save(str(destination)):
            raise RuntimeError("Could not save panel capture")
        print(f"Captured actual panel: {destination}")
        panel.close()
        panel.widget.close()


if __name__ == "__main__":
    main()
