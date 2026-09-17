from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class PowerBIService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cached_embed: dict[str, Any] | None = None

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _env(self, key: str, default: str = "") -> str:
        return str(os.getenv(key, default) or "").strip()

    def _token_config(self) -> dict[str, str]:
        return {
            "tenant_id": self._env("POWERBI_TENANT_ID"),
            "client_id": self._env("POWERBI_CLIENT_ID"),
            "client_secret": self._env("POWERBI_CLIENT_SECRET"),
            "workspace_id": self._env("POWERBI_WORKSPACE_ID"),
            "report_id": self._env("POWERBI_REPORT_ID"),
            "embed_url": self._env("POWERBI_EMBED_URL"),
            "scope": self._env("POWERBI_TOKEN_SCOPE", "https://analysis.windows.net/powerbi/api/.default"),
        }

    def _cached_valid(self) -> bool:
        if not self._cached_embed:
            return False
        expires_at = self._cached_embed.get("expires_at_dt")
        if not isinstance(expires_at, datetime):
            return False
        return expires_at > (self._utc_now() + timedelta(seconds=60))

    def _http_json(self, request: Request) -> dict[str, Any]:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)

    def _aad_access_token(self, cfg: dict[str, str]) -> str:
        if not all((cfg["tenant_id"], cfg["client_id"], cfg["client_secret"])):
            raise RuntimeError("Power BI AAD service principal credentials are not fully configured")

        token_url = f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token"
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "scope": cfg["scope"],
            }
        ).encode("utf-8")

        request = Request(token_url, data=body, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        payload = self._http_json(request)
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("AAD token response did not include access_token")
        return token

    def _generate_embed_token(self, cfg: dict[str, str], aad_token: str) -> dict[str, Any]:
        if not cfg["workspace_id"] or not cfg["report_id"]:
            raise RuntimeError("Power BI workspace/report identifiers are not configured")

        api_url = (
            f"https://api.powerbi.com/v1.0/myorg/groups/{cfg['workspace_id']}/"
            f"reports/{cfg['report_id']}/GenerateToken"
        )
        body = json.dumps({"accessLevel": "View", "allowSaveAs": False}).encode("utf-8")

        request = Request(api_url, data=body, method="POST")
        request.add_header("Authorization", f"Bearer {aad_token}")
        request.add_header("Content-Type", "application/json")
        payload = self._http_json(request)

        embed_token = str(payload.get("token") or "").strip()
        expiration = str(payload.get("expiration") or "").strip()
        if not embed_token:
            raise RuntimeError("Power BI embed token response did not include token")

        expires_at_dt: datetime
        if expiration:
            normalized = expiration.replace("Z", "+00:00")
            expires_at_dt = datetime.fromisoformat(normalized)
            if expires_at_dt.tzinfo is None:
                expires_at_dt = expires_at_dt.replace(tzinfo=timezone.utc)
        else:
            expires_at_dt = self._utc_now() + timedelta(minutes=55)

        return {
            "access_token": embed_token,
            "expires_at": expires_at_dt.astimezone(timezone.utc).isoformat(),
            "expires_at_dt": expires_at_dt.astimezone(timezone.utc),
        }

    def embed_config(self, force_refresh: bool = False) -> dict[str, Any]:
        cfg = self._token_config()
        if not cfg["report_id"] or not cfg["embed_url"]:
            raise RuntimeError("POWERBI_REPORT_ID and POWERBI_EMBED_URL must be configured in backend environment")

        with self._lock:
            if not force_refresh and self._cached_valid():
                cached = dict(self._cached_embed or {})
                cached.pop("expires_at_dt", None)
                return cached

            aad_token = self._aad_access_token(cfg)
            embed = self._generate_embed_token(cfg, aad_token)

            response = {
                "report_id": cfg["report_id"],
                "embed_url": cfg["embed_url"],
                "access_token": embed["access_token"],
                "token_type": "Embed",
                "expires_at": embed["expires_at"],
            }
            self._cached_embed = {**response, "expires_at_dt": embed["expires_at_dt"]}
            return response


powerbi_service = PowerBIService()
