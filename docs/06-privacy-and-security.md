# 06 — Privacy and security (in-house)

This product only exists if security will let employees use it.

## Egress

Two explicit profiles: `offline` (default; nothing leaves private
infrastructure) and `aws-private` (only allowlisted Amazon Bedrock/Nova
models, regions, VPC endpoints and buckets). Enforcement is layered:
policy, startup gate, client checks, a process-wide socket guard, and
infrastructure (internal Docker networks, Kubernetes default-deny, AWS VPC
with no IGW/NAT and endpoint policies). See [18](18-deployment-profiles.md)
and [17](17-offline-egress.md). There is no switch that enables public
egress.

## Identity and ACL

`AUTH_MODE=oidc` (JWT verified against the company IdP's JWKS, issuer,
audience, expiry) or `AUTH_MODE=trusted-header` (company SSO reverse proxy
with a shared proxy secret). Unset auth means every data endpoint returns
503. `DEV_BYPASS_AUTH=true` is refused unless `GROUNDED_ENV=development`.
Workspace RBAC (viewer < editor < owner < admin) protects briefings,
uploads, sources, scripts, artifacts and chat; briefings outside a user's
workspaces return 404 so their existence does not leak. Object storage is
never exposed to browsers: the API streams files after authorization;
presigned URLs are not issued.

## Encryption and secrets

TLS on the company mesh / ALB. MinIO with server-side encryption, or S3 with
SSE-KMS (`GROUNDED_OBJECT_KMS_KEY`; the bucket policy denies unencrypted,
non-TLS and non-VPC-endpoint access). AWS credentials are role-based only;
static access keys are refused. No third-party AI keys exist in config.

## Audit and logging

`audit_events` records who created briefings, uploaded assets, started jobs,
accepted scripts, read assets and changed membership, without content.
Application logs carry ids, counts and error classes only
(`grounded.logsafe`); SDK wire logging is suppressed.

## Uploads

Streamed to private storage in bounded parts while hashed (SHA-256), capped
by `GROUNDED_MAX_UPLOAD_BYTES`; a refused upload is deleted. Type is detected
from bytes, not the client's label. Zip packages are expanded one level with
member-count, size and compression-ratio limits. XLSX is read as values and
formulas (macros never execute); legacy binary Office files are refused.

## Malware

Run the company scanner on the storage bucket or at the ingress proxy.

## Training

There is no fine-tune job type. Uploads are never used to train a model
without a separate Legal + Security change.

## Residual risk

* Screenshot text from OCR or Nova is machine-read; blocks carry their
  `extractor` so reviewers can see which citations rest on OCR.
* Humans still accept scripts. Grounding gates block uncited numbers,
  causes, risks and recommendations, but cannot judge whether a correctly
  quoted source is itself wrong.
* Privileged admins of the hosts can read storage; that is existing PAM.

## What we tell InfoSec

Grounded Studio is a self-hosted compiler. Media and documents stay on
company object storage. In the offline profile, speech-to-text, language
models, embeddings and TTS run on company hardware and no public generative
API is called. In the aws-private profile, only allowlisted Bedrock/Nova
models are reachable, through VPC endpoints, with role credentials and
KMS-encrypted storage. Access is SSO + workspace ACL. Every published
sentence is citation-checked and human-accepted.
