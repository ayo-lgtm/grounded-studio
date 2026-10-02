# 16 — Railway test deploy (managed hosting)

Fastest way to run the full stack against real infrastructure: the project
is defined as code in [.railway/railway.ts](../.railway/railway.ts) and
applied with the Railway CLI. Postgres runs as the `pgvector` image
service (the managed Postgres has no pgvector extension), Redis is the
managed plugin, and object storage is an in-project MinIO service with
the `miniodata` volume. The api and worker build from the repo-root
[Dockerfile](../Dockerfile).

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
4. Confirm `GET /health` is `{"ok":true,"egress":"offline","chat":"retrieval","narration":"local","transcription":"local","object_store":"private"}`.
   `object_store: public-refused` with `egress: blocked` means `MINIO_ENDPOINT` is still a public host. Point it at `http://<minio private domain>:9000`.
5. Unset leftover generative variables if they are still on the services: `CLAUDE_MODEL_ID`, `AWS_REGION`, `TRANS_PROVIDER=transcribe`, `NARRATION_PROVIDER=polly`. The process ignores them for chat, TTS, and ASR, and a public object store in the default offline mode fails closed.
6. The old `blobs` Tigris bucket is no longer in the spec. Apply may drop it. Copy anything you still need into MinIO first. The test bucket should not hold customer data.
7. Do not set `EGRESS_MODE=aws-in-region` to keep Tigris. That mode is a legacy object-store opt-in. Chat and media stay local either way.

`/docs` is a local HTML page. It does not load a CDN.

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

- Offline object storage is the `minio` service. Attach volume `miniodata` at `/data`. `MINIO_ENDPOINT` is `http://${{minio.RAILWAY_PRIVATE_DOMAIN}}:9000`. Do not point the offline profile at Tigris (`*.storageapi.dev`).
- Windows note: the IaC SDK's CLI-version check spawns `railway`, which
  fails on `.ps1` shims; the repo-local patch is documented in the
  SDK file and only affects local `config plan/apply`.
- Cost: this burns Railway usage credit (compute + volumes).
  Tear down with `railway project delete` (dashboard) when done testing.
