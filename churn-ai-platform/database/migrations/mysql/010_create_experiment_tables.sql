CREATE TABLE IF NOT EXISTS experiments (
  experiment_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL UNIQUE,
  description VARCHAR(512) NULL,
  start_date DATE NOT NULL,
  end_date DATE NULL,
  is_active TINYINT NOT NULL DEFAULT 1,
  cost_per_treated DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_experiments_active (is_active, start_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS experiment_assignments (
  assignment_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  experiment_id BIGINT NOT NULL,
  customer_id BIGINT NOT NULL,
  group_name ENUM('treated','control') NOT NULL,
  prediction_id BIGINT NULL,
  assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_experiment_assignments_experiment FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id),
  CONSTRAINT fk_experiment_assignments_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  CONSTRAINT fk_experiment_assignments_prediction FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id),
  UNIQUE KEY uq_experiment_customer (experiment_id, customer_id),
  INDEX idx_experiment_assignments_group (experiment_id, group_name, assigned_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS experiment_outcomes (
  outcome_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  experiment_id BIGINT NOT NULL,
  customer_id BIGINT NOT NULL,
  group_name ENUM('treated','control') NOT NULL,
  evaluation_date DATE NOT NULL,
  churned_flag TINYINT NOT NULL,
  retained_revenue DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  intervention_cost DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_experiment_outcomes_experiment FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id),
  CONSTRAINT fk_experiment_outcomes_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  CONSTRAINT chk_experiment_outcomes_churn CHECK (churned_flag IN (0, 1)),
  UNIQUE KEY uq_experiment_outcome_customer_date (experiment_id, customer_id, evaluation_date),
  INDEX idx_experiment_outcomes_eval (experiment_id, group_name, evaluation_date)
) ENGINE=InnoDB;
