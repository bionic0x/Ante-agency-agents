#!/usr/bin/env python3
"""Runs inside the agent container (mounted read-only by the relay).

The container has no network. This bridges 127.0.0.1:8787 to the relay's per-run unix
socket so standard HTTP clients (ANTHROPIC_BASE_URL) can reach the model proxy, then runs
the agent command with the instruction on stdin and exits with its status."""
import socket
import subprocess
import sys
import threading

SOCKET = "/run/relay/model.sock"
LISTEN = ("127.0.0.1", 8787)


def pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s, how in ((dst, socket.SHUT_WR), (src, socket.SHUT_RD)):
            try:
                s.shutdown(how)
            except OSError:
                pass


def serve(listener):
    while True:
        client, _ = listener.accept()
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            upstream.connect(SOCKET)
        except OSError:
            client.close()
            upstream.close()
            continue
        threading.Thread(target=pipe, args=(client, upstream), daemon=True).start()
        threading.Thread(target=pipe, args=(upstream, client), daemon=True).start()


def main(argv):
    if len(argv) < 2 or argv[0] != "--":
        print("usage: forwarder.py -- <agent command...>", file=sys.stderr)
        return 64
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(LISTEN)
    listener.listen(16)
    threading.Thread(target=serve, args=(listener,), daemon=True).start()
    return subprocess.run(argv[1:]).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
