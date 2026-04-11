import datetime

def get_payload(payload_type: str, target_user_id: str, attacker_user_id: str, timestamp: int = None) -> dict:
    if not timestamp:
        timestamp = int(datetime.datetime.utcnow().timestamp())
        
    if payload_type == "MENTION":
        return {
            "object": "threads",
            "entry": [{
                "id": target_user_id,
                "time": timestamp,
                "changes": [{
                    "value": {
                        "from": {"id": attacker_user_id, "username": "attacker"},
                        "media_id": "12345",
                        "comment_id": "67890",
                        "timestamp": str(timestamp),
                        "text": "@target this is injected"
                    },
                    "field": "mentioned"
                }]
            }]
        }
    elif payload_type == "REPLY":
        return {
            "object": "threads",
            "entry": [{
                "id": target_user_id,
                "time": timestamp,
                "changes": [{
                    "value": {
                        "id": "reply_123",
                        "text": "injected text",
                        "timestamp": str(timestamp),
                        "from": {"id": attacker_user_id}
                    },
                    "field": "replies"
                }]
            }]
        }
    elif payload_type == "FOLLOW":
        return {
            "object": "threads",
            "entry": [{
                "id": target_user_id,
                "time": timestamp,
                "changes": [{
                    "value": {
                        "follower_id": attacker_user_id,
                        "timestamp": str(timestamp)
                    },
                    "field": "follows"
                }]
            }]
        }
    elif payload_type == "ACCOUNT_DELETE":
        return {
            "object": "threads",
            "entry": [{
                "id": target_user_id,
                "time": timestamp,
                "changes": [{
                    "value": {
                        "user_id": target_user_id,
                        "timestamp": str(timestamp)
                    },
                    "field": "account_deleted"
                }]
            }]
        }
    else:
        raise ValueError(f"Unknown payload type: {payload_type}")
