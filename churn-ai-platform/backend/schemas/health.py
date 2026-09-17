from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    database_connected: bool
    uptime_seconds: float
    checks: dict[str, bool]


class SystemHealthResponse(BaseModel):
    model_loaded: bool
    db_connected: bool
    api_status: str
