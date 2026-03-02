#!/usr/bin/env python3

import sys

try:
    from mod_pywebsocket import standalone
except ImportError:
    try:
        from pywebsocket3 import standalone
    except ImportError:
        from pywebsocket import standalone


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
    else:
        print(f"Test console at http://localhost:{int(sys.argv[1])}/console.html")
        standalone._main(['-p', sys.argv[1], '-d', 'server', '--log_level=info'])
