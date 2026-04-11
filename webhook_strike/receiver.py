import os
import hmac
import hashlib
from flask import Flask, request, jsonify
from rich.console import Console
import datetime

console = Console()
app = Flask(__name__)

APP_SECRET = os.environ.get("APP_SECRET", "dummy_secret")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "dummy_token")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                console.print(f"[green]WEBHOOK_VERIFIED[/green]")
                return challenge, 200
            else:
                return "Forbidden", 403
                
    elif request.method == "POST":
        signature = request.headers.get("X-Hub-Signature-256")
        body = request.get_data()
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        console.print(f"{timestamp} | POST | /webhook | Received payload: {body.decode('utf-8')[:100]}...")

        if not signature:
            console.print("[red]Missing X-Hub-Signature-256[/red]")
            return "Forbidden", 403

        expected_sig = "sha256=" + hmac.new(APP_SECRET.encode('utf-8'), body, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            console.print("[red]Signature mismatch[/red]")
            return "Forbidden", 403

        console.print("[green]Valid signature[/green]")
        return "OK", 200

def run_server(port: int, secret: str, token: str):
    global APP_SECRET, VERIFY_TOKEN
    APP_SECRET = secret
    VERIFY_TOKEN = token
    app.run(host="0.0.0.0", port=port)
