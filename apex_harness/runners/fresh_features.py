import time
from ..config import Config
from ..endpoints import endpoints_registry, Endpoint
from ..classifier import classify_response, TestResult
from typing import Callable
from rich.console import Console
from ..request_utils import safe_make_request
from tqdm import tqdm

console = Console()

def run_fresh_features(config: Config, save_result_callback: Callable, delay_ms: int = 500):
    console.print("\n[bold green]Running Fresh Features Tests (Polls, Geolocation, Search)[/bold green]")
    
    fresh_endpoints = [
        "poll_b_results",
        "poll_b_vote",
        "poll_b_close",
        "thread_b_location",
        "keyword_search"
    ]
    
    with tqdm(total=len(fresh_endpoints), desc="Running: FRESH_FEATURES") as pbar:
        for eid in fresh_endpoints:
            pbar.set_postfix({"endpoint": eid})
            
            endpoint = next((e for e in endpoints_registry if e.id == eid), None)
            if not endpoint:
                pbar.update(1)
                continue
                
            url = endpoint.url_template.replace("{USER_B_THREADS_ID}", config.USER_B_THREADS_ID)
            url = url.replace("{THREAD_B_TEXT_ID}", config.THREAD_B_TEXT_ID)
            url = url.replace("{THREAD_B_POLL_ID}", config.THREAD_B_POLL_ID)
            
            body = {}
            if eid == "poll_b_close": body = {"poll_status": "CLOSED"}
            if eid == "poll_b_vote": body = {"option_index": 0}
            
            res_dict = safe_make_request(endpoint.method, url, config.THREADS_TOKEN_A, body=body, delay_ms=delay_ms)
            
            classification = "ERROR" if res_dict["error"] else "AMBIGUOUS"
            result = TestResult(
                endpoint_id=eid,
                token_label="THREADS_FULL",
                http_status=res_dict["status_code"],
                response_body=res_dict["text"],
                duration_ms=res_dict["duration_ms"],
                classification=classification
            )
            
            if not res_dict["error"]:
                classified = classify_response(result, endpoint, is_bola_test=True if "b" in eid else False)
                if classified.classification == "CONFIRMED_FINDING":
                    console.print(f"\n[bold red on yellow] 🔴 FRESH FEATURE BYPASS CONFIRMED: {eid} (HTTP {result.http_status}) [/bold red on yellow]")
                save_result_callback(classified, url, endpoint.method, "{}", endpoint.is_fresh_code, endpoint.is_write)
            else:
                save_result_callback(result, url, endpoint.method, "{}", endpoint.is_fresh_code, endpoint.is_write)
                
            pbar.update(1)
