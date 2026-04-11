# APEX-HARNESS

Automated security test execution engine for the Threads API.

## Installation

The easiest way to install this tool so you can run it anywhere is:
```bash
cd ..  # Go to the root of the apex-threads-toolkit repository
pip install -e .
```

This makes the `apex-harness` command globally available.

## Launching the Native Desktop Application
You can run APEX-HARNESS as a standalone local graphical application!

1. Install dependencies: `pip install -r requirements.txt`
2. Run the desktop application wrapper:
```bash
python desktop_app.py
```
This will launch a native window connecting to the internal Flask interface.

### Building a Standalone Executable
To package the tool into a single clickable binary (e.g., an `.app` or `.exe` depending on your OS) that you can share or run without Python installed:
```bash
./build_app.sh
```
Find the completed built package in the `dist/` directory.

## Required Environment Variables
Create a `.env` file in the same directory as the executable (or `main.py`) with the following:
```
APP_ID_A=
APP_SECRET_A=
APP_ID_B=
APP_TOKEN_A=
THREADS_TOKEN_A=
THREADS_TOKEN_A_NARROW=
THREADS_TOKEN_B=
FB_TOKEN_A=
USER_A_THREADS_ID=
USER_B_THREADS_ID=
THREAD_B_TEXT_ID=
THREAD_B_POLL_ID=
THREAD_B_GEO_ID=
USER_B_USERNAME=
```

## Usage

After installing via `pip install .`, run:
```bash
apex-harness run-all
apex-harness run-suite --suite=TOKEN_CONFUSION
apex-harness run-oauth
apex-harness run-race --race-count=20
apex-harness show-findings
apex-harness update-finding --id=APEX-2025-001 --status=FILING
apex-harness generate-report --run-id=UUID
apex-harness run-delete-test
apex-harness ui --port 5005
```
