CREATE TABLE IF NOT EXISTS predictions (
  prediction_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  prediction_ts DATETIME NOT NULL,
  horizon_days INT NOT NULL,
  score DECIMAL(8,6) NOT NULL,
  risk_band ENUM('low','medium','high') NOT NULL,
  model_version VARCHAR(64) NOT NULL,
  feature_version VARCHAR(32) NOT NULL,
  feature_date DATE NOT NULL,
  explainability_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_predictions_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  CONSTRAINT fk_predictions_model_feature FOREIGN KEY (model_version, feature_version)
    REFERENCES model_registry(model_version, feature_version),
  CONSTRAINT chk_predictions_score CHECK (score >= 0.0 AND score <= 1.0),
  CONSTRAINT chk_predictions_horizon CHECK (horizon_days > 0),
  INDEX idx_predictions_customer_ts (customer_id, prediction_ts),
  INDEX idx_predictions_risk_ts (risk_band, prediction_ts),
  INDEX idx_predictions_model_ts (model_version, prediction_ts)
) ENGINE=InnoDB;
