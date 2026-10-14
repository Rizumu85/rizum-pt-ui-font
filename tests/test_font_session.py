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


class _Widget:
    """A managed widget: it has a recorded baseline and a current font."""

    def __init__(self, baseline, current):
        self.properties = {"rizumUiFontBaseline": baseline}
        self.current = current
        self.deleted = False

    def font(self):
        self._check()
        return self.current

    def property(self, name):
        self._check()
        return self.properties.get(name)

    def setProperty(self, name, value):
        self._check()
        self.properties[name] = value

    def _check(self):
        if self.deleted:
            raise RuntimeError("Internal C++ object already deleted.")


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

    def test_a_foreign_size_waits_for_one_requested_settle(self):
        applier = self._applier()
        requests = []
        applier.request_settle = lambda: requests.append(True)
        first = _Widget(_Font(points=10.0), _Font(points=20.0))
        second = _Widget(_Font(points=10.0), _Font(points=20.0))

        applier.widget_font_changed(first)
        applier.widget_font_changed(first)
        applier.widget_font_changed(second)

        self.assertEqual(len(requests), 1)
        self.assertTrue(first.properties["rizumUiFontPending"])
        self.assertIsNotNone(first.properties["rizumUiFontBaseline"])

        applier.settle_pending()

        # Still at the foreign size a turn later: deliberate, record dropped.
        for widget in (first, second):
            self.assertIsNone(widget.properties["rizumUiFontPending"])
            self.assertIsNone(widget.properties["rizumUiFontBaseline"])

        applier.widget_font_changed(_Widget(_Font(points=10.0), _Font(points=20.0)))
        self.assertEqual(len(requests), 2)

    def test_forgetting_drops_the_waiting_widgets_undecided(self):
        applier = self._applier()
        applier.request_settle = lambda: None
        alive = _Widget(_Font(points=10.0), _Font(points=20.0))
        deleted = _Widget(_Font(points=10.0), _Font(points=20.0))
        applier.widget_font_changed(alive)
        applier.widget_font_changed(deleted)
        deleted.deleted = True

        applier.forget_pending()
        applier.settle_pending()

        self.assertEqual(applier._pending, [])
        self.assertIsNone(alive.properties["rizumUiFontPending"])
        self.assertIsNotNone(alive.properties["rizumUiFontBaseline"])


if __name__ == "__main__":
    unittest.main()
