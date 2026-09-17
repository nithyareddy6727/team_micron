CREATE TABLE IF NOT EXISTS events (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  event_type ENUM('session','usage','ticket','payment_failed','payment_succeeded','other') NOT NULL,
  event_ts DATETIME NOT NULL,
  event_value DECIMAL(12,4) NULL,
  source VARCHAR(32) NULL,
  metadata_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_events_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  INDEX idx_events_customer_ts (customer_id, event_ts),
  INDEX idx_events_type_ts (event_type, event_ts),
  INDEX idx_events_ts (event_ts)
) ENGINE=InnoDB;
