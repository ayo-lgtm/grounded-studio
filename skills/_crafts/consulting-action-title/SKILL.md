# craft: consulting-action-title
version: 1.0.0
offline: true
source: grammar from SlideSpeak consulting packs, sentences from the source only
used_by: leadership-brief, weekly-ops-review, comparison-versus-deck, decision-memo-deck, exec-narrative-deck, kpi-spotlight-deck, risk-and-ask-deck, speaker-notes-deck, stakeholder-variant-deck, wbr-ask-pack, wbr-commentary-lock, wbr-executive, wbr-kpi-spine

job: Write a corridor-readable title, one piece of evidence, and a source footer.

rules:
  - Title is a sentence a leader can read in the corridor, built from cited tokens.
  - Evidence is one to three bullets or one table snapshot.
  - Footer is block_id, sheet!cell, or a recording time span.
  - Bad titles: Overview, Agenda, Key takeaways, Next steps, unless that heading exists in the source.
  - Do not upgrade we are considering into a recommendation.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a title that introduces a claim the evidence does not cite
