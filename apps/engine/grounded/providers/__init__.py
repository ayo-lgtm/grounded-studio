"""Provider abstraction for model-backed workloads.

Every pipeline (chat phrasing, director polish, summary drafting,
embeddings, transcription, narration, screenshot text) talks to a provider
interface from :mod:`.base`. A deployment selects one implementation per
workload explicitly (:mod:`.registry`). There is no silent fallback: if the
selected provider is unavailable the workload fails closed or keeps the
deterministic, verbatim result; it never tries another provider.
"""
