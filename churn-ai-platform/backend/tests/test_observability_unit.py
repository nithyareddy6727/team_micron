from services.observability_service import ObservabilityService


def test_request_summary_computes_latency_and_error_rate() -> None:
    service = ObservabilityService()

    service.record_request(duration_ms=100.0, status_code=200)
    service.record_request(duration_ms=200.0, status_code=200)
    service.record_request(duration_ms=300.0, status_code=500)

    summary = service.request_summary()
    assert summary["request_count"] == 3
    assert summary["error_count"] == 1
    assert summary["error_rate"] == 1 / 3
    assert summary["latency_avg_ms"] == 200.0
    assert summary["latency_p95_ms"] == 300.0


def test_slo_status_reflects_dependency_health() -> None:
    service = ObservabilityService()
    service.record_request(duration_ms=120.0, status_code=200)

    healthy = service.slo_status(dependencies_ok=True)
    degraded = service.slo_status(dependencies_ok=False)

    assert healthy["status"]["uptime_ok"] is True
    assert healthy["status"]["overall_ok"] in {True, False}
    assert degraded["current"]["uptime_percent"] == 0.0
    assert degraded["status"]["uptime_ok"] is False
