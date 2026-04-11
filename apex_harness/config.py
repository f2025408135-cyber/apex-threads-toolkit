import os
import sys
import requests
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console

console = Console()

@dataclass
class Config:
    APP_ID_A: str
    APP_SECRET_A: str
    APP_ID_B: str
    APP_TOKEN_A: str
    THREADS_TOKEN_A: str
    THREADS_TOKEN_A_NARROW: str
    THREADS_TOKEN_B: str
    FB_TOKEN_A: str
    USER_A_THREADS_ID: str
    USER_B_THREADS_ID: str
    THREAD_B_TEXT_ID: str
    THREAD_B_POLL_ID: str

    THREAD_B_GEO_ID: Optional[str] = None
    USER_B_USERNAME: Optional[str] = None

def load_and_validate_config() -> Config:
    load_dotenv()
    
    required_vars = [
        "APP_ID_A", "APP_SECRET_A", "APP_ID_B", "APP_TOKEN_A",
        "THREADS_TOKEN_A", "THREADS_TOKEN_A_NARROW", "THREADS_TOKEN_B",
        "FB_TOKEN_A", "USER_A_THREADS_ID", "USER_B_THREADS_ID",
        "THREAD_B_TEXT_ID", "THREAD_B_POLL_ID"
    ]
    
    config_dict = {}
    for var in required_vars:
        val = os.environ.get(var)
        if not val:
            console.print(f"[bold red]ERROR: Missing required environment variable: {var}[/bold red]")
            sys.exit(1)
        config_dict[var] = val
        
    optional_vars = ["THREAD_B_GEO_ID", "USER_B_USERNAME"]
    for var in optional_vars:
        val = os.environ.get(var)
        if not val:
            console.print(f"[yellow]WARNING: Missing optional environment variable: {var}[/yellow]")
        config_dict[var] = val

    return Config(**config_dict)

def validate_token_independence(config: Config) -> None:
    try:
        res_a = requests.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": config.THREADS_TOKEN_A, "access_token": config.APP_TOKEN_A},
            timeout=10
        )
        res_a.raise_for_status()
        data_a = res_a.json().get("data", {})
        app_id_from_a = data_a.get("app_id")

        res_b = requests.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": config.THREADS_TOKEN_B, "access_token": config.APP_TOKEN_A},
            timeout=10
        )
        res_b.raise_for_status()
        data_b = res_b.json().get("data", {})
        app_id_from_b = data_b.get("app_id")

        if app_id_from_a and app_id_from_b and app_id_from_a == app_id_from_b:
            console.print("[bold yellow]WARNING: Token A and Token B share the same app_id![/bold yellow]")
            console.print("[yellow]BOLA findings will be invalid at Meta.[/yellow]")
            val = input("Do you want to continue? (y/n): ")
            if val.lower() != 'y':
                console.print("[red]Exiting...[/red]")
                sys.exit(0)
    except requests.RequestException as e:
        console.print(f"[bold red]Error validating token independence: {e}[/bold red]")
        
config = load_and_validate_config()
