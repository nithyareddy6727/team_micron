from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import joblib

from utils.paths import (
    DEFAULT_MODEL_PATH,
    DEFAULT_PREPROCESSOR_PATH,
    FALLBACK_MODEL_PATH,
    FALLBACK_PREPROCESSOR_PATH,
)


class LoadedArtifacts:
    def __init__(
        self,
        model: Any,
        preprocessor: Any | None,
        model_path: Path,
        preprocessor_path: Path | None,
        model_version: str,
        artifact_sha256: str,
    ):
        self.model = model
        self.preprocessor = preprocessor
        self.model_path = model_path
        self.preprocessor_path = preprocessor_path
        self.model_version = model_version
        self.artifact_sha256 = artifact_sha256


class ModelLoader:
    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _resolve_model_version(model_path: Path, artifact_sha256: str) -> str:
        env_version = os.getenv("MODEL_VERSION")
        if env_version:
            return env_version

        return f"{model_path.stem}-{artifact_sha256[:12]}"

    @staticmethod
    def _resolve_model_path() -> Path:
        env_path = os.getenv("MODEL_PATH")
        if env_path:
            return Path(env_path)
        if DEFAULT_MODEL_PATH.exists():
            return DEFAULT_MODEL_PATH
        return FALLBACK_MODEL_PATH

    @staticmethod
    def _resolve_preprocessor_path() -> Path:
        env_path = os.getenv("PREPROCESSOR_PATH")
        if env_path:
            return Path(env_path)
        if DEFAULT_PREPROCESSOR_PATH.exists():
            return DEFAULT_PREPROCESSOR_PATH
        return FALLBACK_PREPROCESSOR_PATH

    @classmethod
    def load(cls) -> LoadedArtifacts:
        logger = logging.getLogger("churn_app")
        model_path = cls._resolve_model_path()
        if not model_path.exists():
            message = (
                f"Model artifact not found at '{model_path}'. "
                "Set MODEL_PATH to a valid .pkl artifact or place the model at the default artifacts path."
            )
            logger.error("model_load_failed | reason=missing_artifact | path=%s", model_path)
            raise RuntimeError(message)

        try:
            model = joblib.load(model_path)
        except Exception as exc:
            logger.error("model_load_failed | reason=deserialization_error | path=%s | message=%s", model_path, str(exc))
            raise RuntimeError(f"Failed to deserialize model artifact at '{model_path}': {exc}") from exc

        artifact_sha256 = cls._compute_sha256(model_path)
        model_version = cls._resolve_model_version(model_path, artifact_sha256)

        preprocessor = None
        preprocessor_path_used: Path | None = None
        preprocessor_path = cls._resolve_preprocessor_path()
        if preprocessor_path.exists():
            preprocessor = joblib.load(preprocessor_path)
            preprocessor_path_used = preprocessor_path

        artifacts = LoadedArtifacts(
            model=model,
            preprocessor=preprocessor,
            model_path=model_path,
            preprocessor_path=preprocessor_path_used,
            model_version=model_version,
            artifact_sha256=artifact_sha256,
        )

        logger.info(
            "model_load_success | model_path=%s | model_version=%s | artifact_sha256=%s | preprocessor_path=%s",
            artifacts.model_path,
            artifacts.model_version,
            artifacts.artifact_sha256,
            artifacts.preprocessor_path,
        )
        return artifacts
