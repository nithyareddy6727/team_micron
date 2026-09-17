from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import socket
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
APP_ROOT = ROOT / "churn-ai-platform"
BACKEND_DIR = APP_ROOT / "backend"
FRONTEND_DIR = APP_ROOT / "frontend"
BACKEND_HEALTH_URL = "http://127.0.0.1:8000/health"
FRONTEND_URL = "http://127.0.0.1:3000"
API_BASE_URL = "http://localhost:8000"


def _is_healthy(url: str) -> bool:
	parsed = urlparse(url)
	if parsed.hostname and parsed.port:
		try:
			with socket.create_connection((parsed.hostname, parsed.port), timeout=2):
				return True
		except OSError:
			pass
	try:
		with urlopen(url, timeout=2) as response:
			return 200 <= getattr(response, "status", 200) < 400
	except (URLError, OSError, TimeoutError):
		return False


def _get_python_executable() -> str:
	venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
	if venv_python.exists():
		return str(venv_python)
	return sys.executable


def _start_backend() -> subprocess.Popen[str] | None:
	if _is_healthy(BACKEND_HEALTH_URL):
		print("Backend already running at http://localhost:8000")
		return None

	env = os.environ.copy()
	command = [
		_get_python_executable(),
		"-m",
		"uvicorn",
		"main:app",
		"--host",
		"0.0.0.0",
		"--port",
		"8000",
	]
	print("Starting backend on http://localhost:8000")
	return subprocess.Popen(command, cwd=BACKEND_DIR, env=env)


def _start_frontend() -> subprocess.Popen[str] | None:
	if _is_healthy(FRONTEND_URL):
		print("Frontend already running at http://localhost:3000")
		return None

	npm_command = shutil.which("npm")
	if not npm_command:
		raise RuntimeError("npm was not found on PATH")

	env = os.environ.copy()
	env["VITE_API_BASE_URL"] = API_BASE_URL
	command = [npm_command, "run", "start"]
	print("Starting frontend on http://localhost:3000")
	return subprocess.Popen(command, cwd=FRONTEND_DIR, env=env, shell=(os.name == "nt"))


def _wait_for_services(timeout_seconds: int = 120) -> None:
	deadline = time.time() + timeout_seconds
	while time.time() < deadline:
		backend_ready = _is_healthy(BACKEND_HEALTH_URL)
		frontend_ready = _is_healthy(FRONTEND_URL)
		if backend_ready and frontend_ready:
			print("System is ready")
			print("Backend: http://localhost:8000")
			print("Frontend: http://localhost:3000")
			return
		time.sleep(2)
	raise TimeoutError("Timed out waiting for backend and frontend to become ready")


def main() -> int:
	backend_process = None
	frontend_process = None

	try:
		backend_process = _start_backend()
		frontend_process = _start_frontend()
		_wait_for_services()
		print("\n==========================================")
		print("   CHURN AI PLATFORM IS RUNNING")
		print("   Frontend: http://localhost:3000")
		print("   Backend:  http://localhost:8000")
		print("   Press Ctrl+C to stop.")
		print("==========================================\n")
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		print("Startup interrupted")
		for process in (backend_process, frontend_process):
			if process is not None and process.poll() is None:
				process.terminate()
		return 130
	except Exception:
		for process in (backend_process, frontend_process):
			if process is not None and process.poll() is None:
				process.terminate()
		raise


if __name__ == "__main__":
	raise SystemExit(main())
