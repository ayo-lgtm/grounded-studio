"""Private object storage (internal MinIO, or approved private S3).

The endpoint *and bucket* are checked against the deployment policy before
any client is built - including an injected test client - so a public
store is refused even if a bug hands one in.

* MinIO on private infrastructure: access keys from the environment.
* Approved S3 (aws-private mode only, VPC endpoint): IAM role credentials
  from the default chain. Static access keys are refused. Objects are
  written with SSE-KMS when ``GROUNDED_OBJECT_KMS_KEY`` is set (required
  for S3 in aws-private mode).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, BinaryIO

from .policy import EgressError, from_env, host_of, parse_aws_host


class StoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoreConfig:
    endpoint: str
    bucket: str
    access_key: str = ""
    secret_key: str = ""
    region: str = "us-east-1"

    @property
    def is_aws(self) -> bool:
        return parse_aws_host(host_of(self.endpoint)) is not None


def check(config: StoreConfig) -> None:
    try:
        from_env().check_object_store(config.endpoint, config.bucket)
    except EgressError as exc:
        raise StoreError(str(exc)) from exc
    if config.is_aws:
        if config.access_key or config.secret_key:
            raise StoreError("S3 must use IAM role credentials; static access keys are refused")
        if not (os.environ.get("GROUNDED_OBJECT_KMS_KEY") or "").strip():
            raise StoreError("S3 in aws-private mode requires GROUNDED_OBJECT_KMS_KEY (SSE-KMS)")


def client(config: StoreConfig, injected: Any = None) -> Any:
    check(config)
    if injected is not None:
        return injected
    try:
        import boto3
        from botocore.client import Config
    except ImportError as exc:
        raise StoreError("boto3 is not installed") from exc
    kwargs: dict[str, Any] = {
        "endpoint_url": config.endpoint,
        "region_name": config.region,
        "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    }
    if not config.is_aws:
        kwargs["aws_access_key_id"] = config.access_key or None
        kwargs["aws_secret_access_key"] = config.secret_key or None
    try:
        return boto3.session.Session().client("s3", **kwargs)
    except Exception as exc:  # noqa: BLE001
        raise StoreError(f"cannot create store client ({type(exc).__name__})") from None


def write_args(content_type: str) -> dict[str, str]:
    args = {"ContentType": content_type}
    key = (os.environ.get("GROUNDED_OBJECT_KMS_KEY") or "").strip()
    if key:
        args["ServerSideEncryption"] = "aws:kms"
        args["SSEKMSKeyId"] = key
    return args


def put_stream(config: StoreConfig, key: str, stream: BinaryIO, content_type: str, injected: Any = None) -> None:
    """Multipart-stream a file-like object; never buffers the whole body."""
    s3 = client(config, injected)
    try:
        s3.upload_fileobj(stream, config.bucket, key, ExtraArgs=write_args(content_type))
    except StoreError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise StoreError(f"store upload failed ({type(exc).__name__})") from None


def get_stream(config: StoreConfig, key: str, injected: Any = None):
    s3 = client(config, injected)
    try:
        return s3.get_object(Bucket=config.bucket, Key=key)["Body"]
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "response", {}).get("Error", {}).get("Code") if hasattr(exc, "response") else None
        if code in {"NoSuchKey", "NotFound", "404"}:
            raise FileNotFoundError(key) from None
        raise StoreError(f"store read failed ({type(exc).__name__})") from None
