CREATE TABLE IF NOT EXISTS scoring_jobs (
  job_id VARCHAR(64) PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  request_id VARCHAR(64) NOT NULL,
  status ENUM('queued','processing','completed','failed') NOT NULL DEFAULT 'queued',
  attempts_made INT NOT NULL DEFAULT 0,
  prediction_id BIGINT NULL,
  result_json JSON NULL,
  error_message VARCHAR(1024) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_scoring_jobs_status_created (status, created_at),
  INDEX idx_scoring_jobs_customer_created (customer_id, created_at)
) ENGINE=InnoDB;
