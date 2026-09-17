CREATE TABLE IF NOT EXISTS auth_users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  email VARCHAR(191) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role ENUM('admin','analyst','operator') NOT NULL DEFAULT 'operator',
  failed_login_attempts INT NOT NULL DEFAULT 0,
  lockout_until DATETIME NULL,
  refresh_token_hash VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_auth_users_role (role),
  INDEX idx_auth_users_lockout (lockout_until)
) ENGINE=InnoDB;
