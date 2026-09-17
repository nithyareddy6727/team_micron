CREATE TABLE IF NOT EXISTS features_daily (
  feature_date DATE NOT NULL,
  customer_id BIGINT NOT NULL,
  recency_days INT NULL,
  sessions_7d INT NOT NULL DEFAULT 0,
  sessions_30d INT NOT NULL DEFAULT 0,
  usage_drop_30d_pct DECIMAL(7,3) NOT NULL DEFAULT 0.000,
  tickets_30d INT NOT NULL DEFAULT 0,
  payment_failures_30d INT NOT NULL DEFAULT 0,
  tenure_days INT NOT NULL DEFAULT 0,
  feature_version VARCHAR(32) NOT NULL,
  computed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (feature_date, customer_id, feature_version),
  CONSTRAINT fk_features_daily_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  CONSTRAINT chk_features_daily_nonnegative CHECK (
    sessions_7d >= 0 AND sessions_30d >= 0 AND tickets_30d >= 0 AND payment_failures_30d >= 0 AND tenure_days >= 0
  ),
  INDEX idx_features_daily_customer_date (customer_id, feature_date),
  INDEX idx_features_daily_date_version (feature_date, feature_version)
) ENGINE=InnoDB;
