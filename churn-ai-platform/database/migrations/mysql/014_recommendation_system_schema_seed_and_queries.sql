-- Recommendation System MySQL Schema + Seed Data + Sample Queries
-- Target: MySQL 8+

-- ============================================================
-- 1) TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
  user_id BIGINT UNSIGNED NOT NULL,
  email VARCHAR(255) NOT NULL,
  full_name VARCHAR(160) NOT NULL,
  country_code CHAR(2) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_users_email (email),
  KEY idx_users_active_created (is_active, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS items (
  item_id BIGINT UNSIGNED NOT NULL,
  sku VARCHAR(64) NOT NULL,
  item_name VARCHAR(255) NOT NULL,
  category VARCHAR(120) NOT NULL,
  price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (item_id),
  UNIQUE KEY uq_items_sku (sku),
  KEY idx_items_category_active (category, is_active),
  KEY idx_items_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS interactions (
  interaction_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  item_id BIGINT UNSIGNED NOT NULL,
  interaction_type ENUM('view','click','cart','purchase','like','rating') NOT NULL,
  interaction_value DECIMAL(10,4) NOT NULL DEFAULT 1.0000,
  event_ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  context_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (interaction_id),
  CONSTRAINT fk_interactions_user
    FOREIGN KEY (user_id) REFERENCES users (user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_interactions_item
    FOREIGN KEY (item_id) REFERENCES items (item_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  KEY idx_interactions_user_ts (user_id, event_ts DESC),
  KEY idx_interactions_item_ts (item_id, event_ts DESC),
  KEY idx_interactions_type_ts (interaction_type, event_ts DESC),
  KEY idx_interactions_user_item (user_id, item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS recommendations (
  recommendation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  item_id BIGINT UNSIGNED NOT NULL,
  model_version VARCHAR(64) NOT NULL,
  score DECIMAL(10,6) NOT NULL,
  rank_position INT UNSIGNED NOT NULL,
  source VARCHAR(64) NOT NULL DEFAULT 'fastapi-cf',
  generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NULL,
  served_at DATETIME NULL,
  clicked_at DATETIME NULL,
  PRIMARY KEY (recommendation_id),
  CONSTRAINT fk_recommendations_user
    FOREIGN KEY (user_id) REFERENCES users (user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_recommendations_item
    FOREIGN KEY (item_id) REFERENCES items (item_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  UNIQUE KEY uq_recommendation_snapshot (user_id, item_id, generated_at),
  KEY idx_recommendations_user_generated (user_id, generated_at DESC),
  KEY idx_recommendations_user_rank (user_id, rank_position),
  KEY idx_recommendations_model_generated (model_version, generated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 2) SEED DATA
-- ============================================================

INSERT INTO users (user_id, email, full_name, country_code)
VALUES
  (1001, 'alice@example.com', 'Alice Sharma', 'IN'),
  (1002, 'bob@example.com', 'Bob Verma', 'IN'),
  (1003, 'charlie@example.com', 'Charlie Roy', 'US')
ON DUPLICATE KEY UPDATE
  email = VALUES(email),
  full_name = VALUES(full_name),
  country_code = VALUES(country_code),
  updated_at = CURRENT_TIMESTAMP;


INSERT INTO items (item_id, sku, item_name, category, price)
VALUES
  (2001, 'SKU-TSHIRT-001', 'Classic T-Shirt', 'apparel', 19.99),
  (2002, 'SKU-JEANS-002', 'Blue Jeans', 'apparel', 49.99),
  (2003, 'SKU-SHOES-003', 'Running Shoes', 'footwear', 79.99),
  (2004, 'SKU-WATCH-004', 'Digital Watch', 'accessories', 59.99),
  (2005, 'SKU-BAG-005', 'Travel Backpack', 'accessories', 39.99),
  (2006, 'SKU-SOCKS-006', 'Sports Socks', 'footwear', 9.99)
ON DUPLICATE KEY UPDATE
  sku = VALUES(sku),
  item_name = VALUES(item_name),
  category = VALUES(category),
  price = VALUES(price),
  updated_at = CURRENT_TIMESTAMP;


INSERT INTO interactions (user_id, item_id, interaction_type, interaction_value, event_ts, context_json)
VALUES
  (1001, 2001, 'view', 1.0, NOW() - INTERVAL 10 DAY, JSON_OBJECT('device', 'mobile')),
  (1001, 2002, 'click', 1.2, NOW() - INTERVAL 9 DAY, JSON_OBJECT('device', 'mobile')),
  (1001, 2003, 'purchase', 5.0, NOW() - INTERVAL 6 DAY, JSON_OBJECT('payment', 'card')),
  (1001, 2004, 'view', 1.0, NOW() - INTERVAL 2 DAY, JSON_OBJECT('device', 'web')),
  (1002, 2001, 'view', 1.0, NOW() - INTERVAL 8 DAY, JSON_OBJECT('device', 'web')),
  (1002, 2005, 'cart', 2.0, NOW() - INTERVAL 4 DAY, JSON_OBJECT('device', 'web')),
  (1002, 2006, 'purchase', 4.0, NOW() - INTERVAL 1 DAY, JSON_OBJECT('payment', 'upi')),
  (1003, 2002, 'click', 1.1, NOW() - INTERVAL 7 DAY, JSON_OBJECT('device', 'mobile')),
  (1003, 2004, 'like', 2.5, NOW() - INTERVAL 3 DAY, JSON_OBJECT('channel', 'email')),
  (1003, 2005, 'purchase', 5.0, NOW() - INTERVAL 1 DAY, JSON_OBJECT('payment', 'card'))
ON DUPLICATE KEY UPDATE
  interaction_value = VALUES(interaction_value),
  event_ts = VALUES(event_ts),
  context_json = VALUES(context_json);


INSERT INTO recommendations (user_id, item_id, model_version, score, rank_position, source, generated_at)
VALUES
  (1001, 2005, 'cf-cosine-v1', 0.923100, 1, 'fastapi-cf', NOW()),
  (1001, 2006, 'cf-cosine-v1', 0.811200, 2, 'fastapi-cf', NOW()),
  (1002, 2003, 'cf-cosine-v1', 0.887700, 1, 'fastapi-cf', NOW()),
  (1002, 2004, 'cf-cosine-v1', 0.755400, 2, 'fastapi-cf', NOW())
ON DUPLICATE KEY UPDATE
  model_version = VALUES(model_version),
  score = VALUES(score),
  rank_position = VALUES(rank_position),
  source = VALUES(source),
  generated_at = VALUES(generated_at);


-- ============================================================
-- 3) SAMPLE QUERIES
-- ============================================================

-- Q1: Get latest top-N recommendations for one user
-- Replace 1001 and 5 as needed.
SELECT
  r.user_id,
  r.item_id,
  i.item_name,
  i.category,
  r.score,
  r.rank_position,
  r.model_version,
  r.generated_at
FROM recommendations r
JOIN items i ON i.item_id = r.item_id
WHERE r.user_id = 1001
ORDER BY r.generated_at DESC, r.rank_position ASC
LIMIT 5;


-- Q2: User interaction history (recent first)
SELECT
  it.user_id,
  it.item_id,
  i.item_name,
  it.interaction_type,
  it.interaction_value,
  it.event_ts
FROM interactions it
JOIN items i ON i.item_id = it.item_id
WHERE it.user_id = 1001
ORDER BY it.event_ts DESC
LIMIT 50;


-- Q3: CTR proxy for recommendations (clicked vs served)
SELECT
  DATE(generated_at) AS rec_date,
  COUNT(*) AS total_recommendations,
  SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) AS clicked,
  ROUND(
    SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
    4
  ) AS ctr
FROM recommendations
GROUP BY DATE(generated_at)
ORDER BY rec_date DESC;


-- Q4: Top popular items by weighted interactions
SELECT
  i.item_id,
  i.item_name,
  i.category,
  ROUND(SUM(it.interaction_value), 2) AS weighted_interactions
FROM interactions it
JOIN items i ON i.item_id = it.item_id
GROUP BY i.item_id, i.item_name, i.category
ORDER BY weighted_interactions DESC
LIMIT 10;


-- Q5: Clear and re-insert recommendation snapshot for one user
-- Useful when backend writes fresh recommendations.
-- DELETE FROM recommendations WHERE user_id = 1001;
-- INSERT INTO recommendations (user_id, item_id, model_version, score, rank_position, source)
-- VALUES
--   (1001, 2004, 'cf-cosine-v2', 0.901122, 1, 'fastapi-cf'),
--   (1001, 2006, 'cf-cosine-v2', 0.822341, 2, 'fastapi-cf');
