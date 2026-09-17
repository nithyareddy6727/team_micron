"""Backward-compatible module alias for API routes.

Importing ``routes.routes`` returns the same module object as ``api.routes``
so monkeypatches and symbol updates stay in sync.
"""

import sys

from api import routes as _api_routes

sys.modules[__name__] = _api_routes
