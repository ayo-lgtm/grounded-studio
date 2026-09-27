import json
import uuid

import redis

from .settings import settings

QUEUE_NAME = "grounded.jobs"


def enqueue(job_id: str, job_type: str, briefing_id: str) -> None:
    r = redis.from_url(settings.redis_url)
    r.lpush(
        QUEUE_NAME,
        json.dumps({"job_id": job_id, "type": job_type, "briefing_id": briefing_id}),
    )


def new_id() -> str:
    return str(uuid.uuid4())
