# Feature Engineering Summary

- Rows: 7043
- Original columns: 49
- Engineered columns: 56

## Added Features
- tenure_group
- revenue_per_month
- avg_monthly_value
- service_count
- satisfaction_tenure_interaction
- satisfaction_monthly_charge_interaction
- revenue_tenure_interaction

## Engineering Notes
- tenure_group bins tenure_in_months into ordered customer lifecycle stages.
- revenue_per_month and avg_monthly_value capture revenue efficiency over customer tenure.
- service_count aggregates active service flags into a single usage signal.
- interaction features combine satisfaction and revenue signals with tenure.