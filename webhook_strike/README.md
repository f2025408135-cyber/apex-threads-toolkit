# WEBHOOK-STRIKE

Standalone tool for testing Threads webhook signature validation bypass on third-party webhook consumer endpoints.

## Installation
```bash
pip install -r requirements.txt
```

## Usage
### Start Reference Receiver
```bash
python main.py serve --port=8080 --app-secret=SECRET --verify-token=TOKEN
```

### Attack Target
```bash
python main.py attack --target-url=http://localhost:8080/webhook --payload=MENTION --target-user-id=123 --attacker-user-id=456
```

### Generate Payload
```bash
python main.py generate-payload --type=MENTION
```
