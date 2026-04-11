import click
import uuid
import datetime
import asyncio
from typing import List

from .config import load_and_validate_config, validate_token_independence
from .database import Database, Finding
from .classifier import TestResult
from .reporter import Reporter

from .runners.token_confusion import run_token_confusion
from .runners.bola import run_bola_tests
from .runners.scope_enforcement import run_scope_enforcement
from .runners.oauth_flow import run_oauth_flow
from .runners.race_condition import run_race_condition
from .runners.field_enum import run_field_enum
from .runners.fresh_features import run_fresh_features

import logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

@click.group()
def cli():
    """APEX-HARNESS: Threads API Security Test Execution Engine"""
    pass

class TestContext:
    def __init__(self, run_id: str):
        self.config = load_and_validate_config()
        self.db = Database()
        self.reporter = Reporter(self.db)
        self.run_id = run_id
        self.start_time = datetime.datetime.utcnow()
        self.metadata = {
            "run_id": run_id,
            "started_at": self.start_time.isoformat() + "Z",
            "completed_at": "",
            "total_tests": 0,
            "confirmed_findings": 0,
            "probable_findings": 0,
            "null_signals": 0,
            "ambiguous": 0,
            "errors": 0
        }

    def save_result_callback(self, result: TestResult, endpoint_url: str, method: str, headers: str, is_fresh: bool, is_write: bool):
        self.db.save_result(result, self.run_id, endpoint_url, method, headers, is_fresh, is_write)
        
        self.metadata["total_tests"] += 1
        if result.classification == "CONFIRMED_FINDING":
            self.metadata["confirmed_findings"] += 1
            finding = Finding(
                run_id=self.run_id,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                finding_id=f"APEX-{datetime.datetime.now().year}-{self.metadata['confirmed_findings']:03d}",
                endpoint_id=result.endpoint_id,
                token_label=result.token_label,
                classification=result.classification,
                finding_class=result.finding_class,
                http_status=result.http_status,
                response_body=result.response_body
            )
            self.db.save_finding(finding)
        elif result.classification == "PROBABLE_FINDING":
            self.metadata["probable_findings"] += 1
            finding = Finding(
                run_id=self.run_id,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                finding_id=f"APEX-{datetime.datetime.now().year}-P{self.metadata['probable_findings']:03d}",
                endpoint_id=result.endpoint_id,
                token_label=result.token_label,
                classification=result.classification,
                finding_class=result.finding_class,
                http_status=result.http_status,
                response_body=result.response_body
            )
            self.db.save_finding(finding)
        elif result.classification == "NULL_SIGNAL":
            self.metadata["null_signals"] += 1
        elif result.classification == "AMBIGUOUS":
            self.metadata["ambiguous"] += 1
        elif result.classification == "ERROR":
            self.metadata["errors"] += 1

    def finalize(self):
        self.metadata["completed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        self.db.save_run_metadata(self.metadata)
        self.reporter.print_terminal_summary(self.run_id)
        self.reporter.generate_html_report(self.run_id)

@cli.command()
@click.option("--delay-ms", default=500, help="Delay between requests in ms")
@click.option("--run-delete-test", is_flag=True, help="Run DELETE BOLA test after explicit confirmation")
def run_all(delay_ms, run_delete_test):
    run_id = str(uuid.uuid4())
    ctx = TestContext(run_id)
    validate_token_independence(ctx.config)

    click.echo(f"Starting APEX-HARNESS Run: {run_id}")
    run_token_confusion(ctx.config, ctx.save_result_callback, delay_ms)
    run_scope_enforcement(ctx.config, ctx.save_result_callback, delay_ms)
    
    should_run_delete = False
    if run_delete_test:
        click.echo("This will attempt to DELETE a thread belonging to Account B.")
        val = input("Type DELETE-CONFIRM to proceed: ")
        if val == "DELETE-CONFIRM":
            should_run_delete = True
            
    run_bola_tests(ctx.config, ctx.save_result_callback, delay_ms, run_write_tests=False, run_delete_test=should_run_delete)
    run_field_enum(ctx.config, ctx.save_result_callback, delay_ms)
    run_fresh_features(ctx.config, ctx.save_result_callback, delay_ms)
    
    ctx.finalize()

@cli.command()
@click.option("--suite", required=True, type=click.Choice(["TOKEN_CONFUSION", "BOLA", "SCOPE", "OAUTH", "RACE", "FIELD_ENUM", "FRESH_FEATURES"]))
@click.option("--delay-ms", default=500)
def run_suite(suite, delay_ms):
    run_id = str(uuid.uuid4())
    ctx = TestContext(run_id)
    
    if suite == "TOKEN_CONFUSION":
        run_token_confusion(ctx.config, ctx.save_result_callback, delay_ms)
    elif suite == "BOLA":
        validate_token_independence(ctx.config)
        run_bola_tests(ctx.config, ctx.save_result_callback, delay_ms, run_write_tests=True, run_delete_test=False)
    elif suite == "SCOPE":
        run_scope_enforcement(ctx.config, ctx.save_result_callback, delay_ms)
    elif suite == "OAUTH":
        run_oauth_flow(ctx.config, ctx.save_result_callback)
    elif suite == "RACE":
        asyncio.run(run_race_condition(ctx.config, ctx.save_result_callback))
    elif suite == "FIELD_ENUM":
        run_field_enum(ctx.config, ctx.save_result_callback, delay_ms)
    elif suite == "FRESH_FEATURES":
        run_fresh_features(ctx.config, ctx.save_result_callback, delay_ms)
        
    ctx.finalize()

@cli.command()
def run_oauth():
    run_id = str(uuid.uuid4())
    ctx = TestContext(run_id)
    run_oauth_flow(ctx.config, ctx.save_result_callback)

@cli.command()
@click.option("--race-count", default=20)
def run_race(race_count):
    run_id = str(uuid.uuid4())
    ctx = TestContext(run_id)
    asyncio.run(run_race_condition(ctx.config, ctx.save_result_callback, race_count=race_count))
    ctx.finalize()

@cli.command()
def show_findings():
    ctx = TestContext("temp")
    findings = ctx.db.get_all_confirmed_findings()
    click.echo("--- CONFIRMED FINDINGS ---")
    for f in findings:
        click.echo(f"{f.finding_id}: {f.classification} on {f.endpoint_id} ({f.token_label}) - {f.status}")

@cli.command()
@click.option("--id", required=True)
@click.option("--status", required=True)
def update_finding(id, status):
    ctx = TestContext("temp")
    ctx.db.update_finding_status(id, status)
    click.echo(f"Updated {id} to {status}")

@cli.command()
@click.option("--run-id", required=True)
def generate_report(run_id):
    ctx = TestContext(run_id)
    ctx.reporter.generate_html_report(run_id)

@cli.command()
@click.option("--port", default=5000, help="Port to run the UI on")
def ui(port):
    """Launch the interactive web UI dashboard."""
    from .web import start_server
    click.echo(f"Starting APEX-HARNESS Web UI on port {port}...")
    start_server(port)

if __name__ == "__main__":
    cli()
