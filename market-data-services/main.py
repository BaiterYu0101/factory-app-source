import json
import time
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import requests
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

import os
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

local_user = os.getenv("DB_USER", os.getenv("USER", "postgres"))
local_db = os.getenv("DB_NAME", "factorydb")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg://{local_user}@localhost:5432/{local_db}",
)
if DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+psycopg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)


class WatchlistDB(Base):
    __tablename__ = "watchlist_items"

    user_id = Column(String, primary_key=True, index=True)
    symbol = Column(String, primary_key=True, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PatternAlertDB(Base):
    __tablename__ = "pattern_alerts"

    alert_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    pattern = Column(String, nullable=False)
    threshold = Column(Float, nullable=True)
    status = Column(String, default="active", nullable=False)


init_db()


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


def get_watchlist_symbols(db, user_id: str) -> List[str]:
    query = db.query(WatchlistDB).filter(WatchlistDB.user_id == user_id).order_by(WatchlistDB.added_at)
    return [row.symbol for row in query.all()]


def add_watchlist_symbol(db, user_id: str, symbol: str) -> List[str]:
    normalized = symbol.upper()
    exists = db.query(WatchlistDB).filter(WatchlistDB.user_id == user_id, WatchlistDB.symbol == normalized).first()
    if exists:
        raise HTTPException(status_code=409, detail=f"{normalized} is already in watchlist for {user_id}.")

    item = WatchlistDB(user_id=user_id, symbol=normalized)
    db.add(item)
    db.commit()
    return get_watchlist_symbols(db, user_id)


def remove_watchlist_symbol(db, user_id: str, symbol: str) -> List[str]:
    normalized = symbol.upper()
    existing = db.query(WatchlistDB).filter(WatchlistDB.user_id == user_id, WatchlistDB.symbol == normalized).first()
    if not existing:
        raise HTTPException(status_code=404, detail=f"{normalized} not found in watchlist for {user_id}.")

    db.delete(existing)
    db.commit()
    return get_watchlist_symbols(db, user_id)


def create_pattern_alert_db(db, alert: PatternAlertCreate) -> dict:
    alert_id = str(uuid4())
    record = PatternAlertDB(
        alert_id=alert_id,
        user_id=alert.user_id,
        symbol=alert.symbol.upper(),
        pattern=alert.pattern,
        threshold=alert.threshold,
        status="active",
    )
    db.add(record)
    db.commit()
    return {
        "alert_id": alert_id,
        "user_id": alert.user_id,
        "symbol": alert.symbol.upper(),
        "pattern": alert.pattern,
        "threshold": alert.threshold,
        "status": "active",
    }


def delete_pattern_alert_db(db, alert_id: str) -> dict:
    existing = db.query(PatternAlertDB).filter(PatternAlertDB.alert_id == alert_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")

    user_id = existing.user_id
    db.delete(existing)
    db.commit()
    return {"alert_id": alert_id, "message": "Pattern alert canceled.", "user_id": user_id}


def get_pattern_alerts_for_user(db, user_id: str) -> List[dict]:
    results = db.query(PatternAlertDB).filter(PatternAlertDB.user_id == user_id).all()
    return [
        {
            "alert_id": row.alert_id,
            "user_id": row.user_id,
            "symbol": row.symbol,
            "pattern": row.pattern,
            "threshold": row.threshold,
            "status": row.status,
        }
        for row in results
    ]


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
    db = SessionLocal()
    try:
        watchlist = add_watchlist_symbol(db, user_id, symbol)
        log_structured("INFO", "Watchlist item added", {"user_id": user_id, "symbol": symbol})
        return {
            "user_id": user_id,
            "watchlist": watchlist,
            "message": f"{symbol} added to watchlist.",
        }
    finally:
        db.close()


@app.get("/api/v1/watchlist/{user_id}")
def get_watchlist(user_id: str):
    db = SessionLocal()
    try:
        return {
            "user_id": user_id,
            "watchlist": get_watchlist_symbols(db, user_id),
        }
    finally:
        db.close()


@app.delete("/api/v1/watchlist/{symbol}")
def remove_from_watchlist(symbol: str, user_id: str = Query(..., description="User ID owning the watchlist")):
    db = SessionLocal()
    try:
        watchlist = remove_watchlist_symbol(db, user_id, symbol)
        log_structured("INFO", "Watchlist item removed", {"user_id": user_id, "symbol": symbol.upper()})
        return {
            "user_id": user_id,
            "watchlist": watchlist,
            "message": f"{symbol.upper()} removed from watchlist.",
        }
    finally:
        db.close()


@app.post("/api/v1/pattern-alerts")
def create_pattern_alert(alert: PatternAlertCreate):
    db = SessionLocal()
    try:
        created = create_pattern_alert_db(db, alert)
        log_structured("INFO", "Pattern alert created", {"alert_id": created["alert_id"], "user_id": created["user_id"]})
        return PatternAlert(**created)
    finally:
        db.close()


@app.delete("/api/v1/pattern-alerts/{alert_id}")
def delete_pattern_alert(alert_id: str):
    db = SessionLocal()
    try:
        deleted = delete_pattern_alert_db(db, alert_id)
        log_structured("INFO", "Pattern alert deleted", {"alert_id": alert_id, "user_id": deleted.get("user_id")})
        return {
            "alert_id": alert_id,
            "message": "Pattern alert canceled.",
        }
    finally:
        db.close()


@app.get("/api/v1/pattern-alerts/{user_id}")
def list_pattern_alerts(user_id: str):
    db = SessionLocal()
    try:
        return {
            "user_id": user_id,
            "alerts": get_pattern_alerts_for_user(db, user_id),
        }
    finally:
        db.close()


@app.get("/healthz")
def health_check():
    return Response(content="OK", media_type="text/plain", status_code=200)
