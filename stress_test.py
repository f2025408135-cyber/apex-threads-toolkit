import subprocess
import concurrent.futures
import time
import os
from rich.console import Console

console = Console()

# We set dummy environment variables so the tool actually runs completely
env_vars = os.environ.copy()
env_vars.update({
    "APP_ID_A": "1",
    "APP_SECRET_A": "1",
    "APP_ID_B": "1",
    "APP_TOKEN_A": "1",
    "THREADS_TOKEN_A": "1",
    "THREADS_TOKEN_A_NARROW": "1",
    "THREADS_TOKEN_B": "1",
    "FB_TOKEN_A": "1",
    "USER_A_THREADS_ID": "1",
    "USER_B_THREADS_ID": "1",
    "THREAD_B_TEXT_ID": "1",
    "THREAD_B_POLL_ID": "1"
})

def run_suite_instance(run_id: int):
    # Run the heavy token confusion test which has internal thread pooling too!
    start = time.time()
    try:
        # delay_ms=0 to bombard the DB as fast as possible
        cmd = ["apex-harness", "run-suite", "--suite=TOKEN_CONFUSION", "--delay-ms=0"]
        result = subprocess.run(
            cmd,
            env=env_vars,
            capture_output=True,
            text=True,
            timeout=180
        )
        duration = time.time() - start
        
        if result.returncode != 0:
            return f"Run {run_id} FAILED in {duration:.1f}s: {result.stderr[-200:]}"
            
        if "OperationalError" in result.stderr or "locked" in result.stderr:
            return f"Run {run_id} FAILED (DB LOCKED) in {duration:.1f}s"
            
        return f"Run {run_id} SUCCESS in {duration:.1f}s"
        
    except Exception as e:
        return f"Run {run_id} EXCEPTION: {str(e)}"

def stress_test_50x():
    concurrency = 50
    console.print(f"\n[bold red]🔥 INITIATING 50x MULTI-PROCESS STRESS TEST 🔥[/bold red]")
    console.print(f"Launching {concurrency} complete 'Token Confusion' suites simultaneously...")
    console.print(f"Total concurrent HTTP requests generated internally: {concurrency} * 152 = 7,600 reqs\n")
    
    start_total = time.time()
    success_count = 0
    fail_count = 0
    
    # 50 complete instances running in parallel processes (simulating 50 users clicking "Run" simultaneously)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(run_suite_instance, i): i for i in range(1, concurrency + 1)}
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if "SUCCESS" in res:
                success_count += 1
                console.print(f"[green]✅ {res}[/green]")
            else:
                fail_count += 1
                console.print(f"[red]❌ {res}[/red]")
                
    duration_total = time.time() - start_total
    
    console.print("\n[bold cyan]=== STRESS TEST RESULTS ===[/bold cyan]")
    console.print(f"Total Duration: {duration_total:.2f}s")
    console.print(f"Successful Runs: [green]{success_count}/50[/green]")
    console.print(f"Failed/Locked Runs: [red]{fail_count}/50[/red]")
    
    if fail_count == 0:
        console.print("\n[bold green]🛡️ TOOLKIT IS 100% ENTERPRISE READY. ZERO CRASHES UNDER 50x EXTREME LOAD. 🛡️[/bold green]\n")
    else:
        console.print("\n[bold red]⚠️ TOOLKIT FAILED STRESS TEST. TUNING REQUIRED. ⚠️[/bold red]\n")

if __name__ == "__main__":
    stress_test_50x()
