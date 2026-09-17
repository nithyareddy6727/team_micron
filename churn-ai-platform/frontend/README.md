# ChurnX AI Frontend (Production Architecture)

Apple-inspired, production-grade React frontend for churn prediction and ML observability.

## Stack

- React 19 + Vite
- Tailwind CSS
- Framer Motion
- Recharts
- Zustand
- Axios
- Power BI Embedded (powerbi-client-react)

## Folder Structure

```text
src/
	assets/
	components/
		charts/
		powerbi/
		ui/
	hooks/
	layouts/
	pages/
	services/
	styles/
	utils/
```

## Main Pages

- Dashboard: KPI cards, risk distribution, trend chart, recent predictions
- Prediction: JSON input form, live /predict call, probability and label output
- Analytics: trends, risk segmentation, top feature drivers, filters
- Settings: API base URL configuration and Power BI embed integration

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `VITE_API_BASE_URL` (default: `http://127.0.0.1:8000`)
- `VITE_API_KEY` (optional)
- `VITE_POWERBI_CLIENT_ID`
- `VITE_POWERBI_TENANT_ID`
- `VITE_POWERBI_REPORT_ID`

Legacy compatibility is supported for:

- `REACT_APP_POWERBI_CLIENT_ID`
- `REACT_APP_POWERBI_TENANT_ID`
- `REACT_APP_POWERBI_REPORT_ID`

Power BI tokens should be brokered by backend `/powerbi/embed-config`.

## Run Locally

From `churn-ai-platform/frontend`:

```bash
npm install
npm run start
```

Backend must be running on port `8000` for full API functionality.

## Production Build

```bash
npm run build
npm run preview
```

## Notes

- If port 3000 is busy, Vite auto-selects another port.
- Update API base URL at runtime from the Settings page.
- Theme toggle supports light and dark mode.
