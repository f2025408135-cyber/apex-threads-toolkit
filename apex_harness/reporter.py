from .database import Database, Finding
from typing import List
from rich.console import Console
from rich.table import Table
import os
import json
from jinja2 import Template

console = Console()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>APEX-HARNESS Report - {{ run_id }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 2rem; background: #f9f9f9; color: #333; }
        h1, h2, h3 { color: #111; }
        .summary-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem; }
        .finding-card { background: white; border-left: 5px solid #dc3545; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
        .finding-card.probable { border-left-color: #fd7e14; }
        .code-block { background: #f1f3f5; padding: 1rem; border-radius: 4px; overflow-x: auto; font-family: monospace; font-size: 0.9em; }
        .tag { display: inline-block; padding: 0.25em 0.5em; border-radius: 4px; font-size: 0.85em; font-weight: 600; color: white; }
        .tag-critical { background: #dc3545; }
        .tag-high { background: #fd7e14; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background: #e9ecef; }
        button { background: #007bff; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>APEX-HARNESS Security Report</h1>
    <div class="summary-card">
        <h2>Run Summary</h2>
        <p><strong>Run ID:</strong> {{ run_id }}</p>
        <p><strong>Completed:</strong> {{ completed_at }}</p>
        <p><strong>Total Tests:</strong> {{ metadata.total_tests }}</p>
        <p><strong><span style="color: #dc3545;">🔴 CONFIRMED:</span></strong> {{ metadata.confirmed_findings }}</p>
        <p><strong><span style="color: #fd7e14;">🟠 PROBABLE:</span></strong> {{ metadata.probable_findings }}</p>
        <p><strong><span style="color: #28a745;">✅ NULL SIGNALS:</span></strong> {{ metadata.null_signals }}</p>
        <p><strong><span style="color: #ffc107;">⚠️ AMBIGUOUS:</span></strong> {{ metadata.ambiguous }}</p>
        <p><strong>❌ ERRORS:</strong> {{ metadata.errors }}</p>
    </div>

    <h2>Findings</h2>
    {% if findings %}
        {% for finding in findings %}
        <div class="finding-card {% if finding.classification == 'PROBABLE_FINDING' %}probable{% endif %}">
            <h3>{{ finding.finding_class }} ({{ finding.finding_id }})</h3>
            <p><span class="tag {% if finding.classification == 'CONFIRMED_FINDING' %}tag-critical{% else %}tag-high{% endif %}">{{ finding.classification }}</span></p>
            <p><strong>Endpoint:</strong> {{ finding.endpoint_id }}</p>
            <p><strong>Token:</strong> {{ finding.token_label }}</p>
            <p><strong>HTTP Status:</strong> {{ finding.http_status }}</p>
            
            <h4>Response Body:</h4>
            <div class="code-block">{{ finding.response_body }}</div>
            
            {% if finding.classification == 'CONFIRMED_FINDING' %}
            <h4>Meta Bug Bounty Template:</h4>
            <div class="code-block">
Vulnerability Title: {{ finding.finding_class }} on {{ finding.endpoint_id }}
Severity: High/Critical
CVSS Vector: [Researcher fills in]

Summary:
An authorization issue was discovered on {{ finding.endpoint_id }}. By using a {{ finding.token_label }} token, it was possible to access or modify data unexpectedly, resulting in an HTTP {{ finding.http_status }} response.

Steps to Reproduce:
1. Obtain {{ finding.token_label }} token
2. Send request to endpoint {{ finding.endpoint_id }}
3. Observe response: HTTP {{ finding.http_status }}
4. Notice the returned data or action success:
{{ finding.response_body[:200] }}...

Expected Behavior:
The server should have rejected the request with HTTP 403.

Actual Behavior:
The server returned HTTP {{ finding.http_status }} and processed the request.

Impact:
{{ finding.finding_class }} could lead to unauthorized data access or modification.
            </div>
            {% endif %}
            <br>
            <button onclick='alert("Raw JSON: " + `{{ finding.response_body | escape }}`)'>Export Raw JSON</button>
        </div>
        {% endfor %}
    {% else %}
        <p>No confirmed or probable findings. 🎉</p>
    {% endif %}

</body>
</html>
"""

class Reporter:
    def __init__(self, db: Database):
        self.db = db

    def print_terminal_summary(self, run_id: str):
        metadata = self.db.get_run_summary(run_id)
        if not metadata:
            console.print("[red]Run metadata not found for summary.[/red]")
            return

        findings = self.db.get_findings_by_run(run_id)

        console.print(f"\n[bold]╔{'═'*54}╗[/bold]")
        console.print(f"[bold]║  APEX-HARNESS RUN SUMMARY{' '*27}║[/bold]")
        console.print(f"[bold]║  Run ID: {run_id:<41}║[/bold]")
        console.print(f"[bold]║  Completed: {metadata.get('completed_at', 'N/A'):<38}║[/bold]")
        console.print(f"[bold]╠{'═'*54}╣[/bold]")
        console.print(f"[bold]║  Total Tests:        {metadata.get('total_tests', 0):<32}║[/bold]")
        console.print(f"[bold]║  [red]🔴 CONFIRMED:[/red]       {metadata.get('confirmed_findings', 0):<32}║[/bold]")
        console.print(f"[bold]║  [dark_orange]🟠 PROBABLE:[/dark_orange]        {metadata.get('probable_findings', 0):<32}║[/bold]")
        console.print(f"[bold]║  [green]✅ NULL SIGNALS:[/green]    {metadata.get('null_signals', 0):<32}║[/bold]")
        console.print(f"[bold]║  [yellow]⚠️  AMBIGUOUS:[/yellow]      {metadata.get('ambiguous', 0):<32}║[/bold]")
        console.print(f"[bold]║  ❌ ERRORS:          {metadata.get('errors', 0):<32}║[/bold]")
        console.print(f"[bold]╠{'═'*54}╣[/bold]")
        console.print(f"[bold]║  FINDINGS REQUIRING ACTION:{' '*26}║[/bold]")
        
        for f in findings:
            if f.classification in ["CONFIRMED_FINDING", "PROBABLE_FINDING"]:
                msg = f"{f.finding_id} | {f.endpoint_id} | {f.token_label}"
                console.print(f"[bold]║  {msg:<52}║[/bold]")
                
        console.print(f"[bold]╚{'═'*54}╝[/bold]\n")

    def generate_html_report(self, run_id: str):
        metadata = self.db.get_run_summary(run_id)
        findings = self.db.get_findings_by_run(run_id)
        
        # sort findings: confirmed first
        findings.sort(key=lambda x: 0 if x.classification == "CONFIRMED_FINDING" else 1)

        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            run_id=run_id,
            completed_at=metadata.get("completed_at", "N/A"),
            metadata=metadata,
            findings=findings
        )
        
        filepath = f"./output/report_{run_id}.html"
        with open(filepath, "w") as f:
            f.write(html_content)
            
        console.print(f"[green]HTML Report generated at: {filepath}[/green]")
