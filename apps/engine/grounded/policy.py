"""Deployment profile and egress policy. One source of truth, fail closed.

Grounded Studio runs in exactly one of two explicit deployment modes:

``offline``
    Everything stays on private/local infrastructure. Loopback, RFC1918,
    link-local, cluster service names and explicitly configured internal
    DNS suffixes are the only reachable destinations. Every AWS endpoint,
    including Bedrock, is refused.

``aws-private``
    The same private destinations, plus a small set of company-approved AWS
    services (Amazon Bedrock runtime and S3 by default ceiling), and only for
    the regions, endpoints, Bedrock model IDs and buckets that the deployment
    lists explicitly. Everything not on those lists is refused.

There is no third mode and no escape hatch. An unknown mode, a missing
allowlist, or the retired ``GROUND_ALLOW_PUBLIC_EGRESS`` switch stops the
process instead of degrading to open egress. The policy is a pure function
of the environment so tests can build one per profile.
"""

from __future__ import annotations

import ipaddress
import os
import re
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlparse

OFFLINE = "offline"
AWS_PRIVATE = "aws-private"
MODES = (OFFLINE, AWS_PRIVATE)

#: AWS services a deployment may approve in aws-private mode. Anything else
#: (Transcribe, Polly, public endpoints of other services) can never be
#: approved through configuration; it would need a code change and review.
APPROVABLE_AWS_SERVICES = frozenset({"bedrock-runtime", "s3", "sts", "kms"})

#: Hosts that are never acceptable, whatever the mode or allowlist says.
DENY_SUFFIXES = (
    "storageapi.dev",
    "tigris.dev",
    "r2.cloudflarestorage.com",
    "storage.googleapis.com",
    "googleapis.com",
    "blob.core.windows.net",
    "railway.app",
    "railway.internal",
    "openai.com",
    "anthropic.com",
    "elevenlabs.io",
    "jsdelivr.net",
    "unpkg.com",
    "cdnjs.cloudflare.com",
    "fonts.gstatic.com",
    "huggingface.co",
    "hf.co",
    "scenario.com",
    "runwayml.com",
    "heygen.com",
    "slides.com",
    "sentry.io",
    "segment.io",
    "posthog.com",
    "mixpanel.com",
    "datadoghq.com",
)

#: Third-party managed application hosts. Sensitive runtime never runs there.
HOSTED_RUNTIME_MARKERS = (
    "RAILWAY_ENVIRONMENT",
    "RAILWAY_PROJECT_ID",
    "VERCEL",
    "RENDER",
    "FLY_APP_NAME",
    "HEROKU_APP_ID",
    "NETLIFY",
)

SERVICE_NAMES = frozenset(
    {"localhost", "minio", "postgres", "redis", "pgvector", "ollama", "vllm", "api", "worker", "piper"}
)

_AWS_HOST = re.compile(
    r"^(?:(?!vpce-)(?P<bucket>[a-z0-9][a-z0-9\-]{1,61}[a-z0-9])\.)?"
    r"(?:(?P<vpce>vpce-[a-z0-9\-]+)\.)?"
    r"(?P<service>[a-z0-9\-]+?)(?P<fips>-fips)?"
    r"\.(?P<region>[a-z]{2}(?:-gov)?-[a-z]+-\d)"
    r"(?P<vpce_zone>\.vpce)?\.amazonaws\.com$"
)
_GLOBAL_AWS = re.compile(r"(^|\.)amazonaws\.com$|(^|\.)aws\.amazon\.com$|(^|\.)amazonaws\.com\.cn$")


class EgressError(RuntimeError):
    """A destination, model, bucket or profile violates the egress policy."""


def _split(value: str | None) -> frozenset[str]:
    return frozenset(part.strip().lower() for part in (value or "").split(",") if part.strip())


def _split_exact(value: str | None) -> frozenset[str]:
    return frozenset(part.strip() for part in (value or "").split(",") if part.strip())


def host_of(endpoint: str) -> str:
    text = (endpoint or "").strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"//{text}")
    return (parsed.hostname or "").lower().rstrip(".")


@dataclass(frozen=True)
class AwsHost:
    service: str
    region: str
    vpce: bool
    bucket: str | None


def parse_aws_host(host: str) -> AwsHost | None:
    match = _AWS_HOST.match(host or "")
    if not match:
        return None
    service = match.group("service")
    bucket = match.group("bucket")
    if bucket and service != "s3":
        # e.g. "runtime.sagemaker" style names; only S3 has bucket labels.
        service = f"{bucket}.{service}" if bucket else service
        bucket = None
    vpce = bool(match.group("vpce") or match.group("vpce_zone"))
    if bucket == "bucket" and vpce:
        # S3 interface endpoints use the literal label "bucket." for
        # path-style access; the real bucket is checked separately.
        bucket = None
    return AwsHost(service=service, region=match.group("region"), vpce=vpce, bucket=bucket)


@dataclass(frozen=True)
class Policy:
    mode: str = OFFLINE
    internal_suffixes: tuple[str, ...] = ("internal", "local", "corp", "svc", "cluster.local")
    aws_regions: frozenset[str] = frozenset()
    aws_services: frozenset[str] = frozenset()
    aws_endpoints: frozenset[str] = frozenset()
    aws_private_dns: bool = False
    bedrock_models: frozenset[str] = frozenset()
    buckets: frozenset[str] = frozenset()
    problems: tuple[str, ...] = field(default_factory=tuple)

    # ---- classification -------------------------------------------------
    @property
    def offline(self) -> bool:
        return self.mode == OFFLINE

    @property
    def aws_private(self) -> bool:
        return self.mode == AWS_PRIVATE

    def is_private_host(self, host: str) -> bool:
        name = (host or "").lower().rstrip(".")
        if not name or _denied(name):
            return False
        if name in SERVICE_NAMES or name == "host.docker.internal":
            return True
        try:
            ip = ipaddress.ip_address(name.strip("[]"))
        except ValueError:
            ip = None
        if ip is not None:
            return bool((ip.is_private or ip.is_loopback or ip.is_link_local) and not ip.is_multicast)
        if "." not in name:
            # Docker / Kubernetes service name resolved by the cluster DNS.
            return True
        return any(name == suffix or name.endswith("." + suffix) for suffix in self.internal_suffixes)

    def aws_destination(self, host: str) -> AwsHost | None:
        """Return the parsed AWS host if aws-private mode approves it."""
        if not self.aws_private:
            return None
        parsed = parse_aws_host(host)
        if parsed is None:
            return None
        if parsed.service not in self.aws_services or parsed.service not in APPROVABLE_AWS_SERVICES:
            return None
        if parsed.region not in self.aws_regions:
            return None
        if parsed.bucket and parsed.bucket not in self.buckets:
            return None
        if host in self.aws_endpoints:
            return parsed
        if parsed.vpce:
            # Interface/gateway endpoint DNS names only resolve inside the VPC.
            return parsed
        if self.aws_private_dns:
            # Regional names are acceptable only when the deployment declares
            # that interface endpoints with private DNS serve them in-VPC.
            return parsed
        return None

    def check_url(self, url: str, label: str = "endpoint") -> str:
        host = host_of(url)
        if not host:
            raise EgressError(f"{label} has no hostname")
        if _denied(host):
            raise EgressError(f"{label} host {host} is a denied public service")
        if self.is_private_host(host):
            return url
        if self.aws_destination(host) is not None:
            return url
        if _GLOBAL_AWS.search(host):
            if self.offline:
                raise EgressError(f"{label} host {host} is AWS; offline mode refuses all cloud endpoints")
            raise EgressError(
                f"{label} host {host} is not an approved AWS service/region/endpoint for aws-private mode"
            )
        raise EgressError(f"{label} host {host} is external; egress is denied")

    def check_bedrock(self, model_id: str, region: str) -> None:
        if self.offline:
            raise EgressError("Amazon Bedrock is disabled in offline mode")
        if "bedrock-runtime" not in self.aws_services:
            raise EgressError("bedrock-runtime is not an approved AWS service for this deployment")
        if (region or "").lower() not in self.aws_regions:
            raise EgressError(f"Bedrock region {region or '(missing)'} is not approved")
        if not model_id or model_id not in self.bedrock_models:
            raise EgressError(f"Bedrock model {model_id or '(missing)'} is not on the approved model list")

    def check_object_store(self, endpoint: str, bucket: str | None = None) -> None:
        host = host_of(endpoint)
        if not host:
            raise EgressError("object store endpoint is missing")
        if _denied(host):
            raise EgressError(f"object store host {host} is a denied public service")
        if self.is_private_host(host):
            if self.buckets and bucket and bucket not in self.buckets:
                raise EgressError(f"bucket {bucket} is not on the approved bucket list")
            return
        aws = self.aws_destination(host)
        if aws is not None and aws.service == "s3":
            if not bucket or bucket not in self.buckets:
                raise EgressError(f"S3 bucket {bucket or '(missing)'} is not on the approved bucket list")
            return
        raise EgressError(
            f"object store host {host} is public or unapproved storage for {self.mode} mode"
        )

    def object_store_label(self, endpoint: str, bucket: str | None = None) -> str:
        try:
            self.check_object_store(endpoint, bucket)
        except EgressError:
            return "public-refused"
        return "private" if self.is_private_host(host_of(endpoint)) else "aws-private-s3"

    def describe(self) -> dict[str, object]:
        """Non-sensitive summary for /health and audit."""
        return {
            "mode": self.mode,
            "aws_regions": sorted(self.aws_regions),
            "aws_services": sorted(self.aws_services),
            "bedrock_models": sorted(self.bedrock_models),
            "buckets": len(self.buckets),
        }


def _denied(host: str) -> bool:
    return any(host == suffix or host.endswith("." + suffix) for suffix in DENY_SUFFIXES)


def resolve_mode(env: Mapping[str, str]) -> str:
    raw = (env.get("GROUNDED_DEPLOYMENT_MODE") or env.get("EGRESS_MODE") or OFFLINE).strip().lower()
    if raw not in MODES:
        raise EgressError(
            f"unknown deployment mode {raw!r}; choose one of {', '.join(MODES)}"
        )
    return raw


def from_env(env: Mapping[str, str] | None = None) -> Policy:
    source = os.environ if env is None else env
    escape = (source.get("GROUND_ALLOW_PUBLIC_EGRESS") or "").strip().lower()
    if escape in {"1", "true", "yes", "on"}:
        raise EgressError("GROUND_ALLOW_PUBLIC_EGRESS is retired; public egress cannot be enabled")
    mode = resolve_mode(source)
    suffixes = tuple(
        part.lstrip(".")
        for part in _split(source.get("GROUNDED_INTERNAL_SUFFIXES") or source.get("GROUND_INTERNAL_SUFFIXES"))
    ) or ("internal", "local", "corp", "svc", "cluster.local")
    if mode == OFFLINE:
        return Policy(mode=OFFLINE, internal_suffixes=suffixes)

    regions = _split(source.get("GROUNDED_AWS_REGIONS") or source.get("AWS_REGION"))
    services = _split(source.get("GROUNDED_AWS_SERVICES") or "bedrock-runtime")
    unknown = sorted(services - APPROVABLE_AWS_SERVICES)
    if unknown:
        raise EgressError(f"AWS services {', '.join(unknown)} cannot be approved in aws-private mode")
    models = _split_exact(source.get("GROUNDED_BEDROCK_MODELS"))
    if not regions:
        raise EgressError("aws-private mode requires GROUNDED_AWS_REGIONS")
    if "bedrock-runtime" in services and not models:
        raise EgressError("aws-private mode requires GROUNDED_BEDROCK_MODELS (explicit model allowlist)")
    for model in models:
        if not re.fullmatch(r"(?:(?:us|eu|apac|us-gov|global)\.)?[a-z0-9\-]+\.[A-Za-z0-9.\-:]+", model):
            raise EgressError(f"Bedrock model id {model!r} is malformed")
    return Policy(
        mode=AWS_PRIVATE,
        internal_suffixes=suffixes,
        aws_regions=regions,
        aws_services=services,
        aws_endpoints=frozenset(host_of(url) for url in _split(source.get("GROUNDED_AWS_ENDPOINTS"))),
        aws_private_dns=(source.get("GROUNDED_AWS_PRIVATE_DNS") or "").strip().lower() in {"1", "true", "yes"},
        bedrock_models=models,
        buckets=_split_exact(source.get("GROUNDED_OBJECT_BUCKETS")),
    )


def current() -> Policy:
    return from_env()


def assert_not_hosted_runtime(env: Mapping[str, str] | None = None) -> None:
    source = os.environ if env is None else env
    found = [name for name in HOSTED_RUNTIME_MARKERS if source.get(name)]
    if found:
        raise EgressError("sensitive runtime refuses third-party hosted platforms: " + ", ".join(found))


def assert_runtime(*endpoints: tuple[str, str], env: Mapping[str, str] | None = None) -> Policy:
    """Startup gate for API and worker. Raises before any data is touched."""
    policy = from_env(env)
    assert_not_hosted_runtime(env)
    for label, url in endpoints:
        if not url:
            continue
        if label.upper().startswith("MINIO") or label.upper().startswith("OBJECT"):
            continue  # checked with its bucket by the storage layer
        if label.upper().startswith(("DATABASE", "REDIS")):
            host = host_of(url)
            if not policy.is_private_host(host):
                raise EgressError(f"{label} host {host or '(missing)'} must be private infrastructure")
            continue
        policy.check_url(url, label)
    return policy
