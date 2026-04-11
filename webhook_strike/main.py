import click
import json
from .sender import Sender
from .payloads import get_payload
from .receiver import run_server

@click.group()
def cli():
    """WEBHOOK-STRIKE: Threads webhook signature validation testing tool."""
    pass

@cli.command()
@click.option("--target-url", required=True, help="Target Webhook URL")
@click.option("--payload", default="MENTION", type=click.Choice(["MENTION", "REPLY", "FOLLOW", "ACCOUNT_DELETE"]))
@click.option("--target-user-id", required=True)
@click.option("--attacker-user-id", required=True)
@click.option("--captured-sig", help="Optional captured signature for replay test")
def attack(target_url, payload, target_user_id, attacker_user_id, captured_sig):
    sender = Sender(target_url)
    sender.run_tests(target_user_id, attacker_user_id, payload_type=payload, captured_sig=captured_sig)

@cli.command()
@click.option("--port", default=8080)
@click.option("--app-secret", required=True)
@click.option("--verify-token", required=True)
def serve(port, app_secret, verify_token):
    run_server(port, app_secret, verify_token)

@cli.command()
@click.option("--type", "payload_type", required=True, type=click.Choice(["MENTION", "REPLY", "FOLLOW", "ACCOUNT_DELETE"]))
def generate_payload(payload_type):
    payload = get_payload(payload_type, "TARGET_ID", "ATTACKER_ID")
    click.echo(json.dumps(payload, indent=2))

if __name__ == "__main__":
    cli()
