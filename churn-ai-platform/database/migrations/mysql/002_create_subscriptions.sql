CREATE TABLE IF NOT EXISTS subscriptions (
  subscription_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  plan_code VARCHAR(32) NOT NULL,
  billing_cycle ENUM('monthly','quarterly','yearly') NOT NULL DEFAULT 'monthly',
  status ENUM('active','past_due','cancelled','paused') NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NULL,
  monthly_mrr DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  payment_failures_30d INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_subscriptions_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  CONSTRAINT chk_subscriptions_mrr_nonnegative CHECK (monthly_mrr >= 0),
  INDEX idx_subscriptions_customer_status (customer_id, status),
  INDEX idx_subscriptions_status_end (status, end_date),
  INDEX idx_subscriptions_customer_start (customer_id, start_date)
) ENGINE=InnoDB;
