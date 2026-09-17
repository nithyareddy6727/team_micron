CREATE TABLE IF NOT EXISTS users (
  user_id BIGINT PRIMARY KEY,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS items (
  item_id BIGINT PRIMARY KEY,
  name VARCHAR(255) NULL,
  category VARCHAR(120) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS interactions (
  interaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  item_id BIGINT NOT NULL,
  interaction_type VARCHAR(32) NOT NULL,
  interaction_value DECIMAL(10,4) NULL,
  interacted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_interactions_user_time (user_id, interacted_at),
  INDEX idx_interactions_item (item_id),
  CONSTRAINT fk_interactions_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_interactions_item FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recommendations (
  recommendation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  item_id BIGINT NOT NULL,
  score DECIMAL(10,6) NOT NULL,
  rank_position INT NOT NULL,
  source VARCHAR(64) NOT NULL DEFAULT 'ml-service',
  generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_recommendations_user_time (user_id, generated_at),
  INDEX idx_recommendations_item (item_id),
  CONSTRAINT fk_recommendations_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_recommendations_item FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
