"""Retired cloud transcription compatibility guard.

Grounded Studio private mode prohibits AWS Transcribe and public S3 staging.
"""

class TranscribeError(RuntimeError):
    pass


def parse_transcribe_json(payload):
    raise TranscribeError("AWS Transcribe is disabled; use worker.transcribe_local")


def stage_from_store(*args, **kwargs):
    raise TranscribeError("Public/cloud staging is disabled")


def transcribe_media(*args, **kwargs):
    raise TranscribeError("AWS Transcribe is disabled")
