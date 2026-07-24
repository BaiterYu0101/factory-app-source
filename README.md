# Factory App Source

This project contains two services for a market data demo:

- `market-data-services/` - a FastAPI backend that serves stock data, watchlists, and pattern alerts.
- `admin-ui/` - a Flask admin UI that signs in a user and manages their watchlist and alerts.

## What this project does

- `market-data-services` provides API endpoints for stock lookup, watchlist storage, pattern alerts, and health checks.
- `admin-ui` provides a login page and a user-specific dashboard for watching stocks and creating alerts.

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

Make sure Python 3 is installed.

## Services

This repository contains two services:

- `market-data-services/` — FastAPI backend and PostgreSQL persistence.
- `admin-ui/` — Flask frontend with login and user-specific watchlist/alerts.

## Backend setup (market-data-services)

The frontend now supports password-based signup and login. User accounts are stored in the backend PostgreSQL database.


1. Change into the backend folder:

```bash
cd market-data-services
```

2. Create and activate the Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install backend dependencies:

```bash
pip install -r requirement.txt
```

4. Prepare PostgreSQL:

- Create a database user if needed, or use your local OS user.
- Create the database named `factorydb`.

Example:

```bash
psql -h localhost -U jerry -c 'CREATE DATABASE factorydb;'
```

5. Set environment variables if you need custom creds:

```bash
export DB_USER=jerry
export DB_NAME=factorydb
export DATABASE_URL=postgresql+psycopg://jerry@localhost:5432/factorydb
```

6. Start the backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## Frontend setup (admin-ui)

1. Change into the frontend folder:

```bash
cd ../admin-ui
```

2. Install frontend dependencies:

```bash
pip install -r requirements.txt
```

3. Start the Flask admin UI:

```bash
python app.py
```

4. Open the UI in your browser:

- http://127.0.0.1:8080/

## Login and user-specific behavior

- The admin UI requires a user ID on sign in.
- Each user ID gets its own watchlist and alerts.
- After sign in, all watchlist and alert requests are routed through Flask session state.
- No manual `user_id` is required on the watchlist or alert pages.

## Testing the flow

1. Start the backend service on port `8001`.
2. Start the admin UI on port `8080`.
3. Open the browser at `http://127.0.0.1:8080/`.
4. Sign in with a user ID such as `alice` or `bob`.
5. Add symbols to the watchlist and create pattern alerts.
6. Open the live watchlist page to see user-specific data refresh every 6 seconds.

## Notes

- `market-data-services` uses PostgreSQL via SQLAlchemy.
- `admin-ui` uses Flask sessions and forwards the signed-in user ID automatically.
- If the backend service is not running, the frontend will show API connection errors.

## Notes about the current setup

- The app uses FastAPI for the API layer.
- The app uses Uvicorn as the ASGI server.
- Logs are printed as JSON for easier monitoring.
- The virtual environment is stored in [.venv](.venv).
- Random data is passed into it just for display and testing purpose


