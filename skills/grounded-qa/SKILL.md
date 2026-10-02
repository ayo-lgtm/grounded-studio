# skill: grounded-qa
version: 1.0.0
offline: true
job: Answer questions using only this briefing's indexed sources and accepted script.

inputs_required:
  - briefing index

behavior:
  - retrieve top-k chunks filtered by briefing_id
  - answer only if chunks are sufficient
  - attach citation spans
  - otherwise refuse

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render; no public internet egress
  - world knowledge
  - web search
  - using other briefings in the workspace unless the user attached them

qa_checks:
  - evaluation questions that must refuse
  - answers that mention a feature absent from chunks fail eval

outputs:
  - chat message + citation_ids
