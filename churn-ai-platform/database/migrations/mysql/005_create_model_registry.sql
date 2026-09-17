CREATE TABLE IF NOT EXISTS model_registry (
  model_version VARCHAR(64) PRIMARY KEY,
  model_type VARCHAR(64) NOT NULL,
  training_data_start DATE NOT NULL,
  training_data_end DATE NOT NULL,
  validation_metric VARCHAR(64) NOT NULL,
  validation_score DECIMAL(10,6) NOT NULL,
  threshold_high DECIMAL(8,6) NOT NULL,
  threshold_medium DECIMAL(8,6) NOT NULL,
  feature_version VARCHAR(32) NOT NULL,
  artifact_uri VARCHAR(256) NOT NULL,
  status ENUM('staging','production','archived') NOT NULL DEFAULT 'staging',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_model_registry_thresholds CHECK (threshold_high >= threshold_medium),
  UNIQUE KEY uq_model_feature_version (model_version, feature_version),
  INDEX idx_model_registry_status_created (status, created_at)
) ENGINE=InnoDB;
