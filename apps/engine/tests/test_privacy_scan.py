"""Static privacy regression scan over the runtime (apps/, not tests).

Fails if runtime code reintroduces a public AI/transcription/TTS endpoint,
cloud staging, analytics/telemetry, a public CDN or remote font, a runtime
model download, or a generic HTTP client outside the guarded module.
Each exemption names the one file allowed to hold the construct and why.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"

RUNTIME = [
    path
    for path in sorted(APPS.rglob("*"))
    if path.is_file()
    and path.suffix in {".py", ".html", ".js", ".css"}
    and "tests" not in path.parts
    and "__pycache__" not in path.parts
]

FORBIDDEN = {
    "public AI endpoint": r"api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis|api\.cohere|api\.mistral\.ai|api\.groq\.com",
    "public TTS/ASR": r"elevenlabs\.io|api\.elevenlabs|deepgram\.com|assemblyai\.com|speech\.googleapis",
    "AWS Transcribe": r"start_transcription_job|get_transcription_job|TranscriptFileUri|client\(\s*[\"']transcribe",
    "AWS Polly": r"synthesize_speech|client\(\s*[\"']polly",
    "cloud staging store": r"storageapi\.dev|tigris\.dev|r2\.cloudflarestorage|blob\.core\.windows\.net|storage\.googleapis",
    "public CDN / remote font": r"cdn\.jsdelivr|unpkg\.com|cdnjs\.cloudflare|fonts\.googleapis|fonts\.gstatic|googletagmanager",
    "analytics / telemetry SDK": r"\bimport\s+sentry_sdk|\bposthog\b|\bmixpanel\b|\bsegment\.io\b|datadog|opentelemetry\.exporter|newrelic",
    "runtime model download": r"hf_hub_download|snapshot_download|from_pretrained\(|huggingface\.co|whisper\.load_model",
    "generic SDK HTTP": r"\bimport\s+requests\b|\bfrom\s+requests\b|\bimport\s+httpx\b|\bfrom\s+httpx\b|aiohttp",
    "SaaS video generation": r"runwayml|heygen|synthesia|veo\.googleapis|scenario\.com",
}

# construct -> the only files allowed to contain it, with the reason.
ALLOWED = {
    r"urlopen|urllib\.request|http\.client": {"apps/engine/grounded/net.py"},  # policy-checked, no proxy, no redirects
    r"bedrock-runtime": {"apps/engine/grounded/providers/bedrock.py", "apps/engine/grounded/policy.py", "apps/engine/grounded/providers/registry.py"},
    r"amazonaws\.com": {"apps/engine/grounded/policy.py"},
    r"boto3\.(?:client|session|resource)|\.client\(\s*[\"']s3": {"apps/engine/grounded/objectstore.py", "apps/engine/grounded/providers/bedrock.py"},
    r"\bimport boto3\b": {"apps/engine/grounded/objectstore.py", "apps/engine/grounded/providers/bedrock.py"},
}


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


class PrivacyScanTest(unittest.TestCase):
    def test_runtime_has_files(self):
        self.assertGreater(len(RUNTIME), 30)

    def test_no_forbidden_constructs(self):
        offenders = []
        for path in RUNTIME:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in FORBIDDEN.items():
                for match in re.finditer(pattern, text, re.I):
                    if _rel(path) == "apps/engine/grounded/policy.py" and label in {
                        "public AI endpoint", "public TTS/ASR", "cloud staging store", "public CDN / remote font",
                        "analytics / telemetry SDK", "runtime model download", "SaaS video generation",
                    }:
                        continue  # the deny list itself names these hosts
                    offenders.append(f"{_rel(path)}: {label}: {match.group(0)!r}")
        self.assertEqual(offenders, [])

    def test_restricted_constructs_stay_in_their_files(self):
        offenders = []
        for pattern, allowed in ALLOWED.items():
            for path in RUNTIME:
                if _rel(path) in allowed:
                    continue
                if re.search(pattern, path.read_text(encoding="utf-8", errors="ignore")):
                    offenders.append(f"{_rel(path)} uses {pattern}")
        self.assertEqual(offenders, [])

    def test_no_escape_hatch_reads(self):
        offenders = []
        for path in RUNTIME:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if _rel(path) == "apps/engine/grounded/policy.py":
                continue
            if re.search(r"ALLOW_PUBLIC|ALLOW_EGRESS|EGRESS_BYPASS|DISABLE_GUARD", text):
                offenders.append(_rel(path))
        self.assertEqual(offenders, [])

    def test_html_loads_nothing_remote(self):
        for path in RUNTIME:
            if path.suffix != ".html":
                continue
            text = path.read_text(encoding="utf-8").lower()
            self.assertIsNone(re.search(r"(src|href)\s*=\s*[\"']https?://", text), _rel(path))
            self.assertNotIn("@import url(http", text, _rel(path))

    def test_container_images_do_not_default_to_cloud(self):
        for name in ("Dockerfile", "apps/api/Dockerfile", "apps/worker/Dockerfile"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("DEV_BYPASS_AUTH=true", text, name)
            self.assertNotIn("aws-private", text, name)
            self.assertIn("HF_HUB_OFFLINE=1", text if "worker" in name or name == "Dockerfile" else "HF_HUB_OFFLINE=1")

    def test_compose_and_examples_fail_closed(self):
        for name in (".env.example", "infra/compose.yaml", "docker-compose.coolify.yml"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"DEV_BYPASS_AUTH\s*[:=]\s*[\"']?true", name)
            self.assertNotIn("GROUND_ALLOW_PUBLIC_EGRESS", text, name)
            self.assertNotRegex(text, r"(OPENAI|ANTHROPIC|ELEVENLABS)_API_KEY", name)


if __name__ == "__main__":
    unittest.main()
