from .settings import settings


def _client(client=None):
    if client is not None:
        return client
    try:
        import boto3
        from botocore.client import Config
    except ImportError as exc:
        raise RuntimeError("boto3 is not installed") from exc
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name=settings.minio_region,
    )


def _error_code(exc):
    try:
        return exc.response.get("Error", {}).get("Code")
    except AttributeError:
        return None


def ensure_bucket(client=None) -> None:
    s3 = _client(client)
    try:
        existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    except Exception as exc:
        if _error_code(exc) in {"AccessDenied", "Forbidden"}:
            # Scoped credentials (e.g. a provisioned bucket): listing is
            # forbidden but the bucket exists, so there is nothing to do.
            return
        raise
    if settings.minio_bucket not in existing:
        s3.create_bucket(Bucket=settings.minio_bucket)


def put_bytes(key: str, data: bytes, content_type: str, client=None) -> None:
    ensure_bucket(client)
    _client(client).put_object(
        Bucket=settings.minio_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def signed_url(key: str, expires: int = 300, client=None) -> str:
    return _client(client).generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": key},
        ExpiresIn=expires,
    )


def read_bytes(key: str, client=None) -> bytes:
    """Read one object. Same-origin playback cannot use a signed URL that expires mid-film."""
    try:
        response = _client(client).get_object(Bucket=settings.minio_bucket, Key=key)
    except Exception as exc:
        if _error_code(exc) in {"NoSuchKey", "NotFound", "404"}:
            raise FileNotFoundError(key) from exc
        raise
    body = response["Body"]
    try:
        return body.read()
    finally:
        close = getattr(body, "close", None)
        if close:
            close()
