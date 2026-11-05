import unittest

from labelprinter.print_text import normalize_tape_width
from labelprinter.tape import nominal_width


class TestNominalWidth(unittest.TestCase):
    def test_reported_inches_map_to_cassette(self):
        # The printer reports 0.35 / 0.5 / 0.75 / 1.0 / 2.0 inches
        for inches, expected in (
            (0.35, 9),
            (0.5, 12),
            (0.75, 19),
            (1.0, 25),
            (2.0, 50),
        ):
            self.assertEqual(nominal_width(inches * 25.4), expected)

    def test_print_text_uses_nominal_width(self):
        self.assertEqual(normalize_tape_width(12.7), 12)
        self.assertEqual(normalize_tape_width(50.8), 50)


if __name__ == "__main__":
    unittest.main()
