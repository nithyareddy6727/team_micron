#!/bin/bash
# Database Initialization Script for Churn AI Platform
# Usage: ./init-database.sh [root-password]

MYSQL_ROOT_PASSWORD="${1:-}"
DB_HOST="localhost"
DB_PORT="3306"
DB_USER="churn_user"
DB_PASSWORD="churn_password"
DB_NAME="churn_platform"

echo "================================"
echo "Churn AI Platform - Database Setup"
echo "================================"
echo ""

# Create database and user
if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    echo "Creating database and user (no root password)..."
    mysql -u root --skip-password -e "
        CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE USER IF NOT EXISTS '$DB_USER'@'$DB_HOST' IDENTIFIED BY '$DB_PASSWORD';
        GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'$DB_HOST';
        FLUSH PRIVILEGES;
    " 2>/dev/null
else
    echo "Creating database and user (with root password)..."
    mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "
        CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE USER IF NOT EXISTS '$DB_USER'@'$DB_HOST' IDENTIFIED BY '$DB_PASSWORD';
        GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'$DB_HOST';
        FLUSH PRIVILEGES;
    " 2>/dev/null
fi

if [ $? -ne 0 ]; then
    echo "❌ Failed to create database and user. Check MySQL credentials."
    exit 1
fi

echo "✅ Database and user created"
echo ""

# Run migrations
echo "Running migrations..."
MIGRATION_DIR="churn-ai-platform/database/migrations/mysql"

migrations=(
    "001_create_customers.sql"
    "002_create_subscriptions.sql"
    "003_create_events.sql"
    "004_create_features_daily.sql"
    "005_create_model_registry.sql"
    "006_create_predictions.sql"
    "007_create_interventions.sql"
    "008_create_outcomes.sql"
    "009_create_scoring_jobs.sql"
    "010_create_experiment_tables.sql"
    "011_create_drift_and_retraining_tables.sql"
    "012_add_recommendations.sql"
    "900_seed_data.sql"
)

for migration in "${migrations[@]}"; do
    migration_file="$MIGRATION_DIR/$migration"
    if [ -f "$migration_file" ]; then
        echo "  - Running $migration..."
        mysql -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$migration_file" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "    ✅ $migration"
        else
            echo "    ⚠️  $migration (may have failed or already exists)"
        fi
    else
        echo "    ⚠️  $migration_file not found"
    fi
done

echo ""
echo "================================"
echo "✅ Database initialization complete!"
echo "================================"
echo ""
echo "Connection details:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  User: $DB_USER"
echo "  Database: $DB_NAME"
echo ""
echo "Test connection:"
echo "  mysql -u $DB_USER -p$DB_PASSWORD -h $DB_HOST -P $DB_PORT $DB_NAME"
