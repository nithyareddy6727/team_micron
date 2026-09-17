-- ============================================================
-- Churn AI Platform — MySQL Database Schema
-- ============================================================
-- Production tables:
--   customers       — canonical customer profile store
--   predictions     — model inference history and audit trail
--   model_metadata  — model registry and deployment metadata
--   audit_logs      — operational audit and event history
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    email VARCHAR(191) NOT NULL,
    age INT NOT NULL DEFAULT 0,
    gender VARCHAR(32) NOT NULL DEFAULT 'Unknown',
    tenure INT NOT NULL DEFAULT 0,
    monthly_charges DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    contract_type VARCHAR(64) NOT NULL DEFAULT 'Month-to-month',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_customers_email (email),
    INDEX idx_customers_created_at (created_at),
    INDEX idx_customers_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    customer_id VARCHAR(64) NOT NULL,
    prediction TINYINT(1) NOT NULL,
    probability DECIMAL(10, 6) NOT NULL,
    confidence_score DECIMAL(10, 6) NOT NULL DEFAULT 0.000000,
    latency_ms DECIMAL(10, 3) NOT NULL DEFAULT 0.000,
    risk_level VARCHAR(32) NOT NULL,
    top_features_json JSON NULL,
    model_version VARCHAR(64) NOT NULL DEFAULT '1.0',
    `timestamp` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_predictions_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON DELETE CASCADE,
    INDEX idx_predictions_customer_id (customer_id),
    INDEX idx_predictions_timestamp (`timestamp`),
    INDEX idx_predictions_risk_level (risk_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS prediction_events (
    event_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    customer_id VARCHAR(64) NOT NULL,
    prediction TINYINT(1) NOT NULL,
    probability DECIMAL(10, 6) NOT NULL,
    confidence_score DECIMAL(10, 6) NOT NULL DEFAULT 0.000000,
    latency_ms DECIMAL(10, 3) NOT NULL DEFAULT 0.000,
    risk_level VARCHAR(32) NOT NULL,
    top_features_json JSON NULL,
    input_features_json JSON NULL,
    model_version VARCHAR(64) NOT NULL DEFAULT '1.0',
    `timestamp` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_prediction_events_timestamp (`timestamp`),
    INDEX idx_prediction_events_risk_level (risk_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS model_metadata (
    metadata_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(128) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    artifact_path VARCHAR(255) NOT NULL,
    artifact_sha256 CHAR(64) NOT NULL,
    feature_version VARCHAR(64) NOT NULL DEFAULT 'v1',
    training_started_at DATETIME(6) NULL,
    trained_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    metrics_json JSON NULL,
    notes TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_model_metadata_name_version (model_name, model_version),
    INDEX idx_model_metadata_sha256 (artifact_sha256),
    INDEX idx_model_metadata_active (is_active),
    INDEX idx_model_metadata_trained_at (trained_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_type VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    payload_json JSON NULL,
    actor VARCHAR(128) NULL,
    `timestamp` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_audit_logs_entity_id (entity_id),
    INDEX idx_audit_logs_timestamp (`timestamp`),
    INDEX idx_audit_logs_event_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
