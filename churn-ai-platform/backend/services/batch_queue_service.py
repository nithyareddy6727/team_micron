from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import threading
from typing import Any, Callable
from uuid import uuid4


BatchRunFn = Callable[[dict[str, Any], bool, bool], dict[str, Any]]


class BatchQueueService:
    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="batch-predict")
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def submit(
        self,
        rows: list[dict[str, Any]],
        run_prediction: BatchRunFn,
        return_proba: bool,
        explain: bool,
    ) -> dict[str, Any]:
        job_id = str(uuid4())
        job = {
            "job_id": job_id,
            "status": "queued",
            "submitted_at": self._now_iso(),
            "started_at": None,
            "completed_at": None,
            "total_rows": len(rows),
            "processed_rows": 0,
            "successful_rows": 0,
            "failed_rows": 0,
            "results": [],
            "errors": [],
        }

        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(self._process_job, job_id, rows, run_prediction, return_proba, explain)
        return dict(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return None if job is None else dict(job)

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id].update(updates)

    def _append_result(self, job_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["results"].append(payload)

    def _append_error(self, job_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["errors"].append(payload)

    def _inc_progress(self, job_id: str, successful: bool) -> None:
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["processed_rows"] += 1
            if successful:
                self._jobs[job_id]["successful_rows"] += 1
            else:
                self._jobs[job_id]["failed_rows"] += 1

    def _process_job(
        self,
        job_id: str,
        rows: list[dict[str, Any]],
        run_prediction: BatchRunFn,
        return_proba: bool,
        explain: bool,
    ) -> None:
        self._update_job(job_id, status="processing", started_at=self._now_iso())

        for index, row in enumerate(rows):
            customer_id = str(row.get("customer_id") or row.get("features", {}).get("customer_id") or "manual-input")
            features = dict(row.get("features") or {})
            if "customer_id" not in features and customer_id:
                features["customer_id"] = customer_id

            try:
                result = run_prediction(features, return_proba, explain)
                self._append_result(
                    job_id,
                    {
                        "row_index": index,
                        "customer_id": customer_id,
                        "prediction": int(result["prediction"]),
                        "probability": float(result["probability"]),
                        "risk": str(result["risk"]),
                        "confidence": float(result["confidence"]),
                        "latency_ms": float(result["latency_ms"]),
                        "model_version": str(result["model_version"]),
                        "explanation_text": result.get("explanation_text"),
                        "primary_driver": result.get("primary_driver"),
                        "recommended_action": result.get("recommended_action"),
                    },
                )
                self._inc_progress(job_id, successful=True)
            except Exception as exc:
                self._append_error(
                    job_id,
                    {
                        "row_index": index,
                        "customer_id": customer_id,
                        "message": str(exc),
                    },
                )
                self._inc_progress(job_id, successful=False)

        final_state = "completed"
        job = self.get_job(job_id)
        if job and job["failed_rows"] == job["total_rows"]:
            final_state = "failed"

        self._update_job(job_id, status=final_state, completed_at=self._now_iso())


batch_queue_service = BatchQueueService()
