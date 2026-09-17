from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from utils.paths import DEFAULT_CUSTOMERS_PATH


EXPECTED_DATASET_ROWS = 7043

@dataclass(frozen=True)
class CustomerSearchResult:
    total: int
    customers: list[dict[str, Any]]


class DatasetService:
    def __init__(self, csv_path: Path = DEFAULT_CUSTOMERS_PATH) -> None:
        self._csv_path = csv_path
        self._frame: pd.DataFrame | None = None

    def load(self) -> pd.DataFrame:
        if self._frame is not None:
            return self._frame

        if not self._csv_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self._csv_path}")

        frame = pd.read_csv(self._csv_path)
        frame.columns = [str(column).strip().lower() for column in frame.columns]

        if "customer_id" not in frame.columns:
            raise ValueError("Dataset must contain customer_id")

        frame = frame.drop_duplicates(subset=["customer_id"], keep="last").copy()
        frame["customer_id"] = frame["customer_id"].astype(str).str.strip()
        frame = frame.set_index("customer_id", drop=False)

        if len(frame) != EXPECTED_DATASET_ROWS:
            raise ValueError(f"Canonical dataset must contain exactly {EXPECTED_DATASET_ROWS} rows; found {len(frame)}")

        if "monthly_charge" in frame.columns and "monthly_charges" not in frame.columns:
            frame["monthly_charges"] = frame["monthly_charge"]
        if "tenure_in_months" in frame.columns and "tenure" not in frame.columns:
            frame["tenure"] = frame["tenure_in_months"]
        if "contract" in frame.columns and "contract_type" not in frame.columns:
            frame["contract_type"] = frame["contract"]
        if "city" in frame.columns and "name" not in frame.columns:
            frame["name"] = frame["city"].fillna("").astype(str).where(frame["city"].notna(), frame["state"].fillna("").astype(str))
        if "email" not in frame.columns:
            state_part = frame["state"].fillna("unknown").astype(str).str.lower().str.replace(r"[^a-z0-9]+", "", regex=True)
            frame["email"] = frame["customer_id"].str.lower() + "@" + state_part + ".local"

        self._frame = frame
        return self._frame

    @property
    def frame(self) -> pd.DataFrame:
        return self.load()

    def total_customers(self) -> int:
        return int(len(self.frame))

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        customer_id = str(customer_id).strip()
        if not customer_id:
            return None
        if customer_id not in self.frame.index:
            return None
        return self._normalize_customer_record(self.frame.loc[customer_id].to_dict())

    def get_customer_features(self, customer_id: str) -> dict[str, Any] | None:
        customer = self.get_customer(customer_id)
        if customer is None:
            return None
        return dict(customer)

    def search_customers(self, limit: int = 100, offset: int = 0, search: str | None = None) -> CustomerSearchResult:
        safe_limit = max(1, int(limit))
        safe_offset = max(0, int(offset))
        query = (search or "").strip().lower()

        rows = self.frame.copy()
        if query:
            searchable_columns = [
                column
                for column in ["customer_id", "name", "email", "city", "state", "contract_type", "offer", "customer_status", "churn_label"]
                if column in rows.columns
            ]
            if searchable_columns:
                mask = False
                for column in searchable_columns:
                    mask = mask | rows[column].astype(str).str.lower().str.contains(query, na=False)
                rows = rows.loc[mask]

        total = int(len(rows))
        page = rows.iloc[safe_offset : safe_offset + safe_limit]
        customers = [self._normalize_customer_record(record) for record in page.to_dict(orient="records")]
        return CustomerSearchResult(total=total, customers=customers)

    def _normalize_customer_record(self, record: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(record)
        normalized["customer_id"] = str(normalized.get("customer_id", "")).strip()
        if "name" not in normalized or normalized.get("name") in (None, ""):
            city = str(normalized.get("city", "")).strip()
            state = str(normalized.get("state", "")).strip()
            normalized["name"] = ", ".join([part for part in [city, state] if part]) or normalized["customer_id"]
        if "email" not in normalized or normalized.get("email") in (None, ""):
            state = str(normalized.get("state", "unknown")).strip().lower().replace(" ", "")
            normalized["email"] = f"{normalized['customer_id'].lower()}@{state or 'local'}.local"
        if "monthly_charges" not in normalized and "monthly_charge" in normalized:
            normalized["monthly_charges"] = normalized["monthly_charge"]
        if "tenure" not in normalized and "tenure_in_months" in normalized:
            normalized["tenure"] = normalized["tenure_in_months"]
        if "contract_type" not in normalized and "contract" in normalized:
            normalized["contract_type"] = normalized["contract"]
        return normalized


@lru_cache(maxsize=1)
def get_dataset_service() -> DatasetService:
    return DatasetService()


dataset_service = get_dataset_service()
