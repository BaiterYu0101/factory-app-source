# Factory App Source

This repository contains two services for a market data demo:

- `market-data-services/` — FastAPI backend with file-based JSON persistence.
- `admin-ui/` — Flask frontend with login, watchlists, and alerts.

## Overview

- `market-data-services` serves stock lookup, watchlist storage, pattern alerts, and health checks.
- `admin-ui` provides the login/signup UI and user-specific dashboard.
- User accounts are stored in a simple file-backed JSON store (no external DB required).

## Project structure

```text
factory-app-source/
├── admin-ui/
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
├── market-data-services/
│   ├── main.py
│   ├── requirement.txt
│   └── .venv/
└── README.md
```

## Prerequisites

- Python 3

## Backend setup (`market-data-services`)

1. Change to the backend folder:

```bash
cd market-data-services
```

2. Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirement.txt
```

4. No database setup is required — the backend persists data to JSON files in `market-data-services/data/`.

6. Start the backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## Frontend setup (`admin-ui`)

1. Change to the frontend folder:

```bash
cd ../admin-ui
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the Flask app:

```bash
python app.py
```

4. Open the UI:

- http://127.0.0.1:8080/

## How the two services connect

- `admin-ui` uses `API_BASE_URL` to call the backend.
- Default backend URL: `http://localhost:8001`.
- The frontend sends authenticated requests with the current `user_id`.
- The backend stores users, watchlists, and alerts in a local JSON data directory by default (`market-data-services/data/`).

## User flow

- Sign up with a new `user_id` and password.
- Log in to create a Flask session.
- Add/watch symbols and create alerts for that user.
- The live watchlist page refreshes user-specific data automatically.

## Docker notes

If you want to publish the frontend image later:

```bash
# Giving a tag to image
docker tag factory-admin-ui:latest <username>/factory-admin-ui:latest

# Push the image to dockerhub
docker push <username>/factory-admin-ui:latest
```

## Notes

- The backend uses a simple file-backed JSON store for persistence (no SQLAlchemy required).
- The frontend uses Flask sessions and delegates auth to the backend.
- Start the backend before using the frontend, otherwise API requests will fail.

