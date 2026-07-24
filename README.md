# Factory App Source

This repository contains two services for a market data demo:

- `market-data-services/` — FastAPI backend with PostgreSQL persistence.
- `admin-ui/` — Flask frontend with login, watchlists, and alerts.

## Overview

- `market-data-services` serves stock lookup, watchlist storage, pattern alerts, and health checks.
- `admin-ui` provides the login/signup UI and user-specific dashboard.
- User accounts are stored in the backend PostgreSQL database.

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
- PostgreSQL

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

4. Create the database:

```bash
psql -h localhost -U <db_user> -c 'CREATE DATABASE factorydb;'
```

5. Optionally set custom DB environment variables:

```bash
export DB_USER=<db_user>
export DB_NAME=factorydb
export DATABASE_URL=postgresql+psycopg://<db_user>@localhost:5432/factorydb
```

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
- The backend stores users, watchlists, and alerts in PostgreSQL.

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

- The backend uses SQLAlchemy for DB persistence.
- The frontend uses Flask sessions and delegates auth to the backend.
- Start the backend before using the frontend, otherwise API requests will fail.

