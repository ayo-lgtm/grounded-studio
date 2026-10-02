# 16 — Railway test deploy (managed hosting)

Fastest way to run the full stack against real infrastructure: the project
is defined as code in [.railway/railway.ts](../.railway/railway.ts) and
applied with the Railway CLI. Postgres runs as the `pgvector` image
service (the managed Postgres has no pgvector extension), Redis is the
managed plugin, and object storage is an in-project MinIO service
(`elestio/minio:latest`) with the `miniodata` volume mounted at `/data`.
The api and worker build from the repo-root [Dockerfile](../Dockerfile).
When the Railway GitHub app cannot see this private repo, point both
services at the GHCR image from
[.github/workflows/publish-offline-image.yml](../.github/workflows/publish-offline-image.yml).

## One-time setup

1. Install the CLI (`npm install -g @railway/cli`, 5.63+) and
   `railway login` (browser or `railway login --browserless`).
2. `railway init --name grounded-studio-test` from the repo root
   (creates and links the project).
3. Secrets first — they must exist before the first deploy, otherwise
   postgres/minio boot loops:
   `railway variable set POSTGRES_PASSWORD=<random> --service pgvector`,
   then `railway config apply --yes`.
4. Upload code: `railway up --service api`, `railway up --service worker`.
5. Public URL: `railway domain --service api --port 8000`.
6. First boot only: point the api start command at the bootstrapper
   (`start: "python -m app.bootstrap"` in `.railway/railway.ts`),
   `railway config apply --yes`, confirm `bootstrap: applied N
   statements` in the deploy logs, then restore the uvicorn start and
   apply again.

## Operate

- Status: `railway service status --service <name>`.
- Logs: `railway logs --service <name> -d --lines 50` (deploy/runtime).
- Redeploy: `railway service redeploy --service <name> --yes`.
- Variables: `railway variable set KEY=VALUE --service <name>`.
- Never commit secrets: `POSTGRES_PASSWORD` uses `preserve()` in
  `.railway/railway.ts` so CLI-set values survive applies.

## Offline cutover

The October 2026 audit found the public API healthy but not offline: `/health` reported `aws-in-region` / `bedrock`, `MINIO_*` pointed at Tigris (`*.storageapi.dev`), and `/docs` loaded a public CDN. This config removes that path.

After this branch merges, from a machine that is already logged into the Railway project `grounded-studio-test`:

1. Set secrets if they are not already set. Do not commit them.
   `railway variable set POSTGRES_PASSWORD=<random> --service pgvector`
   `railway variable set MINIO_ROOT_PASSWORD=<random> --service minio`
2. Apply the spec so MinIO and the `miniodata` volume exist and api/worker stop referencing the Tigris bucket:
   `railway config apply --yes`
3. Redeploy both images so they pick up the baked Piper and faster-whisper weights:
   `railway up --service api` and `railway up --service worker`
   or `railway service redeploy --service api --yes` and the same for worker, after the git deploy finishes.
   If the Railway GitHub app cannot clone this private repo, skip `railway up` and use the GHCR image below.
4. Confirm `GET /health` is `{"ok":true,"egress":"offline","chat":"retrieval","narration":"local","transcription":"local","object_store":"private"}`.
   `object_store: public-refused` with `egress: blocked` means `MINIO_ENDPOINT` is still a public host. Point it at `http://<minio private domain>:9000`.
5. Unset leftover generative variables if they are still on the services: `CLAUDE_MODEL_ID`, `AWS_REGION`, `TRANS_PROVIDER=transcribe`, `NARRATION_PROVIDER=polly`. The process ignores them for chat, TTS, and ASR, and a public object store in the default offline mode fails closed.
6. The old `blobs` Tigris bucket is no longer in the spec. Apply may drop it. Copy anything you still need into MinIO first. The test bucket should not hold customer data.
7. Do not set `EGRESS_MODE=aws-in-region` to keep Tigris. That mode is a legacy object-store opt-in. Chat and media stay local either way.

`/docs` is a local HTML page. It does not load a CDN.

## MinIO image

Docker Hub returns 404 for `minio/minio` (including the old `RELEASE.2025-04-22T22-12-26Z` pin) and for `bitnami/minio:latest`. Official Quay MinIO pulls are disabled. The image that boots on this Railway project is `elestio/minio:latest`.

The spec in `.railway/railway.ts` matches the working service:

- Image: `elestio/minio:latest`. The image has no `USER`, so the process is root.
- Start: `minio server /data --address :9000 --console-address :9001`.
- Volume: `miniodata` mounted at `/data`. Use a fresh volume. The image declares `VOLUME /data` and can initialize a new root-owned Railway mount.
- Credentials stay the `MINIO_ROOT_*` pair: `MINIO_ROOT_USER=grounded` and `MINIO_ROOT_PASSWORD` via `preserve()` (set with the CLI, never committed). api and worker read that password as `MINIO_SECRET_KEY`.

Bitnami cannot be the volume-backed store on Railway. `bitnami/minio` and `bitnamilegacy/minio` run as UID 1001. A Railway volume mount is root-owned, and UID 1001 cannot create `/data`. The container crash-loops. `bitnamilegacy/minio:latest` only reaches a healthy process when the volume is left off, which drops persistence. Do not "fix" MinIO by removing `miniodata`.

`elestio/minio` is also the pin in [docker-compose.coolify.yml](../docker-compose.coolify.yml) and [infra/compose.yaml](../infra/compose.yaml). Compose passes the same server arguments. The image entrypoint is `/usr/bin/docker-entrypoint.sh`; if the first argument is already `minio`, it execs that command as-is.

If an earlier Bitnami attempt never became healthy, `miniodata` is empty and safe to replace before apply. Copy objects out before you delete a volume that already has data.

## GHCR image when Railway cannot see the repo

When the Railway GitHub app cannot clone this private repository, a git-connected build of `api` and `worker` does not start. Publish the offline bake to GHCR and point both services at that image. Leave `EGRESS_MODE` as `offline`. The Dockerfile bakes that value, and the spec sets it again at runtime.

Workflow: [.github/workflows/publish-offline-image.yml](../.github/workflows/publish-offline-image.yml).

It runs on `workflow_dispatch`, and on a push to `main` that touches `Dockerfile`, `apps/**`, or `infra/**`. It checks out that ref, builds the repo-root `Dockerfile` for `linux/amd64` (Piper in the bake is `piper_linux_x86_64`), and pushes:

- `ghcr.io/ayo-lgtm/grounded-studio:offline`
- `ghcr.io/ayo-lgtm/grounded-studio:main`

The repo is private, so the package is private. The workflow grants `packages: write` to `GITHUB_TOKEN` and logs in to `ghcr.io` with that token. It does not use a personal access token to push. Dispatch the workflow from `main` when you want `:main` to match `main`. Schema, skills, docs, and `README.md` are copied into the image but do not themselves trigger the push filter; run the workflow by hand after those change.

Point Railway at the image (Pro plan; private registry credentials are a Pro feature):

1. Create a GitHub personal access token (classic) with `read:packages` only. Paste the token alone into Railway. Do not prefix it with a username, and do not reuse the CI write token.
2. For **both** `api` and `worker` on project `grounded-studio-test`: Settings → Source → Docker Image. Image path: `ghcr.io/ayo-lgtm/grounded-studio:offline` (`:main` is the same bake). Under Registry Credentials, put the token in the GitHub Access Token field. Railway fills in the GHCR username.
3. Keep the start commands already in `.railway/railway.ts`. api: `sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'`. worker: `python -m worker.main`. Health check for api stays `/health`.
4. Redeploy. A new GHCR push does not redeploy by itself. `railway service redeploy --service api --yes` and the same for `worker`.

`railway up` from a machine that already has the clone still works when you do not want the registry path. Leave MinIO on `elestio/minio:latest`. Only api and worker move to GHCR.

## End-to-end check

With `API=https://<your-api-domain>`:

```bash
curl $API/health
curl -s -X POST $API/api/v1/briefings \
  -H 'content-type: application/json' \
  -d '{"title":"Settings walkthrough","skill_id":"product-walkthrough"}'
# upload a recording, then enqueue transcribe -> compile -> render jobs,
# fetch the script, list artifacts + download the video, accept the script,
# and ask chat a quoted + a refused question
```

The worker transcribes with faster-whisper and narrates with Piper. Both weights are baked into the image. `TRANS_PROVIDER=local` and `NARRATION_PROVIDER=local`. Public providers fail the job. See [17](17-offline-egress.md).

## Notes

- Offline object storage is the `minio` service (`elestio/minio:latest`), volume `miniodata` at `/data`, start `minio server /data --address :9000 --console-address :9001`. `MINIO_ENDPOINT` is `http://${{minio.RAILWAY_PRIVATE_DOMAIN}}:9000`. Do not point the offline profile at Tigris (`*.storageapi.dev`). Do not switch this service to Bitnami to "get a newer MinIO"; UID 1001 cannot write the Railway volume.
- Windows note: the IaC SDK's CLI-version check spawns `railway`, which
  fails on `.ps1` shims; the repo-local patch is documented in the
  SDK file and only affects local `config plan/apply`.
- Cost: this burns Railway usage credit (compute + volumes).
  Tear down with `railway project delete` (dashboard) when done testing.
