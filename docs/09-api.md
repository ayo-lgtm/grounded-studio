# 09 — HTTP API

Base: `/api/v1`. Every route requires auth (`AUTH_MODE=oidc` bearer token or
the SSO proxy's trusted header). `GET /health`, `GET /docs` and `GET /` (the
room UI shell) are public and carry no data.

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/projects` | member | projects in your workspaces |
| POST | `/workspaces/{id}/members` | admin | `{email, role}` |
| POST | `/briefings` | editor | `{title, skill_id, project_id?}`; pins `skill_version` |
| GET | `/briefings` | member | only your workspaces |
| GET | `/briefings/{id}` | viewer | assets with kind, format, sha256, parent package |
| POST | `/briefings/{id}/assets` | editor | multipart; streamed + hashed; type detected from bytes |
| POST | `/briefings/{id}/jobs` | editor | `ingest`, `transcribe`, `compile`, `qa`, `render`, `index` |
| GET | `/jobs/{id}` | viewer | state, error, `model_ids` (providers used) |
| GET | `/briefings/{id}/script` | viewer | latest script, skill/craft provenance, persisted citations |
| POST | `/briefings/{id}/script/accept` | editor | records `accepted_by` |
| GET | `/briefings/{id}/sources` | viewer | normalized cells, blocks, transcript segments |
| GET | `/assets/{id}/content` | viewer | streams the source file |
| GET | `/briefings/{id}/artifacts` | viewer | deck, video, captions, audits |
| GET | `/artifacts/{id}/file` | viewer | streamed, supports `Range` |
| POST | `/briefings/{id}/chat` | viewer | `{question}` → `{text, citations[], refused, provider}` |
| POST | `/help/chat` | member | product help from on-disk docs (not business data) |
| GET | `/skills` | member | on-disk skill catalog |

Errors: `401` unauthenticated, `403` role too low, `404` not found *or not
visible to you*, `413` upload over the cap, `415` unsupported file type,
`503` auth not configured.
