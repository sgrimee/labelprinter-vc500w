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
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
        self._timeout_standard = 5;
        self._timeout_flush = 1;
        self._timeout_long = 30;
        self._socket.settimeout(self._timeout_standard);
        self._socket.connect((host, port));
        self.flush();

    def flush(self):
        try:
            self._socket.settimeout(self._timeout_flush);
            self._socket.recv(4096);
        except:
            pass
        finally:
            self._socket.settimeout(self._timeout_standard);

    def send_message(self, message):
        self._socket.sendall(message.get_data().encode());

    def send_file(self, handle):
        self._socket.sendfile(handle, 0);

    def get_message(self, long_timeout = False, buffer_size = 4096):
        try:
            if long_timeout:
                self._socket.settimeout(self._timeout_long);

            found = '';

            found = self._socket.recv(buffer_size).decode();

            return found;
        finally:
            self._socket.settimeout(self._timeout_standard);

    def close(self):
        self._socket.close();
