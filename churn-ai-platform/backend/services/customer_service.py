from __future__ import annotations

from typing import Any

from services.dataset_service import dataset_service


class CustomerService:
    def get_customers(self, limit: int = 100, offset: int = 0, search: str | None = None) -> tuple[int, list[dict[str, Any]]]:
        result = dataset_service.search_customers(limit=limit, offset=offset, search=search)
        customers: list[dict[str, Any]] = []
        for row in result.customers:
            customer_id = str(row.get("customer_id") or row.get("id") or "").strip()
            customers.append(
                {
                    "id": customer_id,
                    "customer_id": customer_id,
                    "name": str(row.get("name") or customer_id),
                    "email": str(row.get("email") or ""),
                    "age": int(float(row.get("age") or 0)),
                    "gender": str(row.get("gender") or "Unknown"),
                    "tenure": int(float(row.get("tenure") or 0)),
                    "monthly_charges": float(row.get("monthly_charges") or 0.0),
                    "contract_type": str(row.get("contract_type") or "Unknown"),
                }
            )
        return result.total, customers
