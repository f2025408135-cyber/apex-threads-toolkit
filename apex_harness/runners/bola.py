import time
from ..config import Config
from ..endpoints import endpoints_registry, Endpoint
from ..classifier import classify_response, TestResult
from typing import Callable
from rich.console import Console
from ..request_utils import safe_make_request
from tqdm import tqdm

console = Console()

def run_bola_tests(config: Config, save_result_callback: Callable, delay_ms: int = 500, run_write_tests: bool = False, run_delete_test: bool = False):
    console.print("\n[bold magenta]Running BOLA Tests[/bold magenta]")
    
    # Read bola
    read_bola_endpoints = [
        "user_b_insights", "thread_b_insights", "publishing_limit_user_b", "poll_b_results", "thread_b_location"
    ]
    
    tests_to_run = []
    
    for eid in read_bola_endpoints:
        endpoint = next((e for e in endpoints_registry if e.id == eid), None)
        if endpoint:
            url = endpoint.url_template.replace("{USER_B_THREADS_ID}", config.USER_B_THREADS_ID)
            url = url.replace("{THREAD_B_TEXT_ID}", config.THREAD_B_TEXT_ID)
            url = url.replace("{THREAD_B_POLL_ID}", config.THREAD_B_POLL_ID)
            tests_to_run.append((endpoint, url, None))
            
    if run_write_tests:
        console.print("[bold red]WARNING: The following tests attempt WRITE operations on Account B's content.[/bold red]")
        val = input("Type CONFIRM to run write tests or SKIP to skip them: ")
        if val == "CONFIRM":
            write_bola_endpoints = ["manage_reply_hide", "poll_b_close", "poll_b_vote"]
            for eid in write_bola_endpoints:
                endpoint = next((e for e in endpoints_registry if e.id == eid), None)
                if endpoint:
                    url = endpoint.url_template.replace("{USER_B_THREADS_ID}", config.USER_B_THREADS_ID)
                    url = url.replace("{THREAD_B_TEXT_ID}", config.THREAD_B_TEXT_ID)
                    url = url.replace("{THREAD_B_POLL_ID}", config.THREAD_B_POLL_ID)
                    body = {}
                    if eid == "manage_reply_hide": body = {"hide": "true"}
                    if eid == "poll_b_close": body = {"poll_status": "CLOSED"}
                    if eid == "poll_b_vote": body = {"option_index": 0}
                    tests_to_run.append((endpoint, url, body))
                    
    if run_delete_test:
        endpoint = next((e for e in endpoints_registry if e.id == "delete_thread_b"), None)
        if endpoint:
            url = endpoint.url_template.replace("{THREAD_B_TEXT_ID}", config.THREAD_B_TEXT_ID)
            tests_to_run.append((endpoint, url, None))

    with tqdm(total=len(tests_to_run), desc="Running: BOLA") as pbar:
        for i, (endpoint, url, body) in enumerate(tests_to_run):
            pbar.set_postfix({"endpoint_id": endpoint.id})
            
            res_dict = safe_make_request(endpoint.method, url, config.THREADS_TOKEN_A, body=body, delay_ms=delay_ms)
            
            classification = "ERROR" if res_dict["error"] else "AMBIGUOUS"
            result = TestResult(
                endpoint.id, 
                "THREADS_FULL", 
                res_dict["status_code"], 
                res_dict["text"], 
                res_dict["duration_ms"], 
                classification=classification
            )
            
            if not res_dict["error"]:
                classified = classify_response(result, endpoint, is_bola_test=True)
                if classified.classification == "CONFIRMED_FINDING":
                    console.print(f"\n[bold red on white] 🔴 BOLA CONFIRMED: {endpoint.id} (HTTP {result.http_status}) [/bold red on white]")
                save_result_callback(classified, url, endpoint.method, "{}", endpoint.is_fresh_code, endpoint.is_write)
            else:
                save_result_callback(result, url, endpoint.method, "{}", endpoint.is_fresh_code, endpoint.is_write)
                
            pbar.update(1)
