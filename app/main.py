import logging
import json
import time
import random
from fastapi import FastAPI, Response

app = FastAPI(title="Sentinel-X Telemetry Ingest API")

logger = logging.getLogger("sentinel-x-logger")
logger.setLevel(logging.INFO)

def log_structured(level, message, extra=None):
    payload = {
        "timestamp": round(time.time(), 3),
        "level": level,
        "message": message,
        "component": "sentinel-x-telemetry-api"
    }
    if extra:
        payload.update(extra)
    print(json.dumps(payload), flush=True)

@app.get("/")
def get_market_telemetry():
    log_structured("INFO", "Ingesting real-time financial market stream")
    
    # Simulating high-frequency stock volatility updates
    return {
        "pipeline_status": "synced",
        "environment": "sandbox-cluster",
        "telemetry": {
            "symbol": "SCHG",
            "last_price": round(random.uniform(110.0, 115.0), 2),
            "volume_ingested_cps": random.randint(15000, 25000),
            "pipeline_latency_ms": round(random.uniform(0.8, 2.4), 2)
        }
    }

@app.get("/healthz")
def health_check():
    # Kubernetes probes this endpoint. A 200 OK guarantees that the 
    # container runtime is healthy and won't trigger an accidental crash-loop restart.
    return Response(content="OK", media_type="text/plain", status_code=200)