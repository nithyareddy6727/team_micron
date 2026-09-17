CREATE TABLE IF NOT EXISTS drift_metrics (
  drift_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  computed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  feature_name VARCHAR(128) NOT NULL,
  feature_version VARCHAR(32) NOT NULL,
  model_version VARCHAR(64) NOT NULL,
  psi_value DECIMAL(10,6) NOT NULL,
  threshold_warning DECIMAL(10,6) NOT NULL DEFAULT 0.200000,
  threshold_retrain DECIMAL(10,6) NOT NULL DEFAULT 0.300000,
  status ENUM('ok','warning','retrain') NOT NULL,
  baseline_start DATE NOT NULL,
  baseline_end DATE NOT NULL,
  compare_start DATE NOT NULL,
  compare_end DATE NOT NULL,
  metadata_json JSON NULL,
  INDEX idx_drift_metrics_computed (computed_at),
  INDEX idx_drift_metrics_feature (feature_name, computed_at),
  INDEX idx_drift_metrics_status (status, computed_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS retraining_runs (
  run_id VARCHAR(64) PRIMARY KEY,
  triggered_by ENUM('manual','schedule','drift') NOT NULL,
  trigger_reason VARCHAR(256) NULL,
  trigger_value DECIMAL(10,6) NULL,
  status ENUM('running','completed','failed') NOT NULL,
  model_version VARCHAR(64) NULL,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  details_json JSON NULL,
  INDEX idx_retraining_runs_status_time (status, started_at)
) ENGINE=InnoDB;
