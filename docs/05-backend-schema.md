# 05 — Backend schema

Canonical DDL: [`schema/schema.sql`](../schema/schema.sql).

## Entities

```
Workspace 1---n Project 1---n Briefing
User N---M Workspace (membership + role)
Briefing 1---n SourceAsset
Briefing 1---n ScriptVersion
Briefing 1---n Artifact
Briefing 1---n Chapter
Briefing 1---n Citation
Briefing 1---n EmbeddingChunk
Briefing 1---n ChatMessage
Template = Briefing flagged as template
Job
AuditEvent
```

Citations point at a recording time range, a sheet!cell, or a document block_id.
Chat retrieval is filtered by briefing_id only.
Jobs store pinned model ids so a run is reproducible.
