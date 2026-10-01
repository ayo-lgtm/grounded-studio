# 16 — Railway test deploy (managed hosting)

Fastest way to run the full stack against real infrastructure: the project
is defined as code in [.railway/railway.ts](../.railway/railway.ts) and
applied with the Railway CLI. Postgres runs as the `pgvector` image
service (the managed Postgres has no pgvector extension), Redis is the
managed plugin, and object storage is a native Railway bucket
(S3-compatible). The api and worker build from the repo-root
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

The worker runs stub transcription here (no AWS keys on Railway);
set `TRANS_PROVIDER=transcribe` + `TRANS_S3_BUCKET` only with real
credentials, or keep the AWS legs on EC2/Coolify per [14](14-aws-claude.md).

## Notes

- Buckets expose `ENDPOINT/BUCKET/REGION/ACCESS_KEY_ID/SECRET_ACCESS_KEY`;
  valid bucket regions are `sjc, iad, ams, sin` (stack compute sits in
  `sfo`, so `sjc` is closest).
- Windows note: the IaC SDK's CLI-version check spawns `railway`, which
  fails on `.ps1` shims; the repo-local patch is documented in the
  SDK file and only affects local `config plan/apply`.
- Cost: this burns Railway usage credit (compute + volumes + bucket).
  Tear down with `railway project delete` (dashboard) when done testing.
