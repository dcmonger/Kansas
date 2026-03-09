import logging
import os
import sys
import threading


def _truthy(value):
    return str(value).lower() in ("1", "true", "yes", "on")


def _build_logger():
    logger = logging.getLogger("kansas.trace")
    logger.setLevel(logging.DEBUG)
    return logger


def enable_call_tracing():
    """Enable Python-level tracing for every function call/return/exception event."""
    logger = _build_logger()

    def _trace(frame, event, arg):
        if event not in ("call", "return", "exception"):
            return _trace

        code = frame.f_code
        filename = code.co_filename
        func_name = code.co_name
        lineno = frame.f_lineno

        if event == "exception":
            exc_type = arg[0].__name__ if arg and arg[0] else "Unknown"
            logger.debug("[TRACE] %s %s:%s %s exc=%s", event, filename, lineno, func_name, exc_type)
        elif event == "return":
            logger.debug("[TRACE] %s %s:%s %s", event, filename, lineno, func_name)
        else:
            logger.debug("[TRACE] %s %s:%s %s", event, filename, lineno, func_name)

        return _trace

    sys.setprofile(_trace)
    threading.setprofile(_trace)
    logger.info("Backend call tracing enabled: every Python function call is logged")


def maybe_enable_from_env(debug_enabled=False):
    trace_from_env = os.environ.get("KANSAS_TRACE_CALLS")
    if trace_from_env is None:
        should_trace = bool(debug_enabled)
    else:
        should_trace = _truthy(trace_from_env)

    if should_trace:
        enable_call_tracing()
