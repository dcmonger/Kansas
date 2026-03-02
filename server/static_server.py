#!/usr/bin/env python3

import argparse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


_DEVTOOLS_DISCOVERY_PATH = "/.well-known/appspecific/com.chrome.devtools.json"


class KansasStaticRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == _DEVTOOLS_DISCOVERY_PATH:
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        super().do_GET()


def main():
    parser = argparse.ArgumentParser(description="Kansas static file server")
    parser.add_argument("port", type=int, help="HTTP port to serve")
    args = parser.parse_args()

    with ThreadingHTTPServer(("", args.port), KansasStaticRequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
