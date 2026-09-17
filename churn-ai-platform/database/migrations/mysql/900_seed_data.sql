INSERT INTO customers (customer_id, external_ref, full_name, email, country_code, segment, status, created_at)
VALUES
  (1001, 'EXT-1001', 'Alice Carter', 'alice@example.com', 'US', 'enterprise', 'active', '2024-01-10 09:00:00'),
  (1002, 'EXT-1002', 'Bob Singh', 'bob@example.com', 'IN', 'smb', 'active', '2024-03-15 10:30:00'),
  (1003, 'EXT-1003', 'Carla Diaz', 'carla@example.com', 'BR', 'mid_market', 'active', '2024-06-01 08:10:00')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

INSERT INTO subscriptions (customer_id, plan_code, billing_cycle, status, start_date, end_date, monthly_mrr, payment_failures_30d)
VALUES
  (1001, 'PRO', 'monthly', 'active', '2024-01-10', NULL, 199.00, 0),
  (1002, 'BASIC', 'monthly', 'active', '2024-03-15', NULL, 49.00, 1),
  (1003, 'TEAM', 'monthly', 'past_due', '2024-06-01', NULL, 99.00, 2)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

INSERT INTO events (customer_id, event_type, event_ts, event_value, source)
VALUES
  (1001, 'session', '2026-03-20 09:00:00', 1, 'web'),
  (1001, 'usage', '2026-03-20 09:01:00', 35, 'web'),
  (1001, 'session', '2026-03-25 10:00:00', 1, 'web'),
  (1001, 'ticket', '2026-03-28 14:20:00', 1, 'support'),
  (1002, 'session', '2026-03-10 11:00:00', 1, 'web'),
  (1002, 'usage', '2026-03-10 11:05:00', 20, 'web'),
  (1002, 'payment_failed', '2026-03-19 08:00:00', 1, 'billing'),
  (1002, 'session', '2026-03-30 13:00:00', 1, 'mobile'),
  (1003, 'session', '2026-02-15 15:00:00', 1, 'web'),
  (1003, 'usage', '2026-02-15 15:03:00', 40, 'web'),
  (1003, 'payment_failed', '2026-03-05 08:30:00', 1, 'billing'),
  (1003, 'ticket', '2026-03-22 16:00:00', 1, 'support');

INSERT INTO model_registry (
  model_version, model_type, training_data_start, training_data_end, validation_metric,
  validation_score, threshold_high, threshold_medium, feature_version, artifact_uri, status
)
VALUES
  ('churn_xgb_v1', 'xgboost', '2025-01-01', '2026-02-28', 'pr_auc', 0.741200, 0.700000, 0.400000, 'v1', 's3://models/churn_xgb_v1', 'production')
ON DUPLICATE KEY UPDATE
  validation_score = VALUES(validation_score),
  threshold_high = VALUES(threshold_high),
  threshold_medium = VALUES(threshold_medium),
  status = VALUES(status),
  updated_at = CURRENT_TIMESTAMP;
