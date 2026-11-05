#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Cassette widths of the VC-500W."""

# Nominal widths of the CZ-1001 ... CZ-1005 cassettes in mm. The printer
# reports inches (0.35, 0.5, 0.75, 1.0, 2.0), i.e. 8.9 / 12.7 / 19.05 /
# 25.4 / 50.8 mm, so rounding alone gives 13 and 51 instead of 12 and 50.
NOMINAL_WIDTHS_MM = (9, 12, 19, 25, 50)


def nominal_width(width_mm):
    """Map a reported tape width in mm to the nominal cassette width."""
    return min(NOMINAL_WIDTHS_MM, key=lambda w: abs(w - width_mm))
