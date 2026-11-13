"""QEMU guestfwd helper (macOS and Linux): one guest connection to 10.0.2.2:8765 <-> the local server.

QEMU runs this once per connection with the connection on stdin/stdout. Usage: relay.py PORT
"""
import os
import socket
import sys
import threading


def main():
    s = socket.create_connection(('127.0.0.1', int(sys.argv[1])))
    inp, out = sys.stdin.buffer.raw, sys.stdout.buffer.raw

    def up():
        try:
            while True:
                b = os.read(inp.fileno(), 65536)
                if not b:
                    break
                s.sendall(b)
        except OSError:
            pass
        try:
            s.shutdown(socket.SHUT_WR)
        except OSError:
            pass

    threading.Thread(target=up, daemon=True).start()
    try:
        while True:
            b = s.recv(65536)
            if not b:
                break
            while b:
                b = b[os.write(out.fileno(), b):]
    except OSError:
        pass


if __name__ == '__main__':
    main()
