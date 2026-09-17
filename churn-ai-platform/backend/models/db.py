"""Backward-compatible db module path.

This file preserves imports like `from models.db import ...` after
the database layer moved to `backend/db/db.py`.
"""

from db.db import *  # noqa: F401,F403
