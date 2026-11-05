# CUPS backend `vc500w`

Prints from any application through a normal CUPS queue, but talks the
printer's own protocol instead of AirPrint. That gives you what AirPrint
cannot: the **vivid** print mode and the **cut modes** (full, half, none).

## Install

```sh
sudo contrib/cups/install.sh            # venv in /opt/labelprinter-vc500w
```

Needs `pdftoppm` (poppler) for PDF and `gs` (Ghostscript) for PostScript.
On Linux, `.local` hostnames in the URI need nss-mdns. Without `uv` the
installer falls back to `python3 -m venv` (Debian/Ubuntu: `python3-venv`).

## Queues

The settings live in the device URI, so one queue per cut mode is the
easiest way to pick it from a GUI print dialog (gLabels, GTK, Qt):

```sh
HOST=VC-500W1234.local
sudo lpadmin -p VC500W-cut     -E -m raw -o printer-error-policy=abort-job -v "vc500w://$HOST/?mode=vivid&cut=full"
sudo lpadmin -p VC500W-halfcut -E -m raw -o printer-error-policy=abort-job -v "vc500w://$HOST/?mode=vivid&cut=half"
sudo lpadmin -p VC500W-nocut   -E -m raw -o printer-error-policy=abort-job -v "vc500w://$HOST/?mode=vivid&cut=none"
```

| URI parameter | values | default |
|---|---|---|
| `mode` | `vivid`, `normal` | `vivid` |
| `cut` | `full`, `half`, `none` | `full` |
| `fit` | `1` = scale any page to the tape | off |

On the command line, job options override the URI:
`lp -d VC500W-cut -o cut=half -o mode=normal label.pdf`

## Behaviour

- Every page of the job is one label (PDF, PostScript, PNG, JPEG, …).
- The page width must match the inserted cassette (±1.5 mm); a page whose
  *height* matches is rotated automatically. Anything else (e.g. an A4
  page) cancels the job with a clear message instead of wasting tape —
  unless `fit=1` is set.
- Job state and errors show up in `lpstat -l` and the desktop print queue.
- A failed job (printer unreachable mid-job, timeout) makes CUPS apply the
  queue's error policy. The CUPS default `stop-printer` disables the queue
  until you re-enable it, hence `printer-error-policy=abort-job` above.
- `-o fit` (without a value) counts as `fit=1`.
