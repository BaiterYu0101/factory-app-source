import json
import time
from fastapi import FastAPI, Response, HTTPException
import requests  # Ensure 'requests' is installed in your local environment

app = FastAPI(title="Market Data Ingest API")

# For monitoring puprpose -- later usage
def log_structured(level: str, message: str, extra: dict = None):
    payload = {
        "timestamp": round(time.time(), 3),
        "level": level,
        "message": message,
        "component": "market-data-service"
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload), flush=True)

# Main Request Point - Querying Live Yahoo Finance Data
@app.get("/api/stock/{ticker}")
def get_market_stream(ticker: str):
    log_structured("INFO", f"Ingesting real-time financial market stream for {ticker.upper()}")
    
    # Unofficial Yahoo Finance chart endpoint
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
    
    # A User-Agent header is required so Yahoo Finance does not block the request
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
            raise HTTPException(status_code=404, detail=f"Ticker symbol '{ticker}' not found.")

        result = results[0]
        meta = result.get("meta")
        if not isinstance(meta, dict):
            raise HTTPException(status_code=502, detail=f"Malformed Yahoo Finance metadata for '{ticker}'.")

        current_price = meta.get("regularMarketPrice")
        currency = meta.get("currency")
        previous_close = meta.get("previousClose")

        return {
            "pipeline_status": "synced",
            "environment": "sandbox-cluster",
            "market_data": {
                "symbol": ticker.upper(),
                "last_price": current_price,
                "currency": currency,
                "previous_close": previous_close,
                "pipeline_latency_ms": latency
            }
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"External API connection failed: {str(e)}")

# Health Check Point
@app.get("/healthz")
def health_check():
    return Response(content="OK", media_type="text/plain", status_code=200)