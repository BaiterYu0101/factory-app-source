from fastapi import FastAPI, HTTPException, Query, Response
import json
import time
import hashlib
import hmac
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import requests
from pydantic import BaseModel, Field

import os
import pathlib
import threading

# Simple file-based JSON persistence to replace PostgreSQL/SQLAlchemy
ROOT = pathlib.Path(__file__).parent.resolve()
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

_lock = threading.Lock()

def _read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default

def _write_json(path, obj):
    with _lock:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(obj, fh, indent=2)

USERS_FILE = DATA_DIR / 'users.json'
WATCHLIST_FILE = DATA_DIR / 'watchlist.json'
ALERTS_FILE = DATA_DIR / 'alerts.json'

# Ensure files exist
_write_json(USERS_FILE, _read_json(USERS_FILE, {}))
_write_json(WATCHLIST_FILE, _read_json(WATCHLIST_FILE, {}))
_write_json(ALERTS_FILE, _read_json(ALERTS_FILE, []))


app = FastAPI(
    title="Financial Middleware API",
    description=(
        "A middleware layer that connects your frontend to Yahoo Finance market data. "
        "Supports real-time stock pricing, OHLCV history, watchlists, and "
        "pattern-based trading alerts."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

def log_structured(level: str, message: str, extra: dict = None):
    payload = {
        "timestamp": round(time.time(), 3),
        "level": level,
        "message": message,
        "component": "market-data-service",
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload), flush=True)


def fetch_stock_data(symbol: str) -> dict:
    log_structured("INFO", f"Fetching real-time stock data for {symbol.upper()}")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=5)
        latency = round((time.time() - start_time) * 1000, 2)
        response.raise_for_status()

        data = response.json()
        chart = data.get("chart", {})

        if chart.get("error"):
            raise HTTPException(status_code=503, detail=f"Yahoo Finance error: {chart['error']}")

        results = chart.get("result")
        if not results:
            raise HTTPException(status_code=404, detail=f"Ticker symbol '{symbol}' not found.")

        result = results[0]
        meta = result.get("meta")
        if not isinstance(meta, dict):
            raise HTTPException(status_code=502, detail=f"Malformed Yahoo Finance metadata for '{symbol}'.")

        current_price = meta.get("regularMarketPrice")
        currency = meta.get("currency")
        previous_close = meta.get("previousClose")

        return {
            "pipeline_status": "synced",
            "environment": "sandbox-cluster",
            "market_data": {
                "symbol": symbol.upper(),
                "last_price": current_price,
                "currency": currency,
                "previous_close": previous_close,
                "pipeline_latency_ms": latency,
            },
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"External API connection failed: {str(e)}")


class WatchlistItem(BaseModel):
    user_id: str = Field(..., example="user-123")
    symbol: str = Field(..., example="AAPL")


class PatternAlertCreate(BaseModel):
    user_id: str = Field(..., example="user-123")
    symbol: str = Field(..., example="AAPL")
    pattern: str = Field(..., example="bullish-engulfing")
    threshold: Optional[float] = Field(None, example=150.0)


class PatternAlert(BaseModel):
    alert_id: str
    user_id: str
    symbol: str
    pattern: str
    threshold: Optional[float]
    status: str


class UserSignup(BaseModel):
    user_id: str = Field(..., example="user-123")
    password: str = Field(..., example="changeme")


class UserLogin(BaseModel):
    user_id: str = Field(..., example="user-123")
    password: str = Field(..., example="changeme")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def get_watchlist_symbols(user_id: str) -> List[str]:
    data = _read_json(WATCHLIST_FILE, {})
    return data.get(user_id, [])


def add_watchlist_symbol(user_id: str, symbol: str) -> List[str]:
    normalized = symbol.upper()
    data = _read_json(WATCHLIST_FILE, {})
    user_list = data.get(user_id, [])
    if normalized in user_list:
        raise HTTPException(status_code=409, detail=f"{normalized} is already in watchlist for {user_id}.")
    user_list.append(normalized)
    data[user_id] = user_list
    _write_json(WATCHLIST_FILE, data)
    return user_list


def remove_watchlist_symbol(user_id: str, symbol: str) -> List[str]:
    normalized = symbol.upper()
    data = _read_json(WATCHLIST_FILE, {})
    user_list = data.get(user_id, [])
    if normalized not in user_list:
        raise HTTPException(status_code=404, detail=f"{normalized} not found in watchlist for {user_id}.")
    user_list = [s for s in user_list if s != normalized]
    data[user_id] = user_list
    _write_json(WATCHLIST_FILE, data)
    return user_list


def create_pattern_alert_db(alert: PatternAlertCreate) -> dict:
    alert_id = str(uuid4())
    alerts = _read_json(ALERTS_FILE, [])
    record = {
        "alert_id": alert_id,
        "user_id": alert.user_id,
        "symbol": alert.symbol.upper(),
        "pattern": alert.pattern,
        "threshold": alert.threshold,
        "status": "active",
    }
    alerts.append(record)
    _write_json(ALERTS_FILE, alerts)
    return record


def delete_pattern_alert_db(alert_id: str) -> dict:
    alerts = _read_json(ALERTS_FILE, [])
    existing = next((a for a in alerts if a.get('alert_id') == alert_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    alerts = [a for a in alerts if a.get('alert_id') != alert_id]
    _write_json(ALERTS_FILE, alerts)
    return {"alert_id": alert_id, "message": "Pattern alert canceled.", "user_id": existing.get('user_id')}


def get_pattern_alerts_for_user(user_id: str) -> List[dict]:
    alerts = _read_json(ALERTS_FILE, [])
    return [a for a in alerts if a.get('user_id') == user_id]


@app.post("/api/v1/users/signup")
def signup_user(signup: UserSignup):
    users = _read_json(USERS_FILE, {})
    if signup.user_id in users:
        raise HTTPException(status_code=409, detail=f"User {signup.user_id} already exists.")
    users[signup.user_id] = hash_password(signup.password)
    _write_json(USERS_FILE, users)
    return {"user_id": signup.user_id}


@app.post("/api/v1/users/login")
def login_user(credentials: UserLogin):
    users = _read_json(USERS_FILE, {})
    stored = users.get(credentials.user_id)
    if not stored or not verify_password(credentials.password, stored):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": credentials.user_id}


@app.get("/api/v1/stock/{symbol}")
def get_stock(symbol: str):
    return fetch_stock_data(symbol)


@app.get("/api/stock/{ticker}")
def get_market_stream(ticker: str):
    return fetch_stock_data(ticker)


@app.post("/api/v1/watchlist")
def add_to_watchlist(item: WatchlistItem):
    user_id = item.user_id
    symbol = item.symbol.upper()
    watchlist = add_watchlist_symbol(user_id, symbol)
    log_structured("INFO", "Watchlist item added", {"user_id": user_id, "symbol": symbol})
    return {"user_id": user_id, "watchlist": watchlist, "message": f"{symbol} added to watchlist."}


@app.get("/api/v1/watchlist/{user_id}")
def get_watchlist(user_id: str):
    return {"user_id": user_id, "watchlist": get_watchlist_symbols(user_id)}


@app.delete("/api/v1/watchlist/{symbol}")
def remove_from_watchlist(symbol: str, user_id: str = Query(..., description="User ID owning the watchlist")):
    watchlist = remove_watchlist_symbol(user_id, symbol)
    log_structured("INFO", "Watchlist item removed", {"user_id": user_id, "symbol": symbol.upper()})
    return {"user_id": user_id, "watchlist": watchlist, "message": f"{symbol.upper()} removed from watchlist."}


@app.post("/api/v1/pattern-alerts")
def create_pattern_alert(alert: PatternAlertCreate):
    created = create_pattern_alert_db(alert)
    log_structured("INFO", "Pattern alert created", {"alert_id": created["alert_id"], "user_id": created["user_id"]})
    return PatternAlert(**created)


@app.delete("/api/v1/pattern-alerts/{alert_id}")
def delete_pattern_alert(alert_id: str):
    deleted = delete_pattern_alert_db(alert_id)
    log_structured("INFO", "Pattern alert deleted", {"alert_id": alert_id, "user_id": deleted.get("user_id")})
    return {"alert_id": alert_id, "message": "Pattern alert canceled."}


@app.get("/api/v1/pattern-alerts/{user_id}")
def list_pattern_alerts(user_id: str):
    return {"user_id": user_id, "alerts": get_pattern_alerts_for_user(user_id)}


@app.get("/healthz")
def health_check():
    return Response(content="OK", media_type="text/plain", status_code=200)
