"""Power BI route compatibility module.

The active router registration stays in api.routes to avoid behavior changes.
This module offers a dedicated import surface for Power BI endpoint handlers.
"""

from api.routes import powerbi_embed_config

__all__ = ["powerbi_embed_config"]
