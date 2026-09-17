# Grafana Monitoring Setup

This folder contains Grafana provisioning and dashboard assets for FastAPI + Prometheus monitoring.

## 1. Connect Grafana to Prometheus

Provisioned datasource file:
- infra/monitoring/grafana/provisioning/datasources/prometheus.yml

Default URL used:
- http://prometheus:9090

If Grafana runs outside Docker compose, update the URL to your reachable Prometheus address.

## 2. Dashboard Provisioning

Provisioned dashboard provider:
- infra/monitoring/grafana/provisioning/dashboards/dashboards.yml

Dashboard JSON:
- infra/monitoring/grafana/dashboards/churn-system-overview.json

Dashboard UID:
- churn-api-monitoring

## 3. Dashboard Structure

Dashboard: Churn Platform - API Monitoring

Sections and panels:
- Requests Per Second (Time series)
- API Response Time (Time series: p50/p95)
- Error Count (5m by Handler) (Bar chart)
- System Health Gauge (Success %) (Gauge)
- Error Rate (%) (Time series)

## 4. Query Examples (PromQL)

Request count / throughput (RPS):
- sum(rate(http_requests_total{handler!="/metrics"}[1m]))

RPS by endpoint:
- sum by (handler) (rate(http_requests_total{handler!="/metrics"}[1m]))

API response latency p95:
- histogram_quantile(0.95, sum by (le) (rate(http_request_duration_highr_seconds_bucket{handler!="/metrics"}[5m])))

API response latency p50:
- histogram_quantile(0.50, sum by (le) (rate(http_request_duration_highr_seconds_bucket{handler!="/metrics"}[5m])))

Error count by endpoint (5m):
- sum by (handler) (increase(http_requests_total{status=~"4xx|5xx",handler!="/metrics"}[5m]))

5xx error rate (%):
- 100 * (sum(rate(http_requests_total{status=~"5xx",handler!="/metrics"}[5m])) / clamp_min(sum(rate(http_requests_total{handler!="/metrics"}[5m])), 0.0001))

System health score (% success):
- 100 * (1 - (sum(rate(http_requests_total{status=~"5xx",handler!="/metrics"}[5m])) / clamp_min(sum(rate(http_requests_total{handler!="/metrics"}[5m])), 0.0001)))

## 5. Notes

- Your FastAPI app exposes Prometheus scrape metrics at GET /metrics.
- Your app-level JSON metrics endpoint is available at GET /metrics/app.
- The latency histogram metric name follows instrumentator defaults: http_request_duration_highr_seconds_bucket.
