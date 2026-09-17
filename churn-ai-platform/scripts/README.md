# Ops Scripts

- `launch-full-system.ps1` starts the FastAPI recommendation service and the Node.js backend, then waits for health checks.
- `smoke-test-recommendation.ps1` checks both health endpoints, calls the recommendation flow, and verifies MySQL persistence.
- `release.ps1` applies a versioned release to local, staging, or production.
- `rollback.ps1` rolls Kubernetes deployments back to the previous revision.

Run from PowerShell in the repository root.
