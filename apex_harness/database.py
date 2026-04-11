import sqlite3
import os
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .classifier import TestResult

@dataclass
class Finding:
    run_id: str
    timestamp: str
    finding_id: str
    endpoint_id: str
    token_label: str
    classification: str
    finding_class: Optional[str]
    http_status: int
    response_body: str
    impact_summary: str = ""
    cvss_estimate: str = ""
    bounty_range: str = ""
    status: str = "NEW"
    id: Optional[int] = None

import threading

class Database:
    def __init__(self, db_path: str = "./output/apex_harness.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # check_same_thread=False allows multiple threads to share the connection
        # timeout=60 allows threads to wait up to 60s instead of locking immediately during high concurrency
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=60.0)
        self.conn.row_factory = sqlite3.Row
        
        # Enterprise Hardening: Write-Ahead Logging (WAL) for heavy concurrent read/writes
        # Let SQLite block a bit if necessary to avoid locks under heavy concurrent writes
        self.conn.execute("PRAGMA busy_timeout=60000;")
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        
        self.lock = threading.Lock()
        self._initialize_schema()

    def _initialize_schema(self):
        with self.lock:
            try:
                with self.conn:
                    self.conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    endpoint_id TEXT NOT NULL,
                    endpoint_url TEXT NOT NULL,
                    http_method TEXT NOT NULL,
                    token_label TEXT NOT NULL,
                    http_status INTEGER,
                    response_body TEXT,
                    response_headers TEXT,
                    duration_ms INTEGER,
                    oauth_error_code INTEGER,
                    oauth_error_type TEXT,
                    classification TEXT NOT NULL,
                    confidence TEXT,
                    finding_class TEXT,
                    notes TEXT,
                    is_fresh_code INTEGER,
                    is_write_operation INTEGER
                )
            """)
            
                self.conn.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    finding_id TEXT NOT NULL,
                    endpoint_id TEXT NOT NULL,
                    token_label TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    finding_class TEXT,
                    http_status INTEGER,
                    response_body TEXT,
                    impact_summary TEXT,
                    cvss_estimate TEXT,
                    bounty_range TEXT,
                    status TEXT DEFAULT 'NEW'
                )
            """)
            
                self.conn.execute("""
                CREATE TABLE IF NOT EXISTS run_metadata (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT,
                    completed_at TEXT,
                    total_tests INTEGER,
                    confirmed_findings INTEGER,
                    probable_findings INTEGER,
                    null_signals INTEGER,
                    ambiguous INTEGER,
                        errors INTEGER
                    )
                """)
            except sqlite3.OperationalError:
                pass

    def _execute_with_retry(self, func, *args):
        import time
        max_retries = 10
        for i in range(max_retries):
            try:
                return func(*args)
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and i < max_retries - 1:
                    time.sleep(0.5)
                else:
                    raise e

    def save_result(self, result: TestResult, run_id: str, endpoint_url: str, http_method: str, response_headers: str, is_fresh_code: bool, is_write_operation: bool) -> None:
        def _save():
            with self.lock:
                with self.conn:
                    self.conn.execute("""
                        INSERT INTO test_results (
                        run_id, timestamp, endpoint_id, endpoint_url, http_method, token_label, http_status, response_body,
                        response_headers, duration_ms, oauth_error_code, oauth_error_type, classification, confidence, finding_class,
                        notes, is_fresh_code, is_write_operation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, result.timestamp, result.endpoint_id, endpoint_url, http_method, result.token_label,
                    result.http_status, result.response_body, response_headers, result.duration_ms, result.oauth_error_code,
                    result.oauth_error_type, result.classification, result.confidence, result.finding_class, result.notes,
                        1 if is_fresh_code else 0, 1 if is_write_operation else 0
                    ))
        self._execute_with_retry(_save)

    def save_finding(self, finding: Finding) -> None:
        def _save():
            with self.lock:
                with self.conn:
                    self.conn.execute("""
                        INSERT INTO findings (
                        run_id, timestamp, finding_id, endpoint_id, token_label, classification, finding_class,
                        http_status, response_body, impact_summary, cvss_estimate, bounty_range, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    finding.run_id, finding.timestamp, finding.finding_id, finding.endpoint_id, finding.token_label,
                    finding.classification, finding.finding_class, finding.http_status, finding.response_body,
                        finding.impact_summary, finding.cvss_estimate, finding.bounty_range, finding.status
                    ))
        self._execute_with_retry(_save)

    def get_findings_by_run(self, run_id: str) -> List[Finding]:
        def _get():
            with self.lock:
                cursor = self.conn.execute("SELECT * FROM findings WHERE run_id = ?", (run_id,))
                return [Finding(**dict(row)) for row in cursor.fetchall()]
        return self._execute_with_retry(_get)

    def get_all_confirmed_findings(self) -> List[Finding]:
        def _get():
            with self.lock:
                cursor = self.conn.execute("SELECT * FROM findings WHERE classification = 'CONFIRMED_FINDING'")
                return [Finding(**dict(row)) for row in cursor.fetchall()]
        return self._execute_with_retry(_get)

    def update_finding_status(self, finding_id: str, status: str) -> None:
        def _update():
            with self.lock:
                with self.conn:
                    self.conn.execute("UPDATE findings SET status = ? WHERE finding_id = ?", (status, finding_id))
        self._execute_with_retry(_update)

    def get_run_summary(self, run_id: str) -> dict:
        def _get():
            with self.lock:
                cursor = self.conn.execute("SELECT * FROM run_metadata WHERE run_id = ?", (run_id,))
                row = cursor.fetchone()
                return dict(row) if row else {}
        return self._execute_with_retry(_get)

    def save_run_metadata(self, metadata: dict) -> None:
        def _save():
            with self.lock:
                with self.conn:
                    # Use REPLACE to allow updating completion times dynamically
                    self.conn.execute("""
                        INSERT OR REPLACE INTO run_metadata (
                        run_id, started_at, completed_at, total_tests, confirmed_findings, probable_findings,
                        null_signals, ambiguous, errors
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metadata['run_id'], metadata.get('started_at'), metadata.get('completed_at'),
                        metadata.get('total_tests', 0), metadata.get('confirmed_findings', 0),
                        metadata.get('probable_findings', 0), metadata.get('null_signals', 0),
                        metadata.get('ambiguous', 0), metadata.get('errors', 0)
                    ))
        self._execute_with_retry(_save)
