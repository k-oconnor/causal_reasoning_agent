"""
causal_agent/log_config.py

Logging configuration for the causal_agent framework.

Call setup_logging() once at the top of any entry point (example runner,
eval script, notebook) to activate structured output.

Log levels
----------
DEBUG  – full prompt text, full response text, all tool arguments/results.
         Use this to see exactly what the LLM receives and produces.
INFO   – completion summaries (model, char count, tool call names),
         planning iterations, phase transitions.  Good default for evals.
WARNING – recoverable issues: replan triggered, max_iterations hit.
ERROR  – unrecoverable failures.

Usage
-----
    from causal_agent.log_config import setup_logging
    setup_logging(level="DEBUG")              # see everything
    setup_logging(level="INFO")               # see summaries only
    setup_logging(level="INFO", log_file="run.log")   # also write to file
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


_FRAMEWORK_LOGGER = "causal_agent"

_FMT = "%(asctime)s  %(levelname)-8s  %(name)s  |  %(message)s"
_DATEFMT = "%H:%M:%S"


def setup_logging(
    level: str | int = "INFO",
    log_file: str | Path | None = None,
    fmt: str = _FMT,
    datefmt: str = _DATEFMT,
    load_dotenv: bool = True,
) -> logging.Logger:
    """
    Configure the causal_agent logger and return it.

    Parameters
    ----------
    level      : "DEBUG", "INFO", "WARNING", "ERROR", or an int.
    log_file   : optional path; if provided, output is mirrored to this file
                 (append mode) in addition to stdout.
    fmt        : log format string (default includes timestamp + level + name).
    datefmt    : strftime format for timestamps.
    load_dotenv: if True (default), load .env from the current directory so
                 API keys are available without manual dotenv calls.

    Returns
    -------
    The configured causal_agent root logger.
    """
    if load_dotenv:
        try:
            from dotenv import load_dotenv as _load
            _load()
        except ImportError:
            pass
    numeric = level if isinstance(level, int) else getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    # Force UTF-8 on stdout so non-ASCII content from web pages / LLM responses
    # doesn't crash the log handler on Windows (cp1252 default).
    stdout = sys.stdout
    if hasattr(stdout, "reconfigure"):
        try:
            stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    handlers: list[logging.Handler] = [
        _make_handler(logging.StreamHandler(stdout), formatter),
    ]
    if log_file is not None:
        handlers.append(_make_handler(
            logging.FileHandler(log_file, mode="a", encoding="utf-8"), formatter
        ))

    logger = logging.getLogger(_FRAMEWORK_LOGGER)
    logger.setLevel(numeric)
    logger.handlers.clear()
    for h in handlers:
        logger.addHandler(h)
    logger.propagate = False   # don't double-log if root logger is configured

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the causal_agent namespace."""
    return logging.getLogger(f"{_FRAMEWORK_LOGGER}.{name}")


def _make_handler(handler: logging.Handler, formatter: logging.Formatter) -> logging.Handler:
    handler.setFormatter(formatter)
    return handler
