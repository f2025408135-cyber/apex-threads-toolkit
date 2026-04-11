import time
import requests
import json
import datetime
import os
from typing import Dict, Any, Optional
from rich.console import Console

console = Console()
os.makedirs("output", exist_ok=True)
LOG_FILE = "output/latest_run.log"

def _log(msg: str, color_msg: str = None):
    if color_msg:
        console.print(color_msg)
    else:
        console.print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

class RequestUtils:
    @staticmethod
    def make_request(method: str, url: str, headers: dict = None, params: dict = None, body: dict = None, timeout: int = 15) -> requests.Response:
        """Centralized request function with 429 retry and specific error handling/logging."""
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=body, timeout=timeout)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                response = requests.request(method.upper(), url, headers=headers, params=params, json=body, timeout=timeout)
                
            duration_ms = int((time.time() - start_time) * 1000)
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            log_str = f"{timestamp} | {method.upper()} | {url} | {response.status_code} | {duration_ms}ms"
            _log(log_str)
            
            # Rate limit retry logic
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                msg = f"Rate limited (429)! Waiting {retry_after}s before retrying..."
                _log(msg, f"[yellow]{msg}[/yellow]")
                time.sleep(retry_after)
                
                start_time = time.time()
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=params, timeout=timeout)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=body, timeout=timeout)
                elif method.upper() == "DELETE":
                    response = requests.delete(url, headers=headers, timeout=timeout)
                else:
                    response = requests.request(method.upper(), url, headers=headers, params=params, json=body, timeout=timeout)
                    
                duration_ms = int((time.time() - start_time) * 1000)
                timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
                log_str = f"{timestamp} | {method.upper()} | {url} | {response.status_code} | {duration_ms}ms"
                _log(log_str)
                
            return response
            
        except requests.Timeout as e:
            duration_ms = int((time.time() - start_time) * 1000)
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            log_str = f"{timestamp} | {method.upper()} | {url} | 0 | {duration_ms}ms (Timeout: {e})"
            _log(log_str)
            raise e
        except requests.ConnectionError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            log_str = f"{timestamp} | {method.upper()} | {url} | 0 | {duration_ms}ms (ConnectionError: {e})"
            _log(log_str)
            raise e
        except requests.HTTPError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            log_str = f"{timestamp} | {method.upper()} | {url} | 0 | {duration_ms}ms (HTTPError: {e})"
            _log(log_str)
            raise e
        except json.JSONDecodeError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            log_str = f"{timestamp} | {method.upper()} | {url} | 0 | {duration_ms}ms (JSONDecodeError: {e})"
            _log(log_str)
            raise e
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            log_str = f"{timestamp} | {method.upper()} | {url} | 0 | {duration_ms}ms (Exception: {e})"
            _log(log_str)
            raise e

def safe_make_request(method: str, url: str, token: str, params: dict = None, body: dict = None, delay_ms: int = 500) -> Any:
    """Wrapper that catches specific exceptions and returns a structured dictionary so runners don't crash."""
    time.sleep(delay_ms / 1000.0)
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    start_time = time.time()
    try:
        response = RequestUtils.make_request(method, url, headers=headers, params=params, body=body)
        duration_ms = int((time.time() - start_time) * 1000)
        return {"status_code": response.status_code, "text": response.text, "duration_ms": duration_ms, "error": None}
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError, json.JSONDecodeError, Exception) as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return {"status_code": 0, "text": str(e), "duration_ms": duration_ms, "error": str(e)}
