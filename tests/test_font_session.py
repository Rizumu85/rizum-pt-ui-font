"""Regression tests for global Painter font application."""

from __future__ import annotations

import unittest

from font_session import FontState, QtFontApplier


class _Font:
    PreferNoHinting = 1

    def __init__(self, other=None, *, points=10.0, pixels=-1, family="Default"):
        if isinstance(other, _Font):
            self.points = other.points
            self.pixels = other.pixels
            self.family = other.family
            self.hinting = other.hinting
            return
        self.points = points
        self.pixels = pixels
        self.family = family
        self.hinting = None

    def pointSizeF(self):
        return self.points

    def pointSize(self):
        return int(self.points)

    def pixelSize(self):
        return self.pixels

    def setPointSizeF(self, value):
        self.points = value
        self.pixels = -1

    def setPixelSize(self, value):
        self.points = -1
        self.pixels = value

    def setFamily(self, value):
        self.family = value

    def setHintingPreference(self, value):
        self.hinting = value


class _Application:
    def __init__(self):
        self.properties = {}
        self.font = None
        self.widgets = [object(), object()]

    def setProperty(self, name, value):
        self.properties[name] = value
        return True

    def setFont(self, font):
        self.font = _Font(font)

    def allWidgets(self):
        return tuple(self.widgets)


class _QApplication:
    current = None

    @classmethod
    def instance(cls):
        return cls.current


class _QtGui:
    QFont = _Font


class _QtWidgets:
    QApplication = _QApplication


class QtFontApplierTests(unittest.TestCase):
    def setUp(self):
        _QApplication.current = _Application()
        self.widget_fonts = []
        self.panel_fonts = []

    def tearDown(self):
        _QApplication.current = None

    def _applier(self, original_font=None):
        return QtFontApplier(
            _QtGui,
            _QtWidgets,
            original_font or _Font(points=10.0),
            lambda widget, font: self.widget_fonts.append((widget, _Font(font))),
            lambda font: self.panel_fonts.append(_Font(font)),
        )

    def test_applies_font_globally_and_publishes_scale(self):
        applier = self._applier()

        applied = applier.apply_state(FontState(scale=1.5, family="MiSans"))

        self.assertTrue(applied)
        self.assertEqual(_QApplication.current.properties["rizumUiFontScale"], 1.5)
        self.assertEqual(_QApplication.current.font.family, "MiSans")
        self.assertEqual(_QApplication.current.font.pointSizeF(), 15.0)
        self.assertEqual(len(self.widget_fonts), 2)
        self.assertEqual(len(self.panel_fonts), 1)

    def test_scales_pixel_sized_fonts(self):
        applier = self._applier(_Font(points=-1, pixels=12))

        font = applier.build_font(FontState(scale=1.5))

        self.assertEqual(font.pixelSize(), 18)

    def test_restore_resets_scale_and_reapplies_original_font(self):
        original = _Font(points=10.0, family="Default")
        applier = self._applier(original)
        applier.apply_state(FontState(scale=1.5, family="MiSans"))

        restored = applier.restore_original()

        self.assertTrue(restored)
        self.assertEqual(_QApplication.current.properties["rizumUiFontScale"], 1.0)
        self.assertEqual(_QApplication.current.font.family, "Default")
        self.assertEqual(_QApplication.current.font.pointSizeF(), 10.0)
        self.assertEqual(len(self.widget_fonts), 4)
        self.assertEqual(self.panel_fonts[-1].family, "Default")

    def test_returns_false_without_application(self):
        _QApplication.current = None

        applied = self._applier().apply_state(FontState(scale=1.25))

        self.assertFalse(applied)


if __name__ == "__main__":
    unittest.main()
