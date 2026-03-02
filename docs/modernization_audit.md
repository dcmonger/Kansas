# Modernization Audit (2026)

This repository needs a short modernization pass before it can run on a typical current developer machine.

## Blocking issues found

1. **Python 2 syntax in runtime scripts**
   - `test_server.py`: Python 2 `print` usage.
   - `server/kansas_wsh.py`: Python 2 exception syntax and Python 2-only APIs.
   - `quickdeck.py`: Python 2 exception syntax and `urllib2` dependency.

2. **Archived websocket dependency**
   - `test_server.py` imports `mod_pywebsocket.standalone`.
   - This package is typically unavailable in modern Python environments and should be replaced.

3. **Outdated run instructions**
   - README still references `python -m SimpleHTTPServer`, which should be `python3 -m http.server`.

4. **No real automated tests yet**
   - `server/kansas_wsh_test.py` is currently a placeholder.

## Recommended update order

1. Port Python scripts to Python 3 syntax + stdlib APIs.
2. Replace websocket server plumbing with a maintained library.
3. Add dependency manifest (`requirements.txt` or `pyproject.toml`).
4. Add smoke tests for websocket connect/move/resync flow.
5. Update card data/image source to maintained HTTPS endpoints.

## Quick command checks used

- `python3 -m compileall test_server.py server/kansas_wsh.py quickdeck.py` (fails due to Python 2 syntax)
- `python3 - <<'PY' ... find_spec('mod_pywebsocket') ... PY` (`mod_pywebsocket` not found)
