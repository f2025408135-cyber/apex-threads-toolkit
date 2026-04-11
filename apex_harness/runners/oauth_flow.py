import time
from ..config import Config
from ..classifier import classify_response, TestResult
from typing import Callable
from rich.console import Console
from ..request_utils import safe_make_request
from tqdm import tqdm

console = Console()

def run_oauth_flow(config: Config, save_result_callback: Callable, test_code: str = None):
    console.print("\n[bold blue]Running OAuth Flow Tests[/bold blue]")
    
    tasks = []
    if test_code:
        tasks.append("auth_code_reuse")
    tasks.append("token_refresh")
    tasks.append("token_exchange")
    
    with tqdm(total=len(tasks), desc="Running: OAUTH_FLOW") as pbar:
        # Test 1: Auth code reuse
        if test_code:
            pbar.set_postfix({"test": "auth_code_reuse"})
            console.print("\n[cyan]Test 1: Auth Code Reuse[/cyan]")
            url = "https://graph.threads.net/oauth/access_token"
            data = {
                "client_id": config.APP_ID_A,
                "client_secret": config.APP_SECRET_A,
                "code": test_code,
                "grant_type": "authorization_code",
                "redirect_uri": "https://localhost:3000/callback"
            }
            res1 = safe_make_request("POST", url, None, body=data)
            res2 = safe_make_request("POST", url, None, body=data)
            console.print(f"Second exchange status: {res2['status_code']}")
            pbar.update(1)

        # Test 2: Token refresh after revocation (Interactive)
        pbar.set_postfix({"test": "token_refresh"})
        console.print("\n[cyan]Test 2: Token Refresh After Revocation[/cyan]")
        me_url = "https://graph.threads.net/v1.0/me"
        res = safe_make_request("GET", me_url, config.THREADS_TOKEN_A)
        if res["status_code"] == 200:
            console.print("✅ Token is currently valid.")
            console.print("Instruction: Go to Threads settings -> Security -> Apps and Websites -> Revoke your test app.")
            input("Press ENTER when you have revoked the token...")
            res_after = safe_make_request("GET", me_url, config.THREADS_TOKEN_A)
            if res_after["status_code"] == 200:
                console.print("\n[bold red] 🔴 CONFIRMED_FINDING: Token valid after revocation![/bold red]")
            else:
                console.print("\n[green]✅ Token correctly invalidated.[/green]")
        pbar.update(1)

        # Test 3: Token exchange with wrong product token
        pbar.set_postfix({"test": "token_exchange"})
        console.print("\n[cyan]Test 3: Token Exchange Endpoint Wrong Product[/cyan]")
        exchange_url = "https://graph.threads.net/access_token"
        params = {
            "grant_type": "th_exchange_token",
            "client_secret": config.APP_SECRET_A,
            "access_token": config.FB_TOKEN_A
        }
        res_ex = safe_make_request("GET", exchange_url, None, params=params)
        console.print(f"Facebook token exchange status: {res_ex['status_code']}")
        pbar.update(1)
        
    # Generate Manual URLs
    console.print("\n[bold yellow]Generating Manual Test URLs...[/bold yellow]")
    
    urls = [
        f"https://threads.net/oauth/authorize?client_id={config.APP_ID_A}&redirect_uri=https://evil.localhost:3000/callback&scope=threads_basic&response_type=code&state=subdomain_test",
        f"https://threads.net/oauth/authorize?client_id={config.APP_ID_A}&redirect_uri=https://localhost:3000/callback/../../../evil&scope=threads_basic&response_type=code&state=traversal_test",
        f"https://threads.net/oauth/authorize?client_id={config.APP_ID_A}&redirect_uri=https://localhost:3000/callback#@evil.com&scope=threads_basic&response_type=code&state=fragment_test",
        f"https://threads.net/oauth/authorize?client_id={config.APP_ID_A}&redirect_uri=https://localhost:3000/callback&scope=threads_basic&response_type=code",
        f"https://threads.net/oauth/authorize?client_id={config.APP_ID_A}&redirect_uri=https://localhost:3000/callback&scope=threads_basic,threads_manage_insights,threads_content_publish,threads_manage_replies,threads_read_replies,threads_keyword_search&response_type=code&state=scope_inflation_test"
    ]
    
    with open("./output/oauth_manual_tests.txt", "w") as f:
        for u in urls:
            console.print(u)
            f.write(u + "\n\n")
            
    console.print("\nURLs saved to ./output/oauth_manual_tests.txt")
