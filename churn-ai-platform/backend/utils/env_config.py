from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PLATFORM_ROOT = _BACKEND_ROOT.parent

# Load environment variables from project root .env once.
load_dotenv(_PLATFORM_ROOT / ".env")


def get_env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip() != "":
            return value
    return default


def get_bool_env(*names: str, default: bool = False) -> bool:
    raw = get_env(*names)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}
