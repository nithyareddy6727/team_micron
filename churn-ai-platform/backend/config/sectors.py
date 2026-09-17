from __future__ import annotations

from typing import Any

# ============================================================
# Centralized Risk Thresholds
# ============================================================
LOW_RISK_THRESHOLD = 0.30
HIGH_RISK_THRESHOLD = 0.70

def get_risk_tier(probability: float) -> str:
    """Classify calibrated probability into a standard risk tier."""
    if probability < LOW_RISK_THRESHOLD:
        return "Low"
    if probability < HIGH_RISK_THRESHOLD:
        return "Medium"
    return "High"


# ============================================================
# Sector Profiles Configuration
# ============================================================
SECTOR_PROFILES: dict[str, dict[str, Any]] = {
    "saas": {
        "id": "saas",
        "name": "SaaS & Cloud Platforms",
        "badge": "SaaS",
        "description": "B2B software subscriptions, cloud platforms, and developer tooling.",
        "terminology": {
            "customer": "Account / Tenant",
            "customers": "Accounts",
            "monthly_charges": "Monthly Recurring Revenue (MRR)",
            "tenure": "Account Age (Months)",
            "contract_type": "Commitment Tier",
            "action_title": "Customer Success & Retention Play",
            "currency_symbol": "$",
        },
        "field_aliases": {
            "monthly_charges": [
                "mrr",
                "subscription_value",
                "monthly_fee",
                "arr_monthly",
                "license_fee",
                "plan_price",
                "monthly_charge",
                "monthly_charges",
            ],
            "tenure": [
                "account_age_months",
                "months_subscribed",
                "subscription_tenure",
                "tenure_months",
                "tenure_in_months",
                "tenure",
            ],
            "contract_type": [
                "billing_frequency",
                "commitment_tier",
                "plan_duration",
                "contract_length",
                "contract_type",
                "contract",
            ],
            "age": [
                "account_maturity",
                "company_age",
                "admin_age",
                "user_age",
                "age",
            ],
        },
        "driver_labels": {
            "monthly_charges": "Subscription Cost (MRR)",
            "monthly_charge": "Subscription Cost (MRR)",
            "tenure": "Account Maturity / Tenure",
            "tenure_in_months": "Account Maturity / Tenure",
            "contract_type": "Contract Commitment",
            "contract": "Contract Commitment",
            "internet_service": "Cloud Add-on Services",
            "payment_method": "Billing & Payment Method",
            "satisfaction_score": "NPS / Customer Satisfaction",
        },
    },
    "telecom": {
        "id": "telecom",
        "name": "Telecom & Broadband",
        "badge": "Telecom",
        "description": "Mobile network providers, fiber internet, and broadband communications.",
        "terminology": {
            "customer": "Subscriber",
            "customers": "Subscribers",
            "monthly_charges": "Monthly Bill",
            "tenure": "Tenure (Months)",
            "contract_type": "Contract Type",
            "action_title": "Retention Offer & Support Play",
            "currency_symbol": "$",
        },
        "field_aliases": {
            "monthly_charges": [
                "monthly_charges",
                "monthly_charge",
                "bill_amount",
                "monthly_bill",
                "MonthlyCharges",
            ],
            "tenure": [
                "tenure",
                "tenure_in_months",
                "months_with_provider",
                "Tenure",
            ],
            "contract_type": [
                "contract_type",
                "contract",
                "plan_term",
                "Contract",
            ],
            "age": [
                "age",
                "subscriber_age",
                "Age",
            ],
        },
        "driver_labels": {
            "monthly_charges": "Monthly Charges",
            "monthly_charge": "Monthly Charges",
            "tenure": "Customer Tenure",
            "tenure_in_months": "Customer Tenure",
            "contract_type": "Contract Agreement",
            "contract": "Contract Agreement",
            "internet_service": "Internet Technology",
            "payment_method": "Payment Setup",
            "satisfaction_score": "Customer Satisfaction Score",
        },
    },
    "consumer": {
        "id": "consumer",
        "name": "Consumer & Digital Services",
        "badge": "Consumer / Digital",
        "description": "Streaming entertainment, e-commerce subscriptions, and consumer memberships.",
        "terminology": {
            "customer": "Member / Consumer",
            "customers": "Members",
            "monthly_charges": "Monthly Spend / Fee",
            "tenure": "Membership Duration",
            "contract_type": "Membership Plan",
            "action_title": "Re-engagement & Loyalty Campaign",
            "currency_symbol": "$",
        },
        "field_aliases": {
            "monthly_charges": [
                "monthly_spend",
                "subscription_fee",
                "avg_order_value",
                "membership_fee",
                "monthly_charges",
                "monthly_charge",
            ],
            "tenure": [
                "membership_months",
                "active_months",
                "membership_duration",
                "tenure_in_months",
                "tenure",
            ],
            "contract_type": [
                "membership_type",
                "plan_tier",
                "pass_type",
                "contract_type",
                "contract",
            ],
            "age": [
                "user_age",
                "member_age",
                "age",
            ],
        },
        "driver_labels": {
            "monthly_charges": "Monthly Subscription Fee / Spend",
            "monthly_charge": "Monthly Subscription Fee / Spend",
            "tenure": "Membership Duration",
            "tenure_in_months": "Membership Duration",
            "contract_type": "Membership Commitment",
            "contract": "Membership Commitment",
            "internet_service": "Service Tier & Streaming Add-ons",
            "payment_method": "Payment Method",
            "satisfaction_score": "Rating & Engagement Score",
        },
    },
}

DEFAULT_SECTOR = "telecom"


def get_sector_profile(sector_id: str | None = None) -> dict[str, Any]:
    """Retrieve sector profile with safe fallback."""
    key = str(sector_id or DEFAULT_SECTOR).strip().lower()
    if "saas" in key:
        return SECTOR_PROFILES["saas"]
    if "consumer" in key or "digital" in key or "ecom" in key or "stream" in key:
        return SECTOR_PROFILES["consumer"]
    return SECTOR_PROFILES["telecom"]
