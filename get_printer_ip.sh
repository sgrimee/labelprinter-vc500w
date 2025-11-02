#!/usr/bin/env bash
#
# Get the IP address of Brother VC-500W label printer
# Uses avahi to resolve the printer hostname

set -euo pipefail

# Load config or use defaults
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/labelprinter"
CONFIG_FILE="$CONFIG_DIR/config.json"

get_config_value() {
    local key="$1"
    local default="$2"

    if [[ -f "$CONFIG_FILE" ]]; then
        # Extract value from JSON using basic parsing (could use jq if available)
        local value
        value=$(grep -o "\"$key\": *\"[^\"]*\"" "$CONFIG_FILE" 2>/dev/null | sed "s/.*\"$key\": *\"\([^\"]*\)\".*/\1/")
        if [[ -n "$value" ]]; then
            echo "$value"
            return
        fi
    fi

    echo "$default"
}

readonly PRINTER_HOSTNAME="${PRINTER_HOSTNAME:-$(get_config_value host "VC-500W4188.local")}"

resolve_printer_ip() {
    avahi-resolve -n "$PRINTER_HOSTNAME" -4 2>/dev/null | awk '{print $2}'
}

main() {
    if ! command -v avahi-resolve >/dev/null 2>&1; then
        echo "Error: avahi-resolve not found. Install avahi-utils." >&2
        exit 1
    fi

    local ip_address
    ip_address=$(resolve_printer_ip)

    if [[ -n "$ip_address" ]]; then
        echo "$ip_address"
    else
        echo "Error: Could not resolve printer IP address for $PRINTER_HOSTNAME" >&2
        echo "Make sure the printer is on and connected to the network." >&2
        exit 1
    fi
}

main "$@"