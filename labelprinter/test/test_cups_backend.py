import os
import tempfile
import unittest

from PIL import Image

from labelprinter import cups_backend as cb


class TestParsing(unittest.TestCase):
    def test_parse_options(self):
        self.assertEqual(
            cb.parse_options("cut=half job-uuid=x noflag"),
            {"cut": "half", "job-uuid": "x", "noflag": "1"},
        )
        self.assertEqual(cb.parse_options(""), {})

    def test_parse_device_uri(self):
        host, port, query = cb.parse_device_uri(
            "vc500w://VC-500W6382.local/?mode=normal&cut=half"
        )
        self.assertEqual(host, "vc-500w6382.local")  # urlsplit lowercases
        self.assertEqual(port, 9100)
        self.assertEqual(query, {"mode": "normal", "cut": "half"})
        self.assertEqual(cb.parse_device_uri("vc500w://10.0.0.5:9999")[1], 9999)

    def test_parse_device_uri_rejects_other_schemes(self):
        with self.assertRaises(ValueError):
            cb.parse_device_uri("ipp://printer/")

    def test_job_options_override_uri(self):
        settings = cb.resolve_settings({"cut": "half"}, {"cut": "none", "fit": "1"})
        self.assertEqual(settings, {"mode": "vivid", "cut": "none", "fit": True})

    def test_invalid_values(self):
        with self.assertRaises(ValueError):
            cb.resolve_settings({"cut": "diagonal"}, {})
        with self.assertRaises(ValueError):
            cb.resolve_settings({}, {"mode": "neon"})


class TestNominalWidth(unittest.TestCase):
    def test_reported_inches_map_to_cassette(self):
        self.assertEqual(cb.nominal_width(2.0 * 25.4), 50)
        self.assertEqual(cb.nominal_width(0.5 * 25.4), 12)
        self.assertEqual(cb.nominal_width(0.35 * 25.4), 9)


class TestPrepareLabel(unittest.TestCase):
    lpi = 317
    settings = {"mode": "vivid", "cut": "full", "fit": False}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _page(self, width_mm, height_mm):
        px = lambda mm: round(mm / 25.4 * self.lpi)  # noqa: E731
        path = os.path.join(self.tmp.name, "page.png")
        Image.new("RGB", (px(width_mm), px(height_mm)), "white").save(
            path, dpi=(self.lpi, self.lpi)
        )
        return path

    def _prepare(self, page, tape_mm, settings=None):
        out = cb.prepare_label(
            page, tape_mm, settings or self.settings, self.lpi, self.tmp.name, 1
        )
        with Image.open(out) as im:
            return im.size

    def test_matching_width_is_kept(self):
        size = self._prepare(self._page(25, 60), 25.4)
        self.assertLess(size[0], size[1])

    def test_matching_height_is_rotated(self):
        size = self._prepare(self._page(60, 25), 25.4)
        self.assertLess(size[0], size[1])

    def test_wrong_cassette_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self._prepare(self._page(210, 297), 50.8)
        self.assertIn("50 mm cassette", str(ctx.exception))

    def test_fit_allows_any_size(self):
        settings = dict(self.settings, fit=True)
        size = self._prepare(self._page(100, 30), 12.7, settings)
        self.assertLess(size[0], size[1])


class TestRenderPages(unittest.TestCase):
    def test_image_keeps_its_dpi(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in.jpg")
            Image.new("RGB", (591, 300), "red").save(src, dpi=(300, 300))
            work = os.path.join(tmp, "work")
            os.mkdir(work)
            (page,) = cb.render_pages(src, work, 317)
            with Image.open(page) as im:
                width_mm, _ = cb.page_size_mm(im, 317)
            self.assertAlmostEqual(width_mm, 50.0, delta=0.2)

    def test_image_becomes_single_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in.jpg")
            Image.new("RGB", (100, 200), "red").save(src)
            work = os.path.join(tmp, "work")
            os.mkdir(work)
            pages = cb.render_pages(src, work, 317)
            self.assertEqual(len(pages), 1)


if __name__ == "__main__":
    unittest.main()
