-- Add recommended_action column to predictions table for storing system recommendations
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS recommended_action VARCHAR(64) NULL AFTER risk_band;
