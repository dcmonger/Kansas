#!/usr/bin/env python3

import argparse
import logging
import os
from types import SimpleNamespace

from server import debugtrace


kansas_wsh = None


try:
    from websockets.sync.server import serve
except ImportError as exc:
    raise SystemExit(
        "Missing dependency 'websockets'. Install with: python3 -m pip install websockets"
    ) from exc


class _CompatStream:
    def __init__(self, conn):
        self._conn = conn
        # Preserve historical access pattern used in kansas_wsh.py
        self._request = SimpleNamespace(
            connection=SimpleNamespace(remote_addr=(conn.remote_address[0], conn.remote_address[1]))
        )

    def send_message(self, message, binary=False):
        if binary:
            self._conn.send(message if isinstance(message, bytes) else message.encode("utf-8"))
        else:
            if isinstance(message, bytes):
                message = message.decode("utf-8", errors="ignore")
            self._conn.send(message)

    def receive_message(self):
        try:
            msg = self._conn.recv()
            if isinstance(msg, bytes):
                return msg.decode("utf-8", errors="ignore")
            return msg
        except Exception:
            # Match historical behavior in kansas_wsh.web_socket_transfer_data
            # where a falsy value signals disconnect.
            return None

    def close_connection(self, wait_response=False):
        self._conn.close()


class _CompatRequest:
    def __init__(self, conn):
        self.ws_stream = _CompatStream(conn)


def _handler(conn):
    # Only /kansas websocket path is expected by the browser client.
    if conn.request.path != "/kansas":
        conn.close(1008, "Unsupported websocket path")
        return

    req = _CompatRequest(conn)
    kansas_wsh.web_socket_do_extra_handshake(req)
    kansas_wsh.web_socket_transfer_data(req)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Kansas websocket test server")
    parser.add_argument("port", type=int, help="WebSocket port")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose server logging for debugging",
    )
    args = parser.parse_args()

    loglevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=loglevel,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logging.info("Server debug logging %s", "enabled" if args.debug else "disabled")

    if args.debug and "KANSAS_TRACE_CALLS" not in os.environ:
        os.environ["KANSAS_TRACE_CALLS"] = "1"
    debugtrace.maybe_enable_from_env(debug_enabled=args.debug)

    from server import kansas_wsh

    print(f"Test console at http://localhost:{args.port}/console.html")
    with serve(_handler, "0.0.0.0", args.port):
        print(f"WebSocket server listening on ws://localhost:{args.port}/kansas")
        try:
            while True:
                import time
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
