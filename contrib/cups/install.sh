#!/bin/sh
# Install the vc500w CUPS backend system-wide (run as root).
#
#   sudo contrib/cups/install.sh [PREFIX]
#
# PREFIX defaults to /opt/labelprinter-vc500w. The backend needs a Python
# environment readable by the CUPS user, so it gets its own venv there.
set -eu
umask 022   # the venv must be readable by the CUPS user (lp)

PREFIX="${1:-/opt/labelprinter-vc500w}"
SRC="$(cd "$(dirname "$0")/../.." && pwd)"

if command -v cups-config >/dev/null; then
    BACKEND_DIR="$(cups-config --serverbin)/backend"
elif [ -d /usr/lib/cups/backend ]; then
    BACKEND_DIR=/usr/lib/cups/backend        # Debian/Ubuntu/Arch
elif [ -d /usr/libexec/cups/backend ]; then
    BACKEND_DIR=/usr/libexec/cups/backend    # Fedora/Gentoo
else
    echo "error: CUPS backend directory not found" >&2
    exit 1
fi

# sudo's secure_path usually hides a per-user uv; look in the caller's home
UV="$(command -v uv || true)"
if [ -z "$UV" ] && [ -n "${SUDO_USER:-}" ]; then
    SUDO_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
    for candidate in "$SUDO_HOME/.local/bin/uv" "$SUDO_HOME/.cargo/bin/uv"; do
        [ -x "$candidate" ] && UV="$candidate" && break
    done
fi

for tool in pdftoppm gs; do
    command -v "$tool" >/dev/null || echo "warning: $tool not found (needed for PDF / PostScript jobs)" >&2
done

# Build from a copy so root does not leave build/ artifacts in the checkout.
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
cp -r "$SRC/pyproject.toml" "$SRC/README.md" "$SRC/LICENSE" "$SRC/labelprinter" "$BUILD/"

if [ -n "$UV" ]; then
    "$UV" venv --quiet --allow-existing "$PREFIX"
    "$UV" pip install --quiet --python "$PREFIX/bin/python" --reinstall-package labelprinter "$BUILD"
else
    # needs the python3-venv package on Debian/Ubuntu
    python3 -m venv "$PREFIX"
    "$PREFIX/bin/pip" install --quiet --upgrade "$BUILD"
fi

sed "s|@PREFIX@|$PREFIX|" "$SRC/contrib/cups/vc500w" > "$BACKEND_DIR/vc500w.tmp"
chmod 0755 "$BACKEND_DIR/vc500w.tmp"
mv "$BACKEND_DIR/vc500w.tmp" "$BACKEND_DIR/vc500w"

echo "Installed backend: $BACKEND_DIR/vc500w (Python in $PREFIX)"
echo "Create a queue, e.g.:"
echo "  lpadmin -p VC500W -E -m raw -o printer-error-policy=abort-job -v 'vc500w://VC-500W1234.local/?mode=vivid&cut=full'"
