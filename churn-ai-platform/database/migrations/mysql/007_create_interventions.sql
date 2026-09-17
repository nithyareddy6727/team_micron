CREATE TABLE IF NOT EXISTS interventions (
  intervention_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  prediction_id BIGINT NOT NULL,
  customer_id BIGINT NOT NULL,
  action_type ENUM('discount','call','email','service_credit','none') NOT NULL,
  action_owner VARCHAR(64) NULL,
  action_ts DATETIME NOT NULL,
  action_cost DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  action_status ENUM('planned','executed','failed','cancelled') NOT NULL DEFAULT 'planned',
  notes VARCHAR(512) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_interventions_prediction FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id),
  CONSTRAINT fk_interventions_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  CONSTRAINT chk_interventions_cost_nonnegative CHECK (action_cost >= 0),
  INDEX idx_interventions_customer_ts (customer_id, action_ts),
  INDEX idx_interventions_status_ts (action_status, action_ts),
  INDEX idx_interventions_prediction (prediction_id)
) ENGINE=InnoDB;
