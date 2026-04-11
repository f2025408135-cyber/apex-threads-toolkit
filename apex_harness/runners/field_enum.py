import time
import json
from ..config import Config
from ..classifier import classify_response, TestResult
from ..endpoints import Endpoint
from typing import Callable
from rich.console import Console
from ..request_utils import safe_make_request
from tqdm import tqdm

console = Console()

def run_field_enum(config: Config, save_result_callback: Callable, delay_ms: int = 500):
    console.print("\n[bold cyan]Running Undocumented Field Enumeration[/bold cyan]")
    
    candidates = [
        "email", "phone_number", "contact_email", "business_email",
        "date_of_birth", "age", "gender", "location", "country", "city",
        "ip_address", "device_id", "session_id", "private_key",
        "is_private", "account_type", "linked_facebook_id", "linked_instagram_id",
        "two_factor_enabled", "recovery_codes", "password_last_changed",
        "login_history", "connected_apps", "access_token", "refresh_token",
        "created_time", "last_active", "email_verified", "phone_verified",
        "professional_account_category", "professional_account_subcategory",
        "has_onboarded_to_ig", "interop_messaging_user_fbid",
        "linked_ig_user_id", "page_backed_instagram_account_id"
    ]
    
    url = "https://graph.threads.net/v1.0/me"
    
    with tqdm(total=len(candidates), desc="Running: FIELD_ENUM") as pbar:
        for field in candidates:
            pbar.set_postfix({"field": field})
            
            params = {"fields": field, "access_token": config.THREADS_TOKEN_A}
            res_dict = safe_make_request("GET", url, config.THREADS_TOKEN_A, params=params, delay_ms=delay_ms)
            
            classification = "ERROR" if res_dict["error"] else "AMBIGUOUS"
            result = TestResult("me_field_enum", "THREADS_FULL", res_dict["status_code"], res_dict["text"], res_dict["duration_ms"], classification=classification)
            
            if not res_dict["error"]:
                if res_dict["status_code"] == 200:
                    try:
                        data = json.loads(res_dict["text"])
                        if field in data and data[field] is not None:
                            result.classification = "PROBABLE_FINDING"
                            result.confidence = "HIGH"
                            result.finding_class = "Undocumented Field Disclosure"
                            result.notes = f"Field found: {field}={data[field]}"
                            console.print(f"\n[bold orange3] 🟠 PROBABLE_FINDING: Undocumented field '{field}' returned! [/bold orange3]")
                        else:
                            result.classification = "NULL_SIGNAL"
                    except json.JSONDecodeError:
                        pass
                
                save_result_callback(result, url, "GET", "{}", False, False)
            else:
                save_result_callback(result, url, "GET", "{}", False, False)
                
            pbar.update(1)
            
    # Wildcard test
    console.print("\n[cyan]Testing wildcard fields...[/cyan]")
    wildcard_urls = [
        ("me_wildcard", "https://graph.threads.net/v1.0/me", "id,username,name,biography,profile_picture_url,followers_count,following_count,is_verified,link_in_bio,threads_profile_audience_type"),
        ("user_b_wildcard", f"https://graph.threads.net/v1.0/{config.USER_B_THREADS_ID}", "id,username,name,biography,profile_picture_url,followers_count,following_count,is_verified,link_in_bio")
    ]
    
    for eid, w_url, doc_fields in wildcard_urls:
        params = {"fields": "*", "access_token": config.THREADS_TOKEN_A}
        res_dict = safe_make_request("GET", w_url, config.THREADS_TOKEN_A, params=params, delay_ms=delay_ms)
        
        classification = "ERROR" if res_dict["error"] else "AMBIGUOUS"
        result = TestResult(eid, "THREADS_FULL", res_dict["status_code"], res_dict["text"], res_dict["duration_ms"], classification=classification)
        
        if not res_dict["error"]:
            if res_dict["status_code"] == 200:
                try:
                    data = json.loads(res_dict["text"])
                    returned_fields = set(data.keys())
                    documented = set(doc_fields.split(","))
                    extra = returned_fields - documented
                    
                    if extra:
                        result.classification = "PROBABLE_FINDING"
                        result.confidence = "HIGH"
                        result.finding_class = "Undocumented Field Disclosure (Wildcard)"
                        result.notes = f"Extra fields: {','.join(extra)}"
                        console.print(f"\n[bold orange3] 🟠 PROBABLE_FINDING: Wildcard returned extra fields: {','.join(extra)} [/bold orange3]")
                    else:
                        result.classification = "NULL_SIGNAL"
                except json.JSONDecodeError:
                    pass
            save_result_callback(result, w_url, "GET", "{}", False, False)
        else:
            save_result_callback(result, w_url, "GET", "{}", False, False)
