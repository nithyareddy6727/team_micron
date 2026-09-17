CREATE TABLE IF NOT EXISTS customers (
  customer_id BIGINT PRIMARY KEY,
  external_ref VARCHAR(64) UNIQUE,
  full_name VARCHAR(128),
  email VARCHAR(128) UNIQUE,
  country_code CHAR(2),
  segment VARCHAR(32),
  status ENUM('active','inactive','churned') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_customers_status_created (status, created_at),
  INDEX idx_customers_segment_created (segment, created_at)
) ENGINE=InnoDB;
