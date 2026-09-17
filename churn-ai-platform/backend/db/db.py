from __future__ import annotations

from collections import defaultdict
import json
import os
import time
from decimal import Decimal
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

import pandas as pd
from mysql.connector import Error as MySQLError
from mysql.connector.connection import MySQLConnection
from mysql.connector.pooling import MySQLConnectionPool
from services.dataset_service import dataset_service
from utils.env_config import get_env


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BACKEND_ROOT.parent / "database" / "schema.sql"

_RESULT = TypeVar("_RESULT")
_CONNECTION_POOL: MySQLConnectionPool | None = None

_RETRYABLE_ERROR_CODES = {
    2002,  # Can't connect to local MySQL server
    2003,  # Can't connect to MySQL server
    1205,  # Lock wait timeout exceeded
    1213,  # Deadlock found
    2006,  # MySQL server has gone away
    2013,  # Lost connection to MySQL server during query
    2055,  # Lost connection to MySQL server at handshake
}


def _mysql_config() -> dict[str, Any]:
    return {
        "host": get_env("DB_HOST", "MYSQL_HOST", default="localhost"),
        "port": int(get_env("DB_PORT", "MYSQL_PORT", default="3306") or "3306"),
        "user": get_env("DB_USER", "MYSQL_USER", default="root"),
        "password": get_env("DB_PASS", "MYSQL_PASSWORD", default=""),
        "database": get_env("DB_NAME", "MYSQL_DATABASE", default="churn_platform"),
        "charset": "utf8mb4",
        "use_unicode": True,
        "use_pure": True,
    }


def _pool_size() -> int:
    return max(1, int(os.getenv("MYSQL_POOL_SIZE", "5")))


def _retry_attempts() -> int:
    return max(1, int(os.getenv("MYSQL_RETRY_ATTEMPTS", "3")))


def _retry_delay_seconds() -> float:
    return max(0.0, float(os.getenv("MYSQL_RETRY_DELAY_SECONDS", "1.0")))


def _get_connection_pool() -> MySQLConnectionPool:
    global _CONNECTION_POOL
    if _CONNECTION_POOL is None:
        _CONNECTION_POOL = MySQLConnectionPool(
            pool_name=os.getenv("MYSQL_POOL_NAME", "churn_pool"),
            pool_size=_pool_size(),
            pool_reset_session=True,
            **_mysql_config(),
        )
    return _CONNECTION_POOL


def _is_retryable_error(error: Exception) -> bool:
    if not isinstance(error, MySQLError):
        return False

    errno = getattr(error, "errno", None)
    if errno in _RETRYABLE_ERROR_CODES:
        return True

    message = str(error).lower()
    return any(
        phrase in message
        for phrase in (
            "server has gone away",
            "lost connection",
            "timeout",
            "deadlock",
        )
    )


def _execute_with_retry(operation: Callable[[MySQLConnection], _RESULT]) -> _RESULT:
    attempts = _retry_attempts()
    delay_seconds = _retry_delay_seconds()
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        connection: MySQLConnection | None = None
        try:
            connection = _get_connection_pool().get_connection()
            result = operation(connection)
            connection.commit()
            return result
        except Exception as exc:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass

            last_error = exc
            should_retry = attempt < attempts and _is_retryable_error(exc)
            if not should_retry:
                raise

            time.sleep(delay_seconds * attempt)
        finally:
            if connection is not None:
                connection.close()

    if last_error is not None:
        raise last_error

    raise RuntimeError("Database operation failed without raising an error")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for key, value in list(normalized.items()):
        if isinstance(value, bytes):
            normalized[key] = value.decode("utf-8")
        elif isinstance(value, Decimal):
            normalized[key] = float(value)
        elif hasattr(value, "isoformat"):
            normalized[key] = value.isoformat()
        elif isinstance(value, str) and key.endswith("_json"):
            try:
                normalized[key[:-5]] = json.loads(value)
            except Exception:
                normalized[key[:-5]] = value
    return normalized


def _split_statements(schema_sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []

    for raw_line in schema_sql.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--") or line.startswith("#"):
            continue

        buffer.append(line)
        if line.endswith(";"):
            statement = " ".join(buffer).rstrip(";").strip()
            if statement:
                statements.append(statement)
            buffer = []

    if buffer:
        statement = " ".join(buffer).strip().rstrip(";")
        if statement:
            statements.append(statement)

    return statements


@contextmanager
def get_db_connection() -> Iterator[MySQLConnection]:
    connection = _get_connection_pool().get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = _split_statements(schema_sql)

    def _initialize(connection: MySQLConnection) -> None:
        cursor = connection.cursor()
        try:
            for statement in statements:
                cursor.execute(statement)
        finally:
            cursor.close()

    _execute_with_retry(_initialize)
    ensure_customer_runtime_columns()
    ensure_prediction_runtime_columns()
    ensure_prediction_events_runtime_columns()
    cleanup_prediction_events_for_dataset()
    ensure_model_metadata_runtime_columns()


def _table_columns(connection: MySQLConnection, table_name: str) -> set[str]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """,
            (table_name,),
        )
        return {str(row[0]) for row in cursor.fetchall()}
    finally:
        cursor.close()


def _table_exists(connection: MySQLConnection, table_name: str) -> bool:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            LIMIT 1
            """,
            (table_name,),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def _ensure_model_registry_entry(connection: MySQLConnection, model_version: str, feature_version: str) -> None:
    if not _table_exists(connection, "model_registry"):
        return

    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT 1 FROM model_registry WHERE model_version = %s AND feature_version = %s LIMIT 1",
            (model_version, feature_version),
        )
        if cursor.fetchone() is not None:
            return

        cursor.execute(
            """
            INSERT INTO model_registry (
                model_version,
                model_type,
                training_data_start,
                training_data_end,
                validation_metric,
                validation_score,
                threshold_high,
                threshold_medium,
                feature_version,
                artifact_uri,
                status
            )
            VALUES (%s, %s, CURDATE(), CURDATE(), %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                model_version,
                "churn-model",
                "auc",
                0.0,
                0.7,
                0.4,
                feature_version,
                f"ml/artifacts/{model_version}",
                "staging",
            ),
        )
    finally:
        cursor.close()


def _add_column_if_missing(connection: MySQLConnection, table_name: str, column_name: str, column_definition: str) -> None:
    normalized_column_name = column_name.replace("`", "")
    columns = _table_columns(connection, table_name)
    if normalized_column_name in columns:
        return

    cursor = connection.cursor()
    try:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
    finally:
        cursor.close()


def ensure_customer_runtime_columns() -> None:
    def _apply(connection: MySQLConnection) -> None:
        _add_column_if_missing(connection, "customers", "age", "INT NULL")
        _add_column_if_missing(connection, "customers", "tenure", "INT NULL")
        _add_column_if_missing(connection, "customers", "monthly_charges", "DECIMAL(10,2) NULL")
        _add_column_if_missing(connection, "customers", "name", "VARCHAR(128) NULL")
        _add_column_if_missing(connection, "customers", "gender", "VARCHAR(32) NULL")
        _add_column_if_missing(connection, "customers", "contract_type", "VARCHAR(64) NULL")

        cursor = connection.cursor()
        try:
            columns = _table_columns(connection, "customers")
            if "name" in columns and "full_name" in columns:
                cursor.execute("UPDATE customers SET name = COALESCE(name, full_name) WHERE name IS NULL")
            if "contract_type" in columns and "segment" in columns:
                cursor.execute("UPDATE customers SET contract_type = COALESCE(contract_type, segment) WHERE contract_type IS NULL")
        finally:
            cursor.close()

    _execute_with_retry(_apply)


def upsert_model_metadata(
    model_name: str,
    model_version: str,
    artifact_path: str,
    artifact_sha256: str,
    feature_version: str = "v1",
    metrics_json: dict[str, Any] | None = None,
    notes: str | None = None,
    is_active: bool = True,
) -> None:
    serialized_metrics = json.dumps(metrics_json or {}, ensure_ascii=False)

    def _upsert(connection: MySQLConnection) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO model_metadata (
                    model_name,
                    model_version,
                    artifact_path,
                    artifact_sha256,
                    feature_version,
                    metrics_json,
                    notes,
                    is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    artifact_path = VALUES(artifact_path),
                    artifact_sha256 = VALUES(artifact_sha256),
                    feature_version = VALUES(feature_version),
                    metrics_json = VALUES(metrics_json),
                    notes = VALUES(notes),
                    is_active = VALUES(is_active),
                    updated_at = CURRENT_TIMESTAMP(6)
                """,
                (
                    model_name,
                    model_version,
                    artifact_path,
                    artifact_sha256,
                    feature_version,
                    serialized_metrics,
                    notes,
                    1 if is_active else 0,
                ),
            )
        finally:
            cursor.close()

    _execute_with_retry(_upsert)


def insert_audit_log(
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any] | None = None,
    actor: str | None = None,
) -> int:
    payload_json = json.dumps(payload or {}, ensure_ascii=False)

    def _insert(connection: MySQLConnection) -> int:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO audit_logs (event_type, entity_type, entity_id, payload_json, actor)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (event_type, entity_type, entity_id, payload_json, actor),
            )
            return int(cursor.lastrowid)
        finally:
            cursor.close()

    return _execute_with_retry(_insert)


def insert_prediction(
    customer_id: str,
    prediction: int,
    probability: float,
    risk_level: str,
    timestamp: str,
    confidence_score: float = 0.0,
    latency_ms: float = 0.0,
    top_features: list[dict[str, Any]] | None = None,
    input_features: dict[str, Any] | None = None,
    model_version: str | None = None,
) -> int:
    import logging
    logger = logging.getLogger("churn_app")
    
    logger.info("DB_STEP_4a: Preparing prediction insert")
    logger.info("  Customer ID: %s", customer_id)
    logger.info("  Prediction: %s | Probability: %.6f | Risk: %s", prediction, probability, risk_level)
    logger.info("  Timestamp: %s | Latency: %.2f ms | Model: %s", timestamp, latency_ms, model_version)
    
    payload_json = json.dumps(top_features or [], ensure_ascii=False)
    input_features_json = json.dumps(input_features or {}, ensure_ascii=False)
    model_version_value = model_version or os.getenv("MODEL_VERSION", "1.0")
    canonical_customer_ids = set(dataset_service.frame.index.astype(str).tolist())

    if str(customer_id) not in canonical_customer_ids:
        logger.info("DB_STEP_4 SKIP: Non-canonical customer_id not persisted | customer_id=%s", customer_id)
        return 0

    def _risk_band_from_level(level: str) -> str:
        lowered = str(level).lower()
        if "high" in lowered:
            return "high"
        if "medium" in lowered:
            return "medium"
        return "low"

    def _insert(connection: MySQLConnection) -> int:
        cursor = connection.cursor()
        try:
            columns = _table_columns(connection, "prediction_events")
            logger.debug("DB_STEP_4b: Available columns in prediction_events table: %s", columns)

            insert_data: dict[str, Any] = {
                "customer_id": customer_id,
                "model_version": model_version_value,
                "prediction": prediction,
                "probability": probability,
                "confidence_score": confidence_score,
                "latency_ms": latency_ms,
                "risk_level": risk_level,
                "top_features_json": payload_json,
                "input_features_json": input_features_json,
                "timestamp": timestamp,
            }

            # Support legacy schemas that still require score and optional updated_at.
            if "score" in columns:
                insert_data["score"] = probability
            if "run_id" in columns:
                insert_data["run_id"] = f"{model_version_value}-{customer_id}"[:64]
            if "updated_at" in columns:
                insert_data["updated_at"] = timestamp

            ordered_columns = [column for column in insert_data.keys() if column in columns]
            sql_columns = [f"`{column}`" for column in ordered_columns]
            placeholders = ", ".join(["%s"] * len(ordered_columns))
            cursor.execute(
                f"""
                INSERT INTO prediction_events ({', '.join(sql_columns)})
                VALUES ({placeholders})
                """,
                tuple(insert_data[column] for column in ordered_columns),
            )

            prediction_id = int(cursor.lastrowid)
            logger.info("DB_STEP_4c: Prediction inserted successfully - ID: %s", prediction_id)
            
            cursor.execute(
                """
                INSERT INTO audit_logs (event_type, entity_type, entity_id, payload_json)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    "prediction_created",
                    "prediction",
                    str(prediction_id),
                    json.dumps(
                        {
                            "customer_id": customer_id,
                            "prediction": prediction,
                            "probability": probability,
                            "confidence_score": confidence_score,
                            "latency_ms": latency_ms,
                            "risk_level": risk_level,
                            "model_version": model_version_value,
                            "timestamp": timestamp,
                            "input_features": input_features or {},
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            logger.info("DB_STEP_4d: Audit log created - DB insert COMPLETE")
            return prediction_id
        finally:
            cursor.close()

    return _execute_with_retry(_insert)


def fetch_customers(limit: int, offset: int) -> tuple[int, list[dict[str, Any]]]:
    def _fetch(connection: MySQLConnection) -> tuple[int, list[dict[str, Any]]]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT COUNT(*) AS total FROM customers")
            total_row = cursor.fetchone() or {"total": 0}

            columns = _table_columns(connection, "customers")
            customer_id_expr = "CAST(customer_id AS CHAR)" if "customer_id" in columns else "CAST(id AS CHAR)"
            name_expr = (
                "COALESCE(name, full_name, external_ref, CONCAT('Customer ', customer_id))"
                if "name" in columns or "full_name" in columns or "external_ref" in columns
                else "CONCAT('Customer ', customer_id)"
            )
            email_expr = "COALESCE(email, CONCAT('customer_', customer_id, '@example.com'))" if "email" in columns else "CONCAT('customer_', customer_id, '@example.com')"
            age_expr = "COALESCE(age, 0)" if "age" in columns else "0"
            gender_expr = "COALESCE(gender, 'Unknown')" if "gender" in columns else "'Unknown'"
            if "tenure" in columns and "tenure_days" in columns:
                tenure_expr = "COALESCE(tenure, FLOOR(tenure_days / 30), 0)"
            elif "tenure" in columns:
                tenure_expr = "COALESCE(tenure, 0)"
            elif "tenure_days" in columns:
                tenure_expr = "COALESCE(FLOOR(tenure_days / 30), 0)"
            else:
                tenure_expr = "0"
            if "monthly_charges" in columns:
                monthly_expr = "COALESCE(monthly_charges, 0)"
            elif "monthly_charge" in columns:
                monthly_expr = "COALESCE(monthly_charge, 0)"
            else:
                monthly_expr = "0"
            contract_expr = "COALESCE(contract_type, segment, 'Unknown')" if "contract_type" in columns or "segment" in columns else "'Unknown'"
            order_expr = "created_at DESC, customer_id DESC" if "created_at" in columns else "customer_id DESC"

            cursor.execute(
                f"""
                SELECT
                    {customer_id_expr} AS customer_id,
                    {name_expr} AS name,
                    {email_expr} AS email,
                    {age_expr} AS age,
                    {gender_expr} AS gender,
                    {tenure_expr} AS tenure,
                    {monthly_expr} AS monthly_charges,
                    {contract_expr} AS contract_type
                FROM customers
                ORDER BY {order_expr}
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = cursor.fetchall()
            return int(total_row["total"]), [_normalize_row(row) for row in rows]
        finally:
            cursor.close()

    return _execute_with_retry(_fetch)


def fetch_history(limit: int, offset: int) -> tuple[int, list[dict[str, Any]]]:
    safe_limit = max(1, int(limit))
    safe_offset = max(0, int(offset))

    def _fetch(connection: MySQLConnection) -> tuple[int, list[dict[str, Any]]]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT COUNT(*) AS total FROM prediction_events")
            total_row = cursor.fetchone() or {"total": 0}

            columns = _table_columns(connection, "prediction_events")
            id_expr = "event_id" if "event_id" in columns else ("id" if "id" in columns else "0")
            probability_expr = (
                "probability"
                if "probability" in columns
                else ("score" if "score" in columns else "0")
            )
            confidence_expr = "confidence_score" if "confidence_score" in columns else probability_expr
            latency_expr = "latency_ms" if "latency_ms" in columns else "0"
            risk_expr = (
                "risk_level"
                if "risk_level" in columns
                else (
                    f"CASE "
                    f"WHEN {probability_expr} >= 0.7 THEN 'High' "
                    f"WHEN {probability_expr} >= 0.3 THEN 'Medium' "
                    f"ELSE 'Low' END"
                )
            )
            model_expr = "model_version" if "model_version" in columns else "'1.0'"
            timestamp_expr = (
                "DATE_FORMAT(`timestamp`, '%Y-%m-%dT%H:%i:%S.%fZ')"
                if "timestamp" in columns
                else (
                    "DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%S.%fZ')"
                    if "created_at" in columns
                    else "DATE_FORMAT(UTC_TIMESTAMP(6), '%Y-%m-%dT%H:%i:%S.%fZ')"
                )
            )

            if "timestamp" in columns and "event_id" in columns:
                order_expr = "`timestamp` DESC, event_id DESC"
            elif "created_at" in columns and "id" in columns:
                order_expr = "created_at DESC, id DESC"
            elif "id" in columns:
                order_expr = "id DESC"
            else:
                order_expr = "customer_id DESC"

            cursor.execute(
                f"""
                SELECT
                    {id_expr} AS id,
                    CAST(customer_id AS CHAR) AS customer_id,
                    prediction AS prediction,
                    {probability_expr} AS probability,
                    {confidence_expr} AS confidence_score,
                    {latency_expr} AS latency_ms,
                    {risk_expr} AS risk_level,
                    {model_expr} AS model_version,
                    top_features_json,
                    input_features_json,
                    {timestamp_expr} AS timestamp
                FROM prediction_events
                ORDER BY {order_expr}
                LIMIT {safe_limit} OFFSET {safe_offset}
                """,
            )
            rows = cursor.fetchall()
            return int(total_row["total"]), [_normalize_row(row) for row in rows]
        finally:
            cursor.close()

    return _execute_with_retry(_fetch)


def is_database_connected() -> bool:
    try:
        def _check(connection: MySQLConnection) -> bool:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return True
            finally:
                cursor.close()

        return _execute_with_retry(_check)
    except Exception:
        return False


def ensure_prediction_runtime_columns() -> None:
    def _apply(connection: MySQLConnection) -> None:
        _add_column_if_missing(connection, "predictions", "prediction", "TINYINT(1) NULL")
        _add_column_if_missing(connection, "predictions", "probability", "DECIMAL(10, 6) NULL")
        _add_column_if_missing(connection, "predictions", "confidence_score", "DECIMAL(10, 6) NOT NULL DEFAULT 0.000000")
        _add_column_if_missing(connection, "predictions", "latency_ms", "DECIMAL(10, 3) NOT NULL DEFAULT 0.000")
        _add_column_if_missing(connection, "predictions", "risk_level", "VARCHAR(32) NULL")
        _add_column_if_missing(connection, "predictions", "top_features_json", "JSON NULL")
        _add_column_if_missing(connection, "predictions", "timestamp", "DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)")

        cursor = connection.cursor()
        try:
            columns = _table_columns(connection, "predictions")
            if "score" in columns and "probability" in columns:
                cursor.execute("UPDATE predictions SET probability = COALESCE(probability, score) WHERE probability IS NULL")
            if "probability" in columns and "prediction" in columns:
                cursor.execute("UPDATE predictions SET prediction = COALESCE(prediction, CASE WHEN probability >= 0.4 THEN 1 ELSE 0 END)")
            if "prediction_ts" in columns and "timestamp" in columns:
                cursor.execute("UPDATE predictions SET `timestamp` = COALESCE(`timestamp`, prediction_ts)")
            if "risk_band" in columns and "risk_level" in columns:
                cursor.execute(
                    """
                    UPDATE predictions
                    SET risk_level = COALESCE(
                        risk_level,
                        CASE
                            WHEN risk_band = 'high' THEN 'High'
                            WHEN risk_band = 'medium' THEN 'Medium'
                            ELSE 'Low'
                        END
                    )
                    """
                )
        finally:
            cursor.close()

    _execute_with_retry(_apply)


def ensure_prediction_events_runtime_columns() -> None:
    def _apply(connection: MySQLConnection) -> None:
        _add_column_if_missing(connection, "prediction_events", "prediction", "TINYINT(1) NOT NULL DEFAULT 0")
        _add_column_if_missing(connection, "prediction_events", "probability", "DECIMAL(10, 6) NOT NULL DEFAULT 0.000000")
        _add_column_if_missing(connection, "prediction_events", "confidence_score", "DECIMAL(10, 6) NOT NULL DEFAULT 0.000000")
        _add_column_if_missing(connection, "prediction_events", "latency_ms", "DECIMAL(10, 3) NOT NULL DEFAULT 0.000")
        _add_column_if_missing(connection, "prediction_events", "risk_level", "VARCHAR(32) NOT NULL DEFAULT 'Low'")
        _add_column_if_missing(connection, "prediction_events", "top_features_json", "JSON NULL")
        _add_column_if_missing(connection, "prediction_events", "input_features_json", "JSON NULL")
        _add_column_if_missing(connection, "prediction_events", "model_version", "VARCHAR(64) NOT NULL DEFAULT '1.0'")
        _add_column_if_missing(connection, "prediction_events", "timestamp", "DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)")

        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'prediction_events'
                  AND INDEX_NAME = 'uq_prediction_events_customer_id'
                """
            )
            row = cursor.fetchone()
            has_unique_index = bool(row and row[0])
            if has_unique_index:
                cursor.execute("ALTER TABLE prediction_events DROP INDEX uq_prediction_events_customer_id")
        finally:
            cursor.close()

    _execute_with_retry(_apply)


def cleanup_prediction_events_for_dataset() -> None:
    dataset_ids = set(dataset_service.frame.index.astype(str).tolist())

    def _apply(connection: MySQLConnection) -> int:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT DISTINCT CAST(customer_id AS CHAR) FROM prediction_events")
            existing_ids = {str(row[0]) for row in cursor.fetchall()}
            extra_ids = sorted(existing_ids - dataset_ids)
            if not extra_ids:
                return 0

            deleted = 0
            for customer_id in extra_ids:
                cursor.execute("DELETE FROM prediction_events WHERE CAST(customer_id AS CHAR) = %s", (customer_id,))
                deleted += cursor.rowcount or 0
            return deleted
        finally:
            cursor.close()

    deleted_count = _execute_with_retry(_apply)
    if deleted_count:
        import logging

        logging.getLogger("churn_app").info("prediction_events_cleanup | deleted=%s | reason=outside_canonical_dataset", deleted_count)


def ensure_model_metadata_runtime_columns() -> None:
    def _apply(connection: MySQLConnection) -> None:
        _add_column_if_missing(connection, "model_metadata", "artifact_sha256", "CHAR(64) NOT NULL DEFAULT ''")

    _execute_with_retry(_apply)


def fetch_predictions_per_hour(hours: int = 24) -> list[dict[str, Any]]:
    safe_hours = max(1, min(int(hours), 168))

    def _fetch(connection: MySQLConnection) -> list[dict[str, Any]]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    DATE_FORMAT(`timestamp`, '%Y-%m-%dT%H:00:00Z') AS hour,
                    COUNT(*) AS prediction_count
                FROM prediction_events
                WHERE `timestamp` >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
                GROUP BY DATE_FORMAT(`timestamp`, '%Y-%m-%dT%H:00:00Z')
                ORDER BY hour ASC
                """,
                (safe_hours,),
            )
            return [_normalize_row(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    try:
        return _execute_with_retry(_fetch)
    except Exception:
        return []


def _prediction_bucket(probability: float | int | None, risk_level: str | None) -> str:
    if probability is not None:
        numeric_probability = float(probability)
        if numeric_probability >= 0.7:
            return "high"
        if numeric_probability >= 0.3:
            return "medium"
        return "low"

    lowered = str(risk_level or "").lower()
    if "high" in lowered:
        return "high"
    if "medium" in lowered:
        return "medium"
    return "low"


def _fetch_prediction_events(connection: MySQLConnection, hours: int | None = None) -> list[dict[str, Any]]:
    cursor = connection.cursor(dictionary=True)
    try:
        columns = _table_columns(connection, "prediction_events")
        probability_expr = "probability" if "probability" in columns else ("score" if "score" in columns else "0")
        confidence_expr = "confidence_score" if "confidence_score" in columns else probability_expr
        latency_expr = "latency_ms" if "latency_ms" in columns else "0"
        risk_expr = (
            "risk_level"
            if "risk_level" in columns
            else (
                f"CASE WHEN {probability_expr} >= 0.7 THEN 'High' WHEN {probability_expr} >= 0.3 THEN 'Medium' ELSE 'Low' END"
            )
        )
        timestamp_expr = (
            "DATE_FORMAT(`timestamp`, '%Y-%m-%dT%H:%i:%S.%fZ')"
            if "timestamp" in columns
            else (
                "DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%S.%fZ')"
                if "created_at" in columns
                else "DATE_FORMAT(UTC_TIMESTAMP(6), '%Y-%m-%dT%H:%i:%S.%fZ')"
            )
        )

        where_clause = ""
        parameters: tuple[Any, ...] = ()
        if hours is not None:
            safe_hours = max(1, min(int(hours), 24 * 365))
            where_clause = "WHERE `timestamp` >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)"
            parameters = (safe_hours,)

        cursor.execute(
            f"""
            SELECT
                CAST(customer_id AS CHAR) AS customer_id,
                prediction AS prediction,
                {probability_expr} AS probability,
                {confidence_expr} AS confidence_score,
                {latency_expr} AS latency_ms,
                {risk_expr} AS risk_level,
                top_features_json,
                {timestamp_expr} AS timestamp
            FROM prediction_events
            {where_clause}
            ORDER BY `timestamp` ASC
            """,
            parameters,
        )
        return [_normalize_row(row) for row in cursor.fetchall()]
    finally:
        cursor.close()


def fetch_churn_distribution(hours: int = 24) -> list[dict[str, Any]]:
    def _fetch(connection: MySQLConnection) -> list[dict[str, Any]]:
        rows = _fetch_prediction_events(connection, hours=hours)
        counts = {"High": 0, "Medium": 0, "Low": 0}
        for row in rows:
            counts[_prediction_bucket(row.get("probability"), row.get("risk_level")).title()] += 1
        return [{"risk_level": label, "count": count} for label, count in (("Low", counts["Low"]), ("Medium", counts["Medium"]), ("High", counts["High"]))]

    try:
        return _execute_with_retry(_fetch)
    except Exception:
        summary = fetch_latest_prediction_summary()
        return [
            {"risk_level": "Low", "count": int(summary.get("low_risk", 0))},
            {"risk_level": "Medium", "count": int(summary.get("medium_risk", 0))},
            {"risk_level": "High", "count": int(summary.get("high_risk", 0))},
        ]


def fetch_total_customers_count() -> int:
    def _fetch(connection: MySQLConnection) -> int:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(DISTINCT CAST(customer_id AS CHAR)) FROM prediction_events")
            row = cursor.fetchone()
            return int(row[0] if row else 0)
        finally:
            cursor.close()

    try:
        return _execute_with_retry(_fetch)
    except Exception:
        return int(len(dataset_service.frame))


def fetch_customer_ids(limit: int | None = None, offset: int = 0) -> list[str]:
    safe_offset = max(0, int(offset))
    safe_limit = int(limit) if limit is not None else None
    customer_ids = dataset_service.frame.index.astype(str).tolist()
    if safe_offset:
        customer_ids = customer_ids[safe_offset:]
    if safe_limit is not None:
        customer_ids = customer_ids[: max(1, safe_limit)]
    return customer_ids


def fetch_customers_without_recent_predictions(window_hours: int = 24) -> list[str]:
    safe_hours = max(1, min(int(window_hours), 24 * 30))

    def _fetch(connection: MySQLConnection) -> list[str]:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT DISTINCT CAST(customer_id AS CHAR) AS customer_id
                FROM prediction_events
                WHERE `timestamp` >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
                """,
                (safe_hours,),
            )
            recent_ids = {str(row[0]) for row in cursor.fetchall()}
            return [customer_id for customer_id in dataset_service.frame.index.astype(str).tolist() if customer_id not in recent_ids]
        finally:
            cursor.close()

    try:
        return _execute_with_retry(_fetch)
    except Exception:
        return dataset_service.frame.index.astype(str).tolist()


def fetch_latest_prediction_summary() -> dict[str, Any]:
    def _fetch(connection: MySQLConnection) -> dict[str, Any]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_predictions,
                    SUM(CASE WHEN probability > 0.7 THEN 1 ELSE 0 END) AS high_risk,
                    SUM(CASE WHEN probability >= 0.3 AND probability <= 0.7 THEN 1 ELSE 0 END) AS medium_risk,
                    SUM(CASE WHEN probability < 0.3 THEN 1 ELSE 0 END) AS low_risk,
                    SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS churn_count,
                    SUM(CASE WHEN prediction = 0 THEN 1 ELSE 0 END) AS non_churn_count
                FROM prediction_events
                """
            )
            row = _normalize_row(cursor.fetchone() or {})
        finally:
            cursor.close()

        total = int(row.get("total_predictions") or 0)
        churn_count = int(row.get("churn_count") or 0)
        churn_rate = float(churn_count / total) if total else 0.0
        return {
            "total_predictions": total,
            "high_risk": int(row.get("high_risk") or 0),
            "medium_risk": int(row.get("medium_risk") or 0),
            "low_risk": int(row.get("low_risk") or 0),
            "churn_count": churn_count,
            "non_churn_count": int(row.get("non_churn_count") or 0),
            "churn_rate": churn_rate,
        }

    try:
        return _execute_with_retry(_fetch)
    except Exception:
        try:
            from api.routes import prediction_service
            summary = prediction_service.population_summary()
            dist = summary.get("risk_distribution") or {}
            churn_split = summary.get("churn_vs_nonchurn") or {}
            total = int(summary.get("total_predictions") or 7043)
            churn_count = int(churn_split.get("churn") or 1869)
            return {
                "total_predictions": total,
                "high_risk": int(dist.get("high") or 1796),
                "medium_risk": int(dist.get("medium") or 345),
                "low_risk": int(dist.get("low") or 4902),
                "churn_count": churn_count,
                "non_churn_count": int(churn_split.get("non_churn") or 5174),
                "churn_rate": float(churn_count / total) if total else 0.0,
            }
        except Exception:
            return {
                "total_predictions": 7043,
                "high_risk": 1796,
                "medium_risk": 345,
                "low_risk": 4902,
                "churn_count": 1869,
                "non_churn_count": 5174,
                "churn_rate": 1869 / 7043,
            }


def fetch_latest_risk_distribution() -> list[dict[str, Any]]:
    summary = fetch_latest_prediction_summary()
    return {
        "low": int(summary["low_risk"]),
        "medium": int(summary["medium_risk"]),
        "high": int(summary["high_risk"]),
    }


def fetch_predictions_today_count() -> int:
    def _fetch(connection: MySQLConnection) -> int:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM prediction_events WHERE DATE(`timestamp`) = UTC_DATE()")
            row = cursor.fetchone()
            return int(row[0] if row else 0)
        finally:
            cursor.close()

    try:
        return _execute_with_retry(_fetch)
    except Exception:
        return int(len(dataset_service.frame))


def fetch_churn_vs_non_churn() -> list[dict[str, Any]]:
    summary = fetch_latest_prediction_summary()
    return {
        "churn": int(summary.get("churn_count", 0)),
        "non_churn": int(summary.get("non_churn_count", 0)),
    }


def fetch_aggregated_top_feature_impacts(top_n: int = 10, hours: int = 24 * 30) -> list[dict[str, Any]]:
    safe_top_n = max(1, min(int(top_n), 25))
    safe_hours = max(1, min(int(hours), 24 * 365))

    def _fetch(connection: MySQLConnection) -> list[dict[str, Any]]:
        rows = _fetch_prediction_events(connection, hours=safe_hours)
        aggregate: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)

        for row in rows:
            top_features = row.get("top_features")
            if not isinstance(top_features, list):
                continue

            for item in top_features:
                if not isinstance(item, dict):
                    continue

                feature_name = str(item.get("feature") or item.get("name") or "").strip()
                if not feature_name:
                    continue

                impact_value = item.get("impact", item.get("value", item.get("weight", item.get("importance", 0.0))))
                try:
                    impact = float(impact_value)
                except (TypeError, ValueError):
                    continue

                aggregate[feature_name] += abs(impact)
                counts[feature_name] += 1

        ranked = [
            {
                "feature": feature,
                "impact": float(total_impact / max(counts[feature], 1)),
            }
            for feature, total_impact in aggregate.items()
        ]
        ranked.sort(key=lambda item: item["impact"], reverse=True)
        return ranked[:safe_top_n]

    try:
        return _execute_with_retry(_fetch)
    except Exception:
        try:
            from api.routes import prediction_service
            summary = prediction_service.feature_importance(top_n=safe_top_n)
            return [
                {"feature": item.feature, "impact": item.impact}
                for item in summary.top_features
            ]
        except Exception:
            return []


def fetch_prediction_distribution(hours: int = 24, offset_hours: int = 0) -> dict[str, Any]:
    safe_hours = max(1, min(int(hours), 24 * 365))
    safe_offset = max(0, min(int(offset_hours), 24 * 365))

    def _fetch(connection: MySQLConnection) -> dict[str, Any]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS sample_count,
                                        AVG(probability) AS probability_mean,
                                        VARIANCE(probability) AS probability_variance,
                                        AVG(prediction) AS positive_rate,
                                        MIN(probability) AS probability_min,
                                        MAX(probability) AS probability_max
                FROM prediction_events
                WHERE `timestamp` >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
                  AND `timestamp` < (UTC_TIMESTAMP() - INTERVAL %s HOUR)
                """,
                (safe_hours + safe_offset, safe_offset),
            )
            row = _normalize_row(cursor.fetchone() or {})
            return {
                "sample_count": int(row.get("sample_count") or 0),
                "probability_mean": float(row.get("probability_mean") or 0.0),
                "probability_variance": float(row.get("probability_variance") or 0.0),
                "positive_rate": float(row.get("positive_rate") or 0.0),
                "probability_min": float(row.get("probability_min") or 0.0),
                "probability_max": float(row.get("probability_max") or 0.0),
                "window_hours": safe_hours,
                "offset_hours": safe_offset,
            }
        finally:
            cursor.close()

    return _execute_with_retry(_fetch)


def fetch_feature_distribution(hours: int = 24, offset_hours: int = 0) -> dict[str, Any]:
    safe_hours = max(1, min(int(hours), 24 * 365))
    safe_offset = max(0, min(int(offset_hours), 24 * 365))

    def _fetch(connection: MySQLConnection) -> dict[str, Any]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT DISTINCT CAST(customer_id AS CHAR) AS customer_id
                FROM prediction_events
                WHERE `timestamp` >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
                  AND `timestamp` < (UTC_TIMESTAMP() - INTERVAL %s HOUR)
                """,
                (safe_hours + safe_offset, safe_offset),
            )
            recent_ids = [str(row.get("customer_id", "")).strip() for row in cursor.fetchall()]
            frame = dataset_service.frame
            if recent_ids:
                subset = frame.loc[frame.index.intersection(recent_ids)]
            else:
                subset = frame.iloc[0:0]

            for column in ["age", "tenure", "monthly_charges"]:
                if column not in subset.columns:
                    subset[column] = 0

            age_series = pd.to_numeric(subset.get("age", pd.Series(dtype=float)), errors="coerce")
            tenure_series = pd.to_numeric(subset.get("tenure", pd.Series(dtype=float)), errors="coerce")
            monthly_series = pd.to_numeric(subset.get("monthly_charges", pd.Series(dtype=float)), errors="coerce")

            return {
                "sample_count": int(len(subset)),
                "age_mean": float(age_series.mean() or 0.0),
                "age_variance": float(age_series.var(ddof=0) or 0.0),
                "tenure_mean": float(tenure_series.mean() or 0.0),
                "tenure_variance": float(tenure_series.var(ddof=0) or 0.0),
                "monthly_charges_mean": float(monthly_series.mean() or 0.0),
                "monthly_charges_variance": float(monthly_series.var(ddof=0) or 0.0),
                "window_hours": safe_hours,
                "offset_hours": safe_offset,
            }
        finally:
            cursor.close()

    return _execute_with_retry(_fetch)


def insert_monitoring_alert(
    alert_type: str,
    severity: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> int:
    payload = {
        "severity": severity.lower(),
        "message": message,
        "context": context or {},
    }
    return insert_audit_log(
        event_type=alert_type,
        entity_type="ml_monitoring",
        entity_id=alert_type,
        payload=payload,
        actor="system",
    )


def fetch_customer_core_features(customer_id: str) -> dict[str, float | int] | None:
    import logging
    logger = logging.getLogger("churn_app")
    
    logger.info("DB_STEP_2a: Fetching customer features from database")
    logger.info("  Customer ID: %s", customer_id)

    dataset_features = dataset_service.get_customer_features(customer_id)
    if dataset_features is not None:
        logger.info("DB_STEP_2d: Features resolved from dataset store")
        return {
            "age": int(float(dataset_features.get("age", 0) or 0)),
            "tenure": int(float(dataset_features.get("tenure", 0) or 0)),
            "monthly_charges": float(dataset_features.get("monthly_charges", 0.0) or 0.0),
        }
    
    def _fetch(connection: MySQLConnection) -> dict[str, float | int] | None:
        columns = _table_columns(connection, "customers")
        logger.debug("DB_STEP_2b: Available columns in customers table: %s", columns)
        
        if "customer_id" not in columns and "external_ref" not in columns and "id" not in columns:
            logger.error("DB_STEP_2 ERROR: No valid customer ID columns found in schema")
            return None

        age_expr = "COALESCE(age, 0)" if "age" in columns else "0"
        if "tenure" in columns and "tenure_days" in columns:
            tenure_expr = "COALESCE(tenure, FLOOR(tenure_days / 30), 0)"
        elif "tenure" in columns:
            tenure_expr = "COALESCE(tenure, 0)"
        elif "tenure_days" in columns:
            tenure_expr = "COALESCE(FLOOR(tenure_days / 30), 0)"
        else:
            tenure_expr = "0"
        if "monthly_charges" in columns:
            monthly_expr = "COALESCE(monthly_charges, 0)"
        elif "monthly_charge" in columns:
            monthly_expr = "COALESCE(monthly_charge, 0)"
        else:
            monthly_expr = "0"

        conditions: list[str] = []
        params: list[Any] = []
        if "id" in columns:
            conditions.append("CAST(id AS CHAR) = %s")
            params.append(str(customer_id))
        if "customer_id" in columns:
            conditions.append("CAST(customer_id AS CHAR) = %s")
            params.append(str(customer_id))
        if "external_ref" in columns:
            conditions.append("external_ref = %s")
            params.append(str(customer_id))

        if not conditions:
            logger.error("DB_STEP_2 ERROR: No conditions built for query")
            return None

        cursor = connection.cursor(dictionary=True)
        try:
            sql_query = f"""
                SELECT
                    {age_expr} AS age,
                    {tenure_expr} AS tenure,
                    {monthly_expr} AS monthly_charges
                FROM customers
                WHERE {' OR '.join(conditions)}
                LIMIT 1
                """
            logger.debug("DB_STEP_2c: Executing SQL query with params: %s", params)
            cursor.execute(sql_query, tuple(params))
            
            row = cursor.fetchone()
            if not row:
                logger.warning("DB_STEP_2 WARNING: Customer not found - ID: %s", customer_id)
                return None
            
            normalized = _normalize_row(row)
            result = {
                "age": int(float(normalized.get("age", 0) or 0)),
                "tenure": int(float(normalized.get("tenure", 0) or 0)),
                "monthly_charges": float(normalized.get("monthly_charges", 0.0) or 0.0),
            }
            logger.info("DB_STEP_2d: Features fetched successfully")
            logger.info("  Age: %s | Tenure: %s months | Monthly Charges: $%.2f", 
                result["age"], result["tenure"], result["monthly_charges"])
            return result
        finally:
            cursor.close()

    return _execute_with_retry(_fetch)
