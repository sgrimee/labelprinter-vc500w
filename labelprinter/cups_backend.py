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

"""CUPS backend for the Brother VC-500W.

Lets any application (gLabels, LibreOffice, image viewers, ...) print through
a normal CUPS queue while using the printer's own protocol, which unlike
AirPrint/IPP offers the "vivid" mode and the cut modes.

Device URI:  vc500w://HOST[:PORT]/?mode=vivid&cut=full[&fit=1]

    mode  vivid | normal                      (default vivid)
    cut   full | half | none                  (default full)
    fit   1 = scale any page size to the tape (default: page width must
          match the inserted tape, otherwise the job is cancelled)

Job options (lp -o cut=half -o mode=normal -o fit=1) override the URI.

Each page of the job becomes one label. PDF is rendered with pdftoppm,
PostScript with Ghostscript, images are read with Pillow.

Install: see contrib/cups/README.md
"""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from labelprinter.connection import Connection
from labelprinter.printer import LabelPrinter
from labelprinter.tape import nominal_width

# CUPS backend exit codes (cups/backend.h)
CUPS_BACKEND_OK = 0
CUPS_BACKEND_FAILED = 1
CUPS_BACKEND_CANCEL = 5
CUPS_BACKEND_RETRY = 6

# Printer resolution per mode, see LabelPrinter.Print.get_mode()
LPI = {"vivid": 317, "normal": 264}

# Allowed difference between page width and tape width
WIDTH_TOLERANCE_MM = 1.5

PRINT_TIMEOUT = 180


def log(level, message):
    """Write a message CUPS shows in the job/printer state."""
    print("%s: %s" % (level, message), file=sys.stderr, flush=True)


def parse_options(text):
    """Parse the CUPS options string 'a=b c=d flag' into a dict."""
    options = {}
    for item in (text or "").split():
        key, sep, value = item.partition("=")
        # a bare flag like "-o fit" arrives without a value
        options[key.lower()] = value if sep else "1"
    return options


def parse_device_uri(uri):
    parts = urlsplit(uri)
    if parts.scheme != "vc500w" or not parts.hostname:
        raise ValueError("invalid device URI %r, expected vc500w://HOST/" % uri)
    query = {k: v[-1] for k, v in parse_qs(parts.query).items()}
    return parts.hostname, parts.port or 9100, query


def resolve_settings(uri_query, job_options):
    """Merge URI defaults with job options and validate them."""
    settings = {"mode": "vivid", "cut": "full", "fit": "0"}
    for source in (uri_query, job_options):
        for key in settings:
            if source.get(key):
                settings[key] = source[key].lower()
    if settings["mode"] not in LPI:
        raise ValueError("unknown mode %r (vivid|normal)" % settings["mode"])
    if settings["cut"] not in ("full", "half", "none"):
        raise ValueError("unknown cut %r (full|half|none)" % settings["cut"])
    settings["fit"] = settings["fit"] in ("1", "true", "yes", "on")
    return settings


def sniff_type(path):
    with open(path, "rb") as f:
        head = f.read(8)
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"%!"):
        return "ps"
    return "image"


def render_pages(source, workdir, lpi):
    """Turn the job file into one PNG/JPEG per page, return their paths."""
    kind = sniff_type(source)
    if kind == "pdf":
        subprocess.run(
            ["pdftoppm", "-r", str(lpi), "-png", source, os.path.join(workdir, "page")],
            check=True,
            capture_output=True,
        )
    elif kind == "ps":
        subprocess.run(
            [
                "gs",
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=png16m",
                "-r%d" % lpi,
                "-sOutputFile=" + os.path.join(workdir, "page-%03d.png"),
                source,
            ],
            check=True,
            capture_output=True,
        )
    else:
        with Image.open(source) as im:
            im.load()
            path = os.path.join(workdir, "page-001.png")
            # keep the DPI, it decides the physical size of the label
            dpi = im.info.get("dpi") or (lpi, lpi)
            im.convert("RGB").save(path, dpi=dpi)
    pages = sorted(
        os.path.join(workdir, name)
        for name in os.listdir(workdir)
        if name.startswith("page")
    )
    if not pages:
        raise ValueError("the job contains no printable page")
    return pages


def page_size_mm(image, lpi):
    """Physical page size; images without DPI info count as printer LPI."""
    dpi = image.info.get("dpi", (lpi, lpi))
    dpi_x = dpi[0] or lpi
    dpi_y = dpi[1] or lpi
    return image.width / dpi_x * 25.4, image.height / dpi_y * 25.4


def prepare_label(page, tape_mm, settings, lpi, workdir, index):
    """Rotate the page so its width runs across the tape, save as JPEG."""
    with Image.open(page) as im:
        im = im.convert("RGB")
        width_mm, height_mm = page_size_mm(im, lpi)

        if abs(width_mm - tape_mm) <= WIDTH_TOLERANCE_MM:
            pass
        elif abs(height_mm - tape_mm) <= WIDTH_TOLERANCE_MM:
            im = im.rotate(90, expand=True)
        elif not settings["fit"]:
            raise ValueError(
                "label is %.1f x %.1f mm but a %d mm cassette is inserted "
                "- insert the matching cassette or print with -o fit=1"
                % (width_mm, height_mm, nominal_width(tape_mm))
            )
        elif im.width > im.height:
            # fit=1: let the long side run along the tape
            im = im.rotate(90, expand=True)

        path = os.path.join(workdir, "label-%03d.jpg" % index)
        im.save(path, quality=95, dpi=(lpi, lpi))
    return path


def discovery():
    print('network vc500w "Unknown" "Brother VC-500W (vivid, cut modes)"')
    return CUPS_BACKEND_OK


def run(argv, env):
    if len(argv) == 1:
        return discovery()
    if len(argv) not in (6, 7):
        log("ERROR", "usage: vc500w job-id user title copies options [file]")
        return CUPS_BACKEND_FAILED

    try:
        host, port, uri_query = parse_device_uri(env.get("DEVICE_URI", argv[0]))
        settings = resolve_settings(uri_query, parse_options(argv[5]))
        copies = max(1, int(argv[4] or 1))
    except ValueError as e:
        log("ERROR", str(e))
        return CUPS_BACKEND_CANCEL

    lpi = LPI[settings["mode"]]
    workdir = tempfile.mkdtemp(prefix="vc500w-", dir=env.get("TMPDIR"))
    connection = None
    # CUPS sends SIGTERM on cancel; exit through finally to clean up
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(CUPS_BACKEND_FAILED))
    try:
        if len(argv) == 7:
            source = argv[6]
        else:
            source = os.path.join(workdir, "job")
            with open(source, "wb") as f:
                shutil.copyfileobj(sys.stdin.buffer, f)

        try:
            pages = render_pages(source, workdir, lpi)
        except Exception as e:  # noqa: BLE001 - any unreadable input, e.g. DecompressionBombError
            log("ERROR", "cannot read the job file: %s" % e)
            return CUPS_BACKEND_CANCEL

        log("STATE", "+connecting-to-device")
        try:
            connection = Connection(host, port, PRINT_TIMEOUT)
            printer = LabelPrinter(connection)
        except (OSError, ValueError) as e:
            log("ERROR", "printer %s not reachable: %s" % (host, e))
            return CUPS_BACKEND_RETRY
        log("STATE", "-connecting-to-device")

        configuration = printer.get_configuration()
        if not configuration.tape_width:
            log("ERROR", "no cassette inserted")
            return CUPS_BACKEND_RETRY
        tape_mm = configuration.tape_width * 25.4

        try:
            labels = [
                prepare_label(page, tape_mm, settings, lpi, workdir, i)
                for i, page in enumerate(pages, 1)
            ]
        except ValueError as e:
            log("ERROR", str(e))
            return CUPS_BACKEND_CANCEL

        total = len(labels) * copies
        done = 0
        for _ in range(copies):
            for label in labels:
                status = printer.get_status()
                if status.print_state != "IDLE":
                    printer.wait_to_turn_idle(PRINT_TIMEOUT)
                done += 1
                log(
                    "INFO",
                    "printing label %d of %d (%s, cut %s)"
                    % (done, total, settings["mode"], settings["cut"]),
                )
                with open(label, "rb") as handle:
                    printer.print_jpeg(handle, settings["mode"], settings["cut"])
                printer.wait_to_turn_idle(PRINT_TIMEOUT)
                log("PAGE", "%d 1" % done)
        log("INFO", "done, %d label(s) printed" % total)
        return CUPS_BACKEND_OK
    except (OSError, TimeoutError, ValueError) as e:
        log("ERROR", "printing failed: %s" % e)
        return CUPS_BACKEND_FAILED
    finally:
        if connection is not None:
            connection.close()
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    sys.exit(run(sys.argv, os.environ))


if __name__ == "__main__":
    main()
