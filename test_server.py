#!/usr/bin/env python3

"""Kansas websocket server entrypoint for modern Python environments."""

import logging
import sys
import time
from dataclasses import dataclass

from server import kansas_wsh

__test__ = False


@dataclass
class _Request:
    ws_stream: object


class _WebSocketStreamAdapter:
    """Adapts websockets.sync connection object to legacy stream interface."""

    def __init__(self, websocket):
        self._websocket = websocket

    def receive_message(self):
        try:
            return self._websocket.recv()
        except Exception:
            return None

    def send_message(self, payload, binary=False):
        if binary:
            self._websocket.send(payload)
        else:
            self._websocket.send(str(payload))


def _handle_connection(websocket):
    stream = _WebSocketStreamAdapter(websocket)
    kansas_wsh.web_socket_transfer_data(_Request(ws_stream=stream))


def main(argv):
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <port>")
        return 1

    try:
        from websockets.sync.server import serve
    except ModuleNotFoundError:
        print("Missing dependency: websockets. Install with `pip install -r requirements.txt`.")
        return 2

    port = int(argv[1])
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(f"Test console at http://localhost:{port}/server/console.html")
    with serve(_handle_connection, "0.0.0.0", port):
        logging.info("Kansas websocket server listening on 0.0.0.0:%d", port)
        try:
            while True:
                # Keep the process alive; each connection is handled in a thread.
                time.sleep(3600)
        except KeyboardInterrupt:
            logging.info("Shutting down")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
