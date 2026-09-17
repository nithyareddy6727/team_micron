CREATE TABLE IF NOT EXISTS prediction_events (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id VARCHAR(64) NOT NULL,
  score DECIMAL(8,6) NOT NULL,
  prediction TINYINT NOT NULL,
  model_version VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  run_id VARCHAR(64) NOT NULL,
  INDEX idx_prediction_events_customer (customer_id),
  INDEX idx_prediction_events_run_id (run_id),
  INDEX idx_prediction_events_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
