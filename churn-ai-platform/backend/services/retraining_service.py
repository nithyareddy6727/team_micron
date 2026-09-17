from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class RetrainingService:
    def __init__(self) -> None:
        self._root = Path(__file__).resolve().parents[2]
        self._script = self._root / "ml" / "service" / "scripts" / "retrain_model.py"
        self._working_dir = self._root / "ml" / "service"

    def retrain(self, force: bool = True, model_type: str = "xgboost", feature_version: str = "v1", horizon_days: int = 30, top_k_pct: float = 0.1) -> dict[str, Any]:
        if not self._script.exists():
            raise FileNotFoundError(f"Retraining script not found: {self._script}")

        command = [
            sys.executable,
            str(self._script),
        ]
        if force:
            command.append("--force")
        command.extend(
            [
                "--model-type",
                model_type,
                "--feature-version",
                feature_version,
                "--horizon-days",
                str(horizon_days),
                "--top-k-pct",
                str(top_k_pct),
            ]
        )

        completed = subprocess.run(
            command,
            cwd=self._working_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()

        parsed_output: dict[str, Any] | None = None
        if stdout:
            try:
                parsed_output = json.loads(stdout.splitlines()[-1])
            except Exception:
                parsed_output = {"raw_stdout": stdout}

        if completed.returncode != 0:
            raise RuntimeError(stderr or stdout or "Retraining failed")

        return {
            "status": "completed",
            "returncode": completed.returncode,
            "output": parsed_output or {"raw_stdout": stdout},
            "stderr": stderr or None,
        }


retraining_service = RetrainingService()