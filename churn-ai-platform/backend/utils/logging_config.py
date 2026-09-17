from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os
import json
from datetime import datetime, timezone

from utils.request_context import RequestIdFilter


class ServiceNameFilter:
    def __init__(self, service_name: str) -> None:
        self._service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self._service_name
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "churn-fastapi-backend"),
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(logs_dir: Path) -> tuple[logging.Logger, logging.Logger]:
    logs_dir.mkdir(parents=True, exist_ok=True)

    service_name = os.getenv("SERVICE_NAME", "churn-fastapi-backend")

    # Baseline root logger config requested by the architecture requirement.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        force=True,
    )

    app_logger = logging.getLogger("churn_app")
    error_logger = logging.getLogger("churn_error")

    app_logger.setLevel(logging.INFO)
    error_logger.setLevel(logging.ERROR)

    app_logger.handlers.clear()
    error_logger.handlers.clear()

    # Structured JSON formatter for production-grade machine parsing.
    formatter = JsonFormatter()
    request_filter = RequestIdFilter()
    service_filter = ServiceNameFilter(service_name)

    app_handler = RotatingFileHandler(logs_dir / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    app_handler.setFormatter(formatter)
    app_handler.addFilter(request_filter)
    app_handler.addFilter(service_filter)

    error_handler = RotatingFileHandler(logs_dir / "error.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    error_handler.setFormatter(formatter)
    error_handler.addFilter(request_filter)
    error_handler.addFilter(service_filter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_filter)
    console_handler.addFilter(service_filter)

    app_logger.addHandler(app_handler)
    app_logger.addHandler(console_handler)

    error_logger.addHandler(error_handler)
    error_logger.addHandler(console_handler)

    app_logger.info("logging_initialized | service=%s | logs_dir=%s", service_name, logs_dir)
    return app_logger, error_logger
