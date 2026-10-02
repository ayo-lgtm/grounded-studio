# 16 — Railway is not a supported runtime

Grounded Studio must not receive WBRs, internal documents, recordings,
screenshots, transcripts, prompts or artifacts on Railway or any other
third-party managed application host.

* `.railway/railway.ts` declares a project with **zero resources**, so an
  old linked test project converges to no Grounded Studio services or
  storage.
* API and worker refuse to start when they detect a hosted-runtime marker
  (`RAILWAY_ENVIRONMENT`, `RAILWAY_PROJECT_ID`, `VERCEL`, `RENDER`,
  `FLY_APP_NAME`, `HEROKU_APP_ID`, `NETLIFY`), in every deployment mode.
* `*.railway.internal` and `*.railway.app` are on the policy deny list, so a
  leftover Railway private-DNS endpoint is not treated as private.

Deploy on company-controlled infrastructure: `infra/compose.yaml` for a
single internal host (offline profile), Kubernetes with
`infra/k8s/networkpolicy.yaml`, or AWS with `infra/aws/terraform/`
(aws-private profile). See [18](18-deployment-profiles.md).

Anything still stored in a former Railway/Tigris test bucket should be
deleted by its owner; this repository no longer references it.
