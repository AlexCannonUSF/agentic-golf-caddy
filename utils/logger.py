"""Structured JSON logging for the agent pipeline."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

_LOG_LEVEL_ENV = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_ENV, logging.INFO)


def setup_logging(level: int | None = None) -> None:
    """Configure root logger with a clean format.

    Called once at application startup. Respects the ``LOG_LEVEL``
    environment variable (DEBUG / INFO / WARNING / ERROR).
    """
    effective_level = level if level is not None else _LOG_LEVEL
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(effective_level)


class PipelineLogger:
    """Emit structured JSON log records for each pipeline step.

    When *enabled* is ``False`` (the default production mode) calls to
    :meth:`log_step` are silently ignored so there is zero overhead.
    """

    def __init__(self, *, enabled: bool = False) -> None:
        self._enabled = enabled
        self._logger = logging.getLogger("pipeline.debug")
        self._step_counter = 0

    def log_step(self, step_name: str, data: dict[str, Any] | None = None) -> None:
        """Write a single structured JSON line for *step_name*."""
        if not self._enabled:
            return

        self._step_counter += 1
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": self._step_counter,
            "name": step_name,
        }
        if data is not None:
            record["data"] = data

        self._logger.debug("PIPELINE_STEP %s", json.dumps(record, default=str))

    def log_data_source(self, source_name: str, data: dict[str, Any] | None = None) -> None:
        """Write a structured data-source event for cache/API observability."""

        payload = {"source": source_name}
        if data:
            payload.update(data)
        self.log_step("data_source", payload)
