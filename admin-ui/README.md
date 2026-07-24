# Admin UI

This is the Flask frontend for the market data demo.

## What it does

- Displays a login page where users enter a simple `user_id`.
- Uses Flask session state to keep the signed-in user.
- Sends all watchlist and alert requests through the current session user.
- Shows a live watchlist page with periodic updates.

## Setup

1. Change into the `admin-ui/` folder:

```bash
cd admin-ui
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

4. Open the UI:

- http://127.0.0.1:8080/

## Important

- The frontend expects the backend API to be running on `http://localhost:8001` by default.
- You can override the backend location with:

```bash
export API_BASE_URL=http://localhost:8001
```

## Login and signup flow

- Open the page and sign in with a registered user ID and password.
- If you do not have an account, click **Create one** to sign up.
- The signup page requires a unique `user_id` and a password.
- After signup, you are signed in and brought to the dashboard.
- Each distinct `user_id` gets its own watchlist and alerts.
- Account credentials are stored in the backend PostgreSQL database.
- After sign in, the UI no longer requires manual `user_id` entry for watchlist or alerts.
