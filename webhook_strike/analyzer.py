import click

from .sender import Sender

class Analyzer:
    @staticmethod
    def analyze(target_url, target_user_id, attacker_user_id, payload_type, captured_sig):
        sender = Sender(target_url)
        sender.run_tests(target_user_id, attacker_user_id, payload_type=payload_type, captured_sig=captured_sig)
