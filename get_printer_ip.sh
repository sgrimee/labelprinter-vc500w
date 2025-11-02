#!/usr/bin/env bash

# Get the IP address of Brother VC-500W label printer
# Uses avahi to resolve the printer hostname

PRINTER_HOSTNAME="VC-500W4188.local"
IP_ADDRESS=$(avahi-resolve -n "$PRINTER_HOSTNAME" -4 2>/dev/null | awk '{print $2}')

if [ -n "$IP_ADDRESS" ]; then
    echo "$IP_ADDRESS"
    exit 0
else
    echo "Error: Could not resolve printer IP address" >&2
    exit 1
fi