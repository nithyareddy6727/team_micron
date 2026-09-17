import sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("\n" + "="*60)
print("VERIFYING DASHBOARD ENDPOINT:")
dash = client.get("/dashboard").json()
print("Success:", dash["success"])
print("Total Customers:", dash["data"]["total_customers"])
print("High-Risk Count:", dash["data"]["high_risk_count"])
print("Top 3 High-Risk Queue:")
for c in dash["data"]["high_risk_customers"][:3]:
    print(f"  - Customer {c['customer_id']}: {c['probability']*100:.1f}% risk | Driver: {c['primary_driver']} | Action: {c['recommended_action']}")

print("\n" + "="*60)
print("VERIFYING SECTOR PREDICTIONS (SaaS / Telecom / Consumer):")
test_cases = [
    ("saas", {"customer_id": "CUST-SAAS-101", "sector": "saas", "features": {"mrr": 185.0, "account_age_months": 2, "plan_tier": "Monthly"}, "explain": True}),
    ("telecom", {"customer_id": "CUST-TELCO-202", "sector": "telecom", "features": {"monthly_charges": 98.5, "tenure": 3, "contract": "Month-to-month"}, "explain": True}),
    ("consumer", {"customer_id": "CUST-CONS-303", "sector": "consumer", "features": {"monthly_spend": 82.0, "membership_months": 1, "billing_plan": "Flexible"}, "explain": True}),
]

for sec, payload in test_cases:
    res = client.post("/predict", json=payload).json()
    assert res["success"] is True, f"Failed for {sec}: {res}"
    d = res["data"]
    print(f"\n--- SECTOR: {sec.upper()} ---")
    print(f"Prediction: {d['prediction_label']} | Probability: {d['probability']*100:.1f}% | Risk: {d['risk_level']}")
    print(f"Primary Churn Driver: {d['primary_driver']}")
    print(f"Top 2 Retention Plays:")
    for play in d["recommendations"][:2]:
        print(f"   * {play}")

print("\n" + "="*60)
print("ALL DEMO CAPABILITIES VERIFIED SUCCESSFULLY!")
print("="*60 + "\n")
