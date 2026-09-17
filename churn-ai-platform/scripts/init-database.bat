@echo off
REM Database Initialization Script for Churn AI Platform (Windows)
REM Usage: init-database.bat [root-password]

setlocal enabledelayedexpansion

set DB_HOST=localhost
set DB_PORT=3306
set DB_USER=churn_user
set DB_PASSWORD=churn_password
set DB_NAME=churn_platform
set MYSQL_ROOT_PASSWORD=%1

echo ================================
echo Churn AI Platform - Database Setup
echo ================================
echo.

REM Create database and user
echo Creating database and user...

if "%MYSQL_ROOT_PASSWORD%"=="" (
    mysql -u root --skip-password -e "CREATE DATABASE IF NOT EXISTS %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS '%DB_USER%'@'%DB_HOST%' IDENTIFIED BY '%DB_PASSWORD%'; GRANT ALL PRIVILEGES ON %DB_NAME%.* TO '%DB_USER%'@'%DB_HOST%'; FLUSH PRIVILEGES;" 2>nul
) else (
    mysql -u root -p%MYSQL_ROOT_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS '%DB_USER%'@'%DB_HOST%' IDENTIFIED BY '%DB_PASSWORD%'; GRANT ALL PRIVILEGES ON %DB_NAME%.* TO '%DB_USER%'@'%DB_HOST%'; FLUSH PRIVILEGES;" 2>nul
)

if errorlevel 1 (
    echo X Failed to create database and user. Check MySQL credentials.
    pause
    exit /b 1
)

echo ✓ Database and user created
echo.

REM Run migrations
echo Running migrations...
set MIGRATION_DIR=churn-ai-platform\database\migrations\mysql

for %%F in (
    001_create_customers.sql
    002_create_subscriptions.sql
    003_create_events.sql
    004_create_features_daily.sql
    005_create_model_registry.sql
    006_create_predictions.sql
    007_create_interventions.sql
    008_create_outcomes.sql
    009_create_scoring_jobs.sql
    010_create_experiment_tables.sql
    011_create_drift_and_retraining_tables.sql
    012_add_recommendations.sql
    900_seed_data.sql
) do (
    set migration_file=!MIGRATION_DIR!\%%F
    if exist !migration_file! (
        echo   - Running %%F...
        mysql -u %DB_USER% -p%DB_PASSWORD% %DB_NAME% < !migration_file! 2>nul
        if errorlevel 0 (
            echo     ✓ %%F
        ) else (
            echo     ~ %%F ^(may have failed or already exists^)
        )
    ) else (
        echo     ~ %%F not found
    )
)

echo.
echo ================================
echo ✓ Database initialization complete!
echo ================================
echo.
echo Connection details:
echo   Host: %DB_HOST%
echo   Port: %DB_PORT%
echo   User: %DB_USER%
echo   Database: %DB_NAME%
echo.
echo Test connection:
echo   mysql -u %DB_USER% -p%DB_PASSWORD% -h %DB_HOST% -P %DB_PORT% %DB_NAME%
echo.
pause
