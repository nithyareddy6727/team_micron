CREATE TABLE IF NOT EXISTS outcomes (
  outcome_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  prediction_id BIGINT NULL,
  evaluation_date DATE NOT NULL,
  churned_flag TINYINT NOT NULL,
  retained_revenue DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  observation_window_days INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_outcomes_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  CONSTRAINT fk_outcomes_prediction FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id),
  CONSTRAINT chk_outcomes_churned_flag CHECK (churned_flag IN (0, 1)),
  CONSTRAINT chk_outcomes_revenue_nonnegative CHECK (retained_revenue >= 0),
  CONSTRAINT chk_outcomes_window_positive CHECK (observation_window_days > 0),
  UNIQUE KEY uq_outcomes_customer_eval_window (customer_id, evaluation_date, observation_window_days),
  INDEX idx_outcomes_eval_date (evaluation_date),
  INDEX idx_outcomes_churned_eval (churned_flag, evaluation_date)
) ENGINE=InnoDB;
