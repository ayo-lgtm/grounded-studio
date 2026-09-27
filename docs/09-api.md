# 09 — HTTP API sketch

Base: `/api/v1`. Auth: SSO session.

- `GET /workspaces`
- `POST /projects/{id}/briefings` `{ title, skill_id }`
- `POST /briefings/{id}/assets` multipart
- `POST /briefings/{id}/jobs` `{ type }`
- `GET /briefings/{id}/script`
- `POST /briefings/{id}/script/accept`
- `PATCH /briefings/{id}/beats/{id}`
- `GET /briefings/{id}/player-session`
- `POST /briefings/{id}/chat` `{ message }`
- `POST /briefings/{id}/mark-template`
- `POST /templates/{id}/refresh`
- `GET /admin/audit`
- `GET /admin/models`

Chat response includes `citations[]` and `refused`.
QA failure returns `409` with the report. Compiler offline returns `503`.
