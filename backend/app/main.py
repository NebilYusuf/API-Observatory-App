from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import time
from datetime import datetime
from urllib.parse import urlparse

app = FastAPI(title="API Observatory Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)

@app.get("/")
def read_root():
    return {"message": "API Observatory backend is running"}

@app.post("/check")
async def check_url(payload: URLRequest):
    url = normalize_url(payload.url)

    if not is_valid_url(url):
        return {
            "url": url,
            "status": "Invalid",
            "status_code": None,
            "response_time_ms": None,
            "checked_at": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "message": "Please enter a valid URL."
        }

    start_time = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(url)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "url": url,
            "status": "Up" if response.status_code < 400 else "Warning",
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
            "checked_at": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "message": "Healthy response" if response.status_code < 400 else "Endpoint responded with an error status."
        }

    except httpx.TimeoutException:
        return {
            "url": url,
            "status": "Down",
            "status_code": None,
            "response_time_ms": None,
            "checked_at": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "message": "Request timed out."
        }

    except httpx.RequestError:
        return {
            "url": url,
            "status": "Down",
            "status_code": None,
            "response_time_ms": None,
            "checked_at": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "message": "Could not connect to the URL."
        }
