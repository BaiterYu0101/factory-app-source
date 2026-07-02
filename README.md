# Factory App Source

This project is a small FastAPI application that simulates a telemetry ingest API for a financial data pipeline.

## What this app does

The app exposes two endpoints:

- `GET /` returns simulated market telemetry data such as stock symbol, price, volume, and pipeline latency.
- `GET /healthz` returns a simple `200 OK` response for health checks.

It also prints structured JSON logs for monitoring and debugging.

## Project structure

```text
factory-app-source/
├── app/
│   └── main.py
├── .venv/
├── requirement.txt
└── README.md
```

## Prerequisites

Make sure Python 3 is installed.

## Setup

Before installing dependencies or running the app, activate the virtual environment from the project root.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run this once:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then install dependencies:

```bash
pip install -r requirement.txt
```

> Important: make sure the virtual environment is activated before running the app or installing packages.

## Run the app

Start the server with:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/healthz

## Notes about the current setup

- The app uses FastAPI for the API layer.
- The app uses Uvicorn as the ASGI server.
- Logs are printed as JSON for easier monitoring.
- The virtual environment is stored in [.venv](.venv).
- Random data is passed into it just for display and testing purpose


