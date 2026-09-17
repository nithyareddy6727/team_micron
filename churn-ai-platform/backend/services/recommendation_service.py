from __future__ import annotations

import logging
from typing import Any

from config.sectors import get_sector_profile

logger = logging.getLogger("churn_app")


class RecommendationService:
    """
    Domain-aware, evidence-driven retention recommendation engine.
    Generates actionable retention plays based on sector, risk tier, probability,
    and local SHAP feature drivers.
    """

    @staticmethod
    def identify_primary_driver(
        top_features: list[dict[str, Any]],
        customer_features: dict[str, Any],
        sector_id: str = "telecom",
    ) -> str:
        """Derive the human-readable primary churn driver from SHAP/model features."""
        profile = get_sector_profile(sector_id)
        driver_labels = profile.get("driver_labels", {})

        if top_features:
            lead = top_features[0]
            feature_key = str(lead.get("feature") or lead.get("name") or "").lower()
            impact_score = lead.get("impact") or lead.get("shap_value") or lead.get("importance") or 0.0

            if "month" in feature_key or "charge" in feature_key or "mrr" in feature_key or "spend" in feature_key:
                val = customer_features.get("monthly_charges") or customer_features.get("mrr") or customer_features.get("monthly_spend")
                if val and float(val) > 65:
                    return f"High {driver_labels.get('monthly_charges', 'Monthly Cost')}"
                return driver_labels.get("monthly_charges", "Billing & Cost Sensitivity")

            if "tenure" in feature_key or "age" in feature_key:
                val = customer_features.get("tenure") or customer_features.get("tenure_in_months") or customer_features.get("account_age_months")
                if val is not None and float(val) <= 12:
                    return f"Early Lifecycle Risk ({driver_labels.get('tenure', 'Tenure')} ≤ 12m)"
                return f"{driver_labels.get('tenure', 'Tenure / Lifecycle')}"

            if "contract" in feature_key:
                val = str(customer_features.get("contract_type") or customer_features.get("contract") or "").lower()
                if "month" in val or "flexible" in val or "no" in val:
                    return f"Flexible / Month-to-month {driver_labels.get('contract_type', 'Contract')}"
                return driver_labels.get("contract_type", "Contract Commitment")

            if "internet" in feature_key or "service" in feature_key:
                return driver_labels.get("internet_service", "Service Configuration")

            mapped = driver_labels.get(feature_key)
            if mapped:
                return mapped
            return feature_key.replace("_", " ").title()

        # Fallback inspection of raw customer features
        tenure = customer_features.get("tenure") or customer_features.get("tenure_in_months")
        if tenure is not None and float(tenure) <= 6:
            return "Early Account Lifecycle (New Customer)"

        charges = customer_features.get("monthly_charges") or customer_features.get("monthly_charge")
        if charges is not None and float(charges) > 75:
            return "Elevated Monthly Charges"

        contract = str(customer_features.get("contract_type") or customer_features.get("contract") or "").lower()
        if "month" in contract:
            return "Uncommitted Monthly Plan"

        return "Multivariate Engagement Decline"

    @classmethod
    def generate_recommendations(
        cls,
        sector_id: str,
        probability: float,
        risk_level: str,
        top_features: list[dict[str, Any]],
        customer_features: dict[str, Any],
    ) -> tuple[str, list[str]]:
        """
        Produce a tailored (primary_driver, list_of_recommendations) tuple.
        """
        profile = get_sector_profile(sector_id)
        sec = profile["id"]
        primary_driver = cls.identify_primary_driver(top_features, customer_features, sector_id=sec)

        normalized_risk = str(risk_level).lower()
        recs: list[str] = []

        # Analyze driver tags
        is_price_driver = any(k in primary_driver.lower() for k in ["cost", "charge", "mrr", "bill", "spend"])
        is_tenure_driver = any(k in primary_driver.lower() for k in ["tenure", "lifecycle", "early", "new"])
        is_contract_driver = any(k in primary_driver.lower() for k in ["contract", "commitment", "flexible", "month-to-month"])

        if "high" in normalized_risk:
            if sec == "saas":
                if is_price_driver:
                    recs.append("Offer an annual prepayment discount (15-20%) or bundle premium user seats.")
                    recs.append("Review licensing utilization to eliminate inactive seats and lower perceived cost.")
                elif is_tenure_driver:
                    recs.append("Schedule an urgent Executive Onboarding session with a Senior Solution Architect.")
                    recs.append("Trigger an in-app interactive walkthrough targeting high-retention feature workflows.")
                elif is_contract_driver:
                    recs.append("Propose an annual enterprise contract tier with guaranteed SLA and dedicated CSM.")
                    recs.append("Provide a complimentary 60-day trial of the Advanced Analytics add-on module.")
                else:
                    recs.append("Schedule an urgent Customer Success intervention and workflow health review.")
                    recs.append("Audit open support tickets to resolve lingering integration bottlenecks.")
                recs.append("Flag account in Customer Success CRM for immediate priority follow-up within 24 hours.")

            elif sec == "consumer":
                if is_price_driver:
                    recs.append("Issue a targeted 25% discount reward valid across the next 2 billing cycles.")
                    recs.append("Present a flexible pause-membership option to prevent outright cancellation.")
                elif is_tenure_driver:
                    recs.append("Dispatch a personalized onboarding guide featuring trending content and staff picks.")
                    recs.append("Unlock a 30-day VIP trial perk to accelerate user engagement and habit formation.")
                elif is_contract_driver:
                    recs.append("Offer a discounted annual pass providing 3 complimentary months.")
                    recs.append("Bundle premium ad-free / multi-device streaming privileges at no additional charge.")
                else:
                    recs.append("Trigger an automated personalized re-engagement campaign via push and email.")
                    recs.append("Deliver tailored recommendations based on past viewing/purchase history.")
                recs.append("Monitor account activity and dispatch proactive satisfaction survey.")

            else:  # Telecom default
                if is_price_driver:
                    recs.append("Offer an immediate 15% loyalty bill reduction or transition to a capped value plan.")
                    recs.append("Waive equipment rental fees and review monthly call/data add-on charges.")
                elif is_tenure_driver:
                    recs.append("Enroll subscriber in the Welcome Loyalty Care program with bonus high-speed data.")
                    recs.append("Assign a dedicated customer care representative for all future inquiries.")
                elif is_contract_driver:
                    recs.append("Offer a 12-month rate-freeze contract renewal with a complimentary streaming package.")
                    recs.append("Provide a bill discount incentive in exchange for switching to auto-debit billing.")
                else:
                    recs.append("Perform automated line diagnostics to ensure broadband/mobile speed stability.")
                    recs.append("Provide a free router equipment upgrade or Wi-Fi booster package.")
                recs.append("Dispatch customer service check-in before the next billing cycle cutoff.")

        elif "medium" in normalized_risk:
            if sec == "saas":
                recs.append("Schedule a quarterly business review (QBR) to align on product roadmap value.")
                recs.append("Deliver curated best-practice templates tailored to the customer's industry.")
                recs.append("Verify primary contact satisfaction via a pulse NPS survey.")
            elif sec == "consumer":
                recs.append("Share a weekly discovery digest showcasing newly added catalog favorites.")
                recs.append("Offer loyalty reward points for completing profile preferences.")
                recs.append("Suggest tailored playlist/product bundles based on recent activity.")
            else:
                recs.append("Send a proactive plan optimization notification to ensure fair billing rates.")
                recs.append("Offer optional security and speed booster add-ons at a discounted bundle rate.")
                recs.append("Verify network performance and resolve pending customer service inquiries.")

        else:  # Low risk
            if sec == "saas":
                recs.append("Invite customer to join the Customer Advisory Board and early beta program.")
                recs.append("Explore potential case study collaboration or advocacy testimonial.")
            elif sec == "consumer":
                recs.append("Reward customer with loyalty member tier upgrade and exclusive preview access.")
                recs.append("Send customer appreciation note with a referral bonus link.")
            else:
                recs.append("Thank subscriber for continuous loyalty with complimentary bonus perks.")
                recs.append("Offer family/multi-line promotional expansion rates.")

        return primary_driver, recs


recommendation_service = RecommendationService()
