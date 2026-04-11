import time
from ..config import Config
from ..endpoints import endpoints_registry, Endpoint
from ..classifier import classify_response, TestResult
from typing import Callable
from rich.console import Console
from ..request_utils import safe_make_request
from tqdm import tqdm

console = Console()

def run_scope_enforcement(config: Config, save_result_callback: Callable, delay_ms: int = 500):
    console.print("\n[bold green]Running Scope Enforcement Tests[/bold green]")
    
    test_matrix = [
        {"endpoint": "me_insights", "required": "threads_manage_insights", "expected": 403},
        {"endpoint": "me_threads", "required": "threads_basic", "expected": 200},
        {"endpoint": "manage_reply_hide", "required": "threads_manage_replies", "expected": 403},
        {"endpoint": "thread_b_replies", "required": "threads_read_replies", "expected": 403},
        {"endpoint": "keyword_search", "required": "threads_keyword_search", "expected": 403},
        {"endpoint": "user_b_insights", "required": "threads_manage_insights", "expected": 403}
    ]
    
    with tqdm(total=len(test_matrix), desc="Running: SCOPE_ENFORCEMENT") as pbar:
        for test in test_matrix:
            eid = test["endpoint"]
            pbar.set_postfix({"endpoint_id": eid})
            
            endpoint = next((e for e in endpoints_registry if e.id == eid), None)
            if not endpoint:
                pbar.update(1)
                continue
                
            url = endpoint.url_template.replace("{USER_B_THREADS_ID}", config.USER_B_THREADS_ID)
            url = url.replace("{THREAD_B_TEXT_ID}", config.THREAD_B_TEXT_ID)
            
            body = {}
            if eid == "manage_reply_hide": body = {"hide": "true"}
            
            res_dict = safe_make_request(endpoint.method, url, config.THREADS_TOKEN_A_NARROW, body=body, delay_ms=delay_ms)
            
            classification = "ERROR" if res_dict["error"] else "AMBIGUOUS"
            
            result = TestResult(
                endpoint.id, 
                "THREADS_NARROW", 
                res_dict["status_code"], 
                res_dict["text"], 
                res_dict["duration_ms"], 
                classification=classification
            )
            
            if not res_dict["error"]:
                classified = classify_response(result, endpoint)
                if result.http_status == 200 and test["expected"] == 403:
                    classified.classification = "CONFIRMED_FINDING"
                    classified.confidence = "HIGH"
                    classified.finding_class = "Scope Not Enforced Per-Handler"
                    console.print(f"\n[bold red on yellow] 🔴 SCOPE ENFORCEMENT FAILED: {eid} (HTTP 200) [/bold red on yellow]")
                elif result.http_status == 403 and (classified.oauth_error_code in [10, 200] or '"code": 10' in result.response_body or '"code": 200' in result.response_body):
                    classified.classification = "NULL_SIGNAL"
                elif result.http_status == 200 and test["expected"] == 200:
                    classified.classification = "NULL_SIGNAL"
                else:
                    classified.classification = "AMBIGUOUS"
                    
                save_result_callback(classified, url, endpoint.method, "{}", endpoint.is_fresh_code, endpoint.is_write)
            else:
                save_result_callback(result, url, endpoint.method, "{}", endpoint.is_fresh_code, endpoint.is_write)
                
            pbar.update(1)
