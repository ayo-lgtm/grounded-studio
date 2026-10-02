# skill: narration-room-mix
version: 1.0.0
offline: true
area: video
job: Speak accepted beats with local Piper or Kokoro, then mix a quiet room under a ducked bed.

inputs_required:
  - accepted beat text that already passed citation QA
inputs_optional:
  - the source recording as a bed

truth_source: the accepted beat text

story_beats:
  - One local wav per beat. The text is the beat, verbatim.
  - Prefer Piper lessac-medium or a workspace-pinned Kokoro voice. Both run on the worker.
  - Join beats with a short gap. Do not add words in the gap.
  - Loudness target is -16 LUFS integrated, true peak -1.5 dB, then a limiter.
  - A very short local echo is the room. It is not a music bed.
  - Duck the source bed by 12 dB while the voice plays. Restore it after.
  - If the voice clips, the mix fails. There is no cloud voice to swap in.
  - If Piper and Kokoro are both missing, the job fails closed.

visual_grammar:
  - renderer: recording editor when a picture exists, otherwise the deck is unchanged
  - picture is untouched
  - layout stays the parent beat

qa_checks:
  - offline is true
  - mix.json names piper or kokoro
  - duck is -12 dB
  - loudness target is -16 LUFS and true peak -1.5 dB
  - max volume is not hotter than -1 dB
  - no socket to a TTS host

outputs:
  - voiceover.mp3
  - mix.json
  - mixed mp4 when a bed exists

refresh_policy: replace the wav for a dirty beat and remix

crafts:
  - tts-narration
  - duck-mix

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
