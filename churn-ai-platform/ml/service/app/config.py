from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Churn Intelligence ML Service"
    app_version: str = "1.0.0"
    host: str = os.getenv("ML_SERVICE_HOST", "0.0.0.0")
    port: int = int(os.getenv("ML_SERVICE_PORT", "8000"))

    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3307"))
    mysql_database: str = os.getenv("MYSQL_DATABASE", "churn_platform")
    mysql_user: str = os.getenv("MYSQL_USER", "churn_user")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "churn_password")

    model_artifact_dir: str = os.getenv(
        "MODEL_ARTIFACT_DIR", "artifacts"
    )
    default_feature_version: str = os.getenv("DEFAULT_FEATURE_VERSION", "v1")


settings = Settings()
