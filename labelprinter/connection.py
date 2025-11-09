#!/usr/bin/env python3
#
# Copyright (c) Andrea Micheloni 2021
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import socket


class Connection:
    def __init__(self, host, port):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._timeout_standard = 5
        self._timeout_flush = 1
        self._timeout_long = 30
        self._timeout_connect = 3  # Faster timeout for initial connection
        self._socket.settimeout(self._timeout_connect)

        # Try to resolve hostname first with clear error message
        # Prefer IPv4 since we're using AF_INET socket
        try:
            addr_info = socket.getaddrinfo(
                host, port, socket.AF_INET, socket.SOCK_STREAM
            )
            if not addr_info:
                raise socket.gaierror(-2, "No address found")
        except socket.gaierror as e:
            error_msg = str(e)
            # Check if it's specifically an IPv4 resolution issue
            ipv6_hint = ""
            try:
                # Try to see if IPv6 address exists
                socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_STREAM)
                ipv6_hint = (
                    f"\nNote: The hostname resolves to IPv6 but not IPv4.\n"
                    f"The printer may only have an IPv6 address, or IPv4 may be disabled.\n"
                    f"Try finding the IPv4 address with: avahi-resolve -n {host} -4"
                )
            except (socket.gaierror, OSError):
                # Both IPv4 and IPv6 resolution failed
                pass

            raise ValueError(
                f"Cannot resolve hostname '{host}' to IPv4 address: {error_msg}\n"
                f"Possible solutions:\n"
                f"  • Check if the printer is powered on and connected to the network\n"
                f"  • Try using the IP address directly (find it with: avahi-resolve -n {host} -4)\n"
                f"  • Update your config file (~/.config/labelprinter/config.json) with the printer's IP address\n"
                f"  • Check your network connection and DNS/mDNS settings{ipv6_hint}"
            ) from e

        # Now attempt to connect
        try:
            self._socket.connect((host, port))
        except socket.timeout as e:
            raise ValueError(
                f"Connection to '{host}:{port}' timed out after {self._timeout_connect} seconds.\n"
                f"The hostname resolved but the printer is not responding on port {port}.\n"
                f"Possible solutions:\n"
                f"  • Check if the printer is powered on and not in sleep mode\n"
                f"  • Verify the printer is on the same network segment\n"
                f"  • Check firewall settings on your computer and network\n"
                f"  • Try using the IP address directly: avahi-resolve -n {host} -4\n"
                f"  • Try restarting the printer"
            ) from e
        except ConnectionRefusedError as e:
            raise ValueError(
                f"Connection to '{host}:{port}' was refused.\n"
                f"Possible solutions:\n"
                f"  • Check if port {port} is correct (usually 9100 for label printers)\n"
                f"  • Verify the printer's network service is running\n"
                f"  • Try restarting the printer"
            ) from e
        except OSError as e:
            raise ValueError(
                f"Cannot connect to printer at '{host}:{port}': {e}\n"
                f"Possible solutions:\n"
                f"  • Verify the hostname or IP address is correct\n"
                f"  • Check your network connection\n"
                f"  • Ensure the printer is on the same network"
            ) from e

        # Connection successful, restore standard timeout
        self._socket.settimeout(self._timeout_standard)
        self.flush()

    def flush(self):
        try:
            self._socket.settimeout(self._timeout_flush)
            self._socket.recv(4096)
        except Exception:
            pass
        finally:
            self._socket.settimeout(self._timeout_standard)

    def send_message(self, message):
        self._socket.sendall(message.get_data().encode())

    def send_file(self, handle):
        self._socket.sendfile(handle, 0)

    def get_message(self, long_timeout=False, buffer_size=4096):
        try:
            if long_timeout:
                self._socket.settimeout(self._timeout_long)

            found = ""

            found = self._socket.recv(buffer_size).decode()

            return found
        finally:
            self._socket.settimeout(self._timeout_standard)

    def close(self):
        self._socket.close()
