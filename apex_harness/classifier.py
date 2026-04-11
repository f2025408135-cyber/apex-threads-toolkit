import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import datetime

@dataclass
class TestResult:
    endpoint_id: str
    token_label: str
    http_status: int
    response_body: str
    duration_ms: int
    oauth_error_code: Optional[int] = None
    oauth_error_type: Optional[str] = None
    oauth_error_message: Optional[str] = None
    classification: str = "AMBIGUOUS"
    confidence: str = "LOW"
    finding_class: Optional[str] = None
    notes: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.utcnow().isoformat() + "Z"

def classify_response(result: TestResult, endpoint, is_bola_test: bool = False) -> TestResult:
    """Classify the HTTP response based on rules defined in Section 3."""
    
    parsed_body = {}
    try:
        parsed_body = json.loads(result.response_body)
    except json.JSONDecodeError:
        pass

    # Extract oauth error if present
    if isinstance(parsed_body, dict) and "error" in parsed_body:
        error = parsed_body["error"]
        if isinstance(error, dict):
            result.oauth_error_code = error.get("code")
            result.oauth_error_type = error.get("type")
            result.oauth_error_message = error.get("message")

    # 1. CONFIRMED_FINDING
    if result.http_status == 200:
        # Condition A: HTTP 200 AND token_label is NOT the expected token type
        # Assuming "THREADS_USER" expected means "THREADS_FULL" is the standard token.
        if endpoint.expected_auth == "THREADS_USER" and result.token_label not in ["THREADS_FULL", "THREADS_B"]:
            # Could be FB_TOKEN, APP_TOKEN, UNAUTHENTICATED
            result.classification = "CONFIRMED_FINDING"
            result.confidence = "HIGH"
            result.finding_class = "Token Confusion"
            
        # Condition B: HTTP 200 AND endpoint is a BOLA write endpoint
        elif endpoint.is_write and is_bola_test and result.token_label == "THREADS_FULL":
            result.classification = "CONFIRMED_FINDING"
            result.confidence = "HIGH"
            result.finding_class = "BOLA Write Access"

        # Condition C: HTTP 200 AND fields in response include location/coordinates
        # AND endpoint is user_b_* AND token is not USER_B's token
        elif is_bola_test and result.token_label != "THREADS_B":
            # Check fields
            response_fields = parsed_body.keys() if isinstance(parsed_body, dict) else []
            if "location" in response_fields or "coordinates" in response_fields:
                result.classification = "CONFIRMED_FINDING"
                result.confidence = "HIGH"
                result.finding_class = "Geolocation Disclosure via BOLA"

    # 2. PROBABLE_FINDING
    if result.classification != "CONFIRMED_FINDING" and result.http_status == 200:
        # Condition: HTTP 200 AND token is NARROW (threads_basic) AND endpoint requires a broader scope
        if result.token_label == "THREADS_NARROW" and endpoint.required_scope != "threads_basic":
            result.classification = "PROBABLE_FINDING"
            result.confidence = "MEDIUM"
            result.finding_class = "Scope Enforcement Failure"

        # Condition: Response contains unexpected fields not in the documented field list
        elif isinstance(parsed_body, dict):
            doc_fields = endpoint.fields.split(",") if endpoint.fields and endpoint.fields != "*" else []
            response_fields = list(parsed_body.keys())
            
            # Simple check if any returned field isn't in doc_fields (ignoring standard pagination or graph objects for now, just root keys)
            unexpected_fields = [f for f in response_fields if f not in doc_fields and doc_fields]
            if unexpected_fields and endpoint.fields != "*":
                result.classification = "PROBABLE_FINDING"
                result.confidence = "MEDIUM"
                result.finding_class = "Undocumented Field Disclosure"
                result.notes = f"Unexpected fields: {','.join(unexpected_fields)}"

    # 3. NULL_SIGNAL
    if result.classification not in ["CONFIRMED_FINDING", "PROBABLE_FINDING"]:
        if result.http_status == 403 and result.oauth_error_code in [10, 200, 190, 104]:
            result.classification = "NULL_SIGNAL"
            result.confidence = "HIGH"

    # 4. AMBIGUOUS
    if result.classification not in ["CONFIRMED_FINDING", "PROBABLE_FINDING", "NULL_SIGNAL"]:
        if result.http_status != 200 and result.http_status != 403:
            result.classification = "AMBIGUOUS"
            result.confidence = "LOW"
            
    # 5. ERROR handled mostly at the request layer before calling this, but we can capture 0
    if result.http_status == 0:
        result.classification = "ERROR"

    return result
