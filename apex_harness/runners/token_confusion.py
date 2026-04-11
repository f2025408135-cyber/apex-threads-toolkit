import time
from typing import Dict, Any, Callable
from ..classifier import TestResult, classify_response
from ..endpoints import endpoints_registry, Endpoint
from ..config import Config
from rich.console import Console
from ..request_utils import safe_make_request
from tqdm import tqdm
import concurrent.futures

console = Console()

def substitute_url(url_template: str, config: Config) -> str:
    url = url_template.replace("{USER_B_THREADS_ID}", config.USER_B_THREADS_ID)
    url = url.replace("{THREAD_B_TEXT_ID}", config.THREAD_B_TEXT_ID)
    url = url.replace("{THREAD_B_POLL_ID}", config.THREAD_B_POLL_ID)
    return url

def run_token_confusion(config: Config, save_result_callback: Callable, delay_ms: int = 500):
    tokens = {
        "THREADS_FULL": config.THREADS_TOKEN_A,
        "THREADS_NARROW": config.THREADS_TOKEN_A_NARROW,
        "THREADS_B": config.THREADS_TOKEN_B,
        "FACEBOOK_USER": config.FB_TOKEN_A,
        "APP_ACCESS": config.APP_TOKEN_A,
        "UNAUTHENTICATED": ""
    }
    
    console.print("\n[bold cyan]Running Token Confusion Matrix[/bold cyan]")
    
    tests_to_run = []
    for endpoint in endpoints_registry:
        url = substitute_url(endpoint.url_template, config)
        for token_label, token_val in tokens.items():
            tests_to_run.append((endpoint, url, token_label, token_val, None))
            if endpoint.method == "POST":
                body = {}
                if "manage_reply" in url:
                    body = {"hide": "true"}
                elif "poll_vote" in url:
                    body = {"option_index": 0}
                elif "poll_status" in url: 
                    body = {"poll_status": "CLOSED"}
                tests_to_run.append((endpoint, url, token_label, token_val, body))
                
    # Extra tests
    extra_tests = [
        ("FB_TOKEN_A_ME", "https://graph.threads.net/v1.0/me", config.FB_TOKEN_A, "FACEBOOK_USER"),
        ("FB_TOKEN_A_USER_B_THREADS", f"https://graph.threads.net/v1.0/{config.USER_B_THREADS_ID}/threads", config.FB_TOKEN_A, "FACEBOOK_USER"),
        ("FB_TOKEN_A_USER_B_INSIGHTS", f"https://graph.threads.net/v1.0/{config.USER_B_THREADS_ID}/insights", config.FB_TOKEN_A, "FACEBOOK_USER")
    ]
    for test_id, url, token_val, label in extra_tests:
        fake_endpoint = Endpoint(id=test_id, method="GET", url_template=url, required_scope="", fields="", description="", expected_auth="THREADS_USER")
        tests_to_run.append((fake_endpoint, url, label, token_val, None))
        
    # Version sweep
    versions = ["v1.0", "v2.0", "v19.0", "v20.0", "v21.0"]
    for version in versions:
        url = f"https://graph.threads.net/{version}/me"
        fake_endpoint = Endpoint(id=f"me_version_{version}", method="GET", url_template=url, required_scope="", fields="", description="", expected_auth="THREADS_USER")
        tests_to_run.append((fake_endpoint, url, "THREADS_FULL", config.THREADS_TOKEN_A, None))

    def execute_test(args):
        endpoint, url, token_label, token_val, body = args
        res_dict = safe_make_request(endpoint.method, url, token_val, body=body, delay_ms=delay_ms)
        
        classification = "ERROR" if res_dict["error"] else ("RATE_LIMITED" if res_dict["status_code"] == 429 else "AMBIGUOUS")
        
        result = TestResult(
            endpoint.id, 
            token_label, 
            res_dict["status_code"], 
            res_dict["text"], 
            res_dict["duration_ms"], 
            classification=classification
        )
        
        if not res_dict["error"]:
            classified_result = classify_response(result, endpoint)
            if classified_result.classification == "CONFIRMED_FINDING":
                console.print(f"\n[bold red on yellow] 🔴 CONFIRMED_FINDING: {token_label} -> {endpoint.id} (HTTP {result.http_status}) [/bold red on yellow]")
            save_result_callback(classified_result, url, endpoint.method, "{}", endpoint.is_fresh_code, endpoint.is_write)
        else:
            save_result_callback(result, url, endpoint.method, "{}", endpoint.is_fresh_code, endpoint.is_write)
            
        return endpoint.id

    console.print(f"\n[cyan]Executing {len(tests_to_run)} tests concurrently...[/cyan]")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        with tqdm(total=len(tests_to_run), desc="Running: TOKEN_CONFUSION") as pbar:
            futures = {executor.submit(execute_test, test): test for test in tests_to_run}
            for future in concurrent.futures.as_completed(futures):
                try:
                    eid = future.result()
                    pbar.set_postfix({"endpoint_id": eid})
                except Exception as exc:
                    console.print(f"[red]Test generated an exception: {exc}[/red]")
                finally:
                    pbar.update(1)
