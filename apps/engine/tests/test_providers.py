"""Provider selection, Bedrock/Nova under policy, and no automatic fallback."""

import io
import json
import os
import unittest
from unittest import mock

from grounded.providers import registry
from grounded.providers.base import Attachment, ProviderError
from grounded.providers.bedrock import BedrockEmbeddings, BedrockImageText, BedrockInference

AWS_ENV = {
    "GROUNDED_DEPLOYMENT_MODE": "aws-private",
    "GROUNDED_AWS_REGIONS": "us-east-1",
    "AWS_REGION": "us-east-1",
    "GROUNDED_AWS_SERVICES": "bedrock-runtime",
    "GROUNDED_BEDROCK_MODELS": "amazon.nova-pro-v1:0,amazon.nova-lite-v1:0,amazon.titan-embed-text-v2:0",
    "GROUNDED_BEDROCK_TEXT_MODEL": "amazon.nova-pro-v1:0",
    "GROUNDED_BEDROCK_MULTIMODAL_MODEL": "amazon.nova-lite-v1:0",
    "GROUNDED_BEDROCK_EMBEDDING_MODEL": "amazon.titan-embed-text-v2:0",
    "GROUNDED_BEDROCK_ENDPOINT": "https://vpce-0abc-1.bedrock-runtime.us-east-1.vpce.amazonaws.com",
}


class FakeBedrock:
    def __init__(self, text="{}", embedding=None):
        self.text = text
        self.embedding = embedding
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [{"text": self.text}]}}, "usage": {"inputTokens": 3, "outputTokens": 2}}

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        return {"body": io.BytesIO(json.dumps({"embedding": self.embedding}).encode())}


class env:
    """Swap os.environ for the duration of a test."""

    def __init__(self, values):
        self.values = values

    def __enter__(self):
        self.patch = mock.patch.dict(os.environ, self.values, clear=True)
        self.patch.start()

    def __exit__(self, *exc):
        self.patch.stop()


class SelectionTest(unittest.TestCase):
    def test_offline_defaults_are_local_and_retrieval_only(self):
        chosen = registry.selection({})
        self.assertEqual(chosen.mode, "offline")
        self.assertEqual(chosen.inference, "none")
        self.assertEqual(chosen.transcription, "local")
        self.assertEqual(chosen.tts, "local")
        self.assertEqual(chosen.embedding, "local-hash")
        self.assertFalse(chosen.uses_cloud())

    def test_offline_refuses_bedrock_for_every_workload(self):
        for key in ("GROUNDED_INFERENCE_PROVIDER", "GROUNDED_EMBEDDING_PROVIDER", "GROUNDED_IMAGE_TEXT_PROVIDER"):
            with self.assertRaises(ProviderError, msg=key):
                registry.selection({key: "bedrock", "GROUNDED_BEDROCK_TEXT_MODEL": "amazon.nova-pro-v1:0"})

    def test_retired_cloud_providers_rejected(self):
        for key, value in (
            ("TRANS_PROVIDER", "transcribe"),
            ("TRANS_PROVIDER", "aws"),
            ("GROUNDED_TRANSCRIPTION_PROVIDER", "stub"),
            ("NARRATION_PROVIDER", "polly"),
            ("GROUNDED_TTS_PROVIDER", "elevenlabs"),
            ("GROUNDED_INFERENCE_PROVIDER", "openai"),
            ("GROUNDED_INFERENCE_PROVIDER", "anthropic"),
        ):
            with self.assertRaises(ProviderError, msg=f"{key}={value}"):
                registry.selection({key: value})
            with self.assertRaises(ProviderError, msg=f"aws {key}={value}"):
                registry.selection({**AWS_ENV, key: value})

    def test_aws_private_bedrock_selection(self):
        chosen = registry.selection({**AWS_ENV, "GROUNDED_INFERENCE_PROVIDER": "bedrock", "GROUNDED_ASSIST_FEATURES": "polish,chat,summary"})
        self.assertEqual(chosen.inference, "bedrock")
        self.assertEqual(chosen.models["text"], "amazon.nova-pro-v1:0")
        # Transcription and TTS stay local even in aws-private mode.
        self.assertEqual(chosen.transcription, "local")
        self.assertEqual(chosen.tts, "local")

    def test_unlisted_model_rejected_at_selection(self):
        with self.assertRaises(ProviderError):
            registry.selection({**AWS_ENV, "GROUNDED_INFERENCE_PROVIDER": "bedrock", "GROUNDED_BEDROCK_TEXT_MODEL": "amazon.nova-premier-v1:0"})

    def test_long_lived_keys_refused(self):
        with self.assertRaises(ProviderError):
            registry.selection({**AWS_ENV, "GROUNDED_INFERENCE_PROVIDER": "bedrock", "AWS_ACCESS_KEY_ID": "AKIAEXAMPLE", "AWS_SECRET_ACCESS_KEY": "x"})
        registry.selection({**AWS_ENV, "GROUNDED_INFERENCE_PROVIDER": "bedrock", "AWS_ACCESS_KEY_ID": "ASIAEXAMPLE", "AWS_SECRET_ACCESS_KEY": "x", "AWS_SESSION_TOKEN": "t"})

    def test_local_inference_requires_private_endpoint(self):
        with self.assertRaises(ProviderError):
            registry.selection({"GROUNDED_INFERENCE_PROVIDER": "local"})
        with self.assertRaises(ProviderError):
            registry.selection({"GROUNDED_INFERENCE_PROVIDER": "local", "MODEL_BASE_URL": "https://api.openai.com"})
        chosen = registry.selection({"GROUNDED_INFERENCE_PROVIDER": "local", "MODEL_BASE_URL": "http://vllm:8000"})
        self.assertEqual(chosen.inference, "local")

    def test_features_require_a_provider(self):
        with self.assertRaises(ProviderError):
            registry.selection({"GROUNDED_ASSIST_FEATURES": "chat"})

    def test_unknown_values_rejected(self):
        with self.assertRaises(ProviderError):
            registry.selection({"GROUNDED_INFERENCE_PROVIDER": "magic"})
        with self.assertRaises(ProviderError):
            registry.selection({"GROUNDED_INFERENCE_PROVIDER": "local", "MODEL_BASE_URL": "http://vllm:8000", "GROUNDED_ASSIST_FEATURES": "invent"})


class BedrockProviderTest(unittest.TestCase):
    def test_offline_refuses_even_an_injected_client(self):
        fake = FakeBedrock('{"text": "x"}')
        with env({"GROUNDED_BEDROCK_TEXT_MODEL": "amazon.nova-pro-v1:0", "AWS_REGION": "us-east-1"}):
            with self.assertRaises(ProviderError):
                BedrockInference(client=fake)
        self.assertEqual(fake.calls, [])

    def test_aws_private_converse_with_allowlisted_model(self):
        fake = FakeBedrock("Revenue is $4.82M.")
        with env(AWS_ENV):
            model = BedrockInference(client=fake)
            result = model.complete("sys", "prompt", max_tokens=50)
        self.assertEqual(result.text, "Revenue is $4.82M.")
        self.assertEqual(result.provider, "bedrock")
        self.assertEqual(result.model_id, "amazon.nova-pro-v1:0")
        self.assertEqual(fake.calls[0]["modelId"], "amazon.nova-pro-v1:0")
        self.assertEqual(fake.calls[0]["inferenceConfig"]["temperature"], 0)

    def test_unapproved_endpoint_refused(self):
        with env({**AWS_ENV, "GROUNDED_BEDROCK_ENDPOINT": "https://bedrock-runtime.us-east-1.amazonaws.com"}):
            with self.assertRaises(ProviderError):
                BedrockInference(client=FakeBedrock())
        with env({**AWS_ENV, "GROUNDED_BEDROCK_ENDPOINT": "https://proxy.example.com"}):
            with self.assertRaises(ProviderError):
                BedrockInference(client=FakeBedrock())

    def test_multimodal_attachments_do_not_leak_filenames(self):
        fake = FakeBedrock("Pipeline")
        with env(AWS_ENV):
            model = BedrockInference(model_id="amazon.nova-lite-v1:0", client=fake)
            model.complete("s", "p", attachments=(
                Attachment("image", "png", b"\x89PNG", name="Q3 layoffs plan.png"),
                Attachment("document", "pdf", b"%PDF", name="secret-roadmap.pdf"),
            ))
        content = fake.calls[0]["messages"][0]["content"]
        self.assertIn("image", content[0])
        self.assertEqual(content[1]["document"]["name"], "source 2")
        self.assertNotIn("secret", json.dumps(content, default=str))

    def test_image_text_marks_extractor(self):
        fake = FakeBedrock("Orders dashboard\n\nOpen tickets 42")
        with env(AWS_ENV):
            reader = BedrockImageText(client=fake)
            self.assertEqual(reader.extract_text(b"\x89PNG", "png"), ["Orders dashboard", "Open tickets 42"])
            self.assertEqual(reader.model_id, "amazon.nova-lite-v1:0")

    def test_embeddings(self):
        fake = FakeBedrock(embedding=[0.1] * 1024)
        with env(AWS_ENV):
            vectors = BedrockEmbeddings(client=fake).embed(["revenue"])
        self.assertEqual(len(vectors[0]), 1024)
        body = json.loads(fake.calls[0]["body"])
        self.assertEqual(body["dimensions"], 1024)

    def test_provider_failure_is_reported_without_content(self):
        class Broken(FakeBedrock):
            def converse(self, **kwargs):
                raise RuntimeError("upstream echoed: CONFIDENTIAL margin 31%")

        with env(AWS_ENV):
            with self.assertRaises(ProviderError) as caught:
                BedrockInference(client=Broken()).complete("s", "p")
        self.assertNotIn("CONFIDENTIAL", str(caught.exception))


class NoFallbackTest(unittest.TestCase):
    def test_bedrock_failure_never_calls_local_model(self):
        from grounded.chat import answer_grounded

        script = {"beats": [{"ord": 1, "kind": "kpi", "layout": "big-number", "text": "Orders are 1,200.",
                             "claims": [{"value": 1200, "sheet": "KPI", "addr": "B3"}],
                             "citations": [{"kind": "workbook", "sheet": "KPI", "addr": "B3"}]}]}

        class Failing:
            name, model_id = "bedrock", "amazon.nova-pro-v1:0"
            calls = 0

            def complete(self, *a, **k):
                Failing.calls += 1
                raise ProviderError("throttled")

        with mock.patch("grounded.providers.local.LocalInference") as local:
            result = answer_grounded(script, "How many orders?", provider=Failing())
        local.assert_not_called()
        self.assertEqual(Failing.calls, 1)
        self.assertEqual(result["text"], "Orders are 1,200.")
        self.assertEqual(result["provider"], "retrieval")

    def test_inference_provider_raises_instead_of_switching(self):
        with env({**AWS_ENV, "GROUNDED_INFERENCE_PROVIDER": "bedrock", "GROUNDED_ASSIST_FEATURES": "chat",
                  "MODEL_BASE_URL": "http://vllm:8000"}):
            with mock.patch("grounded.providers.bedrock._client", side_effect=ProviderError("no endpoint")):
                with mock.patch("grounded.providers.local.LocalInference") as local:
                    with self.assertRaises(ProviderError):
                        registry.inference_provider("chat")
                local.assert_not_called()

    def test_transcription_has_no_cloud_path(self):
        with env(AWS_ENV):
            provider = registry.transcription_provider()
        self.assertEqual(provider.name, "local")
        with env({"GROUNDED_TRANSCRIPTION_PROVIDER": "none"}):
            with self.assertRaises(ProviderError):
                registry.transcription_provider()


class LocalResourcesTest(unittest.TestCase):
    def test_narration_requires_local_voice(self):
        import tempfile
        from pathlib import Path

        from grounded.providers.local import LocalPiper

        with env({"PIPER_BIN": "/nonexistent/piper", "PIPER_MODEL": "/nonexistent/model.onnx"}):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ProviderError) as caught:
                    LocalPiper().narrate({"beats": [{"ord": 1, "text": "Open Settings."}]}, Path(tmp) / "v.mp3")
        self.assertIn("public TTS is disabled", str(caught.exception))

    def test_whisper_refuses_runtime_download(self):
        import tempfile
        from pathlib import Path

        from grounded.providers.local import LocalWhisper

        with tempfile.TemporaryDirectory() as tmp:
            with env({"WHISPER_CACHE": tmp}):
                with self.assertRaises(ProviderError) as caught:
                    LocalWhisper(model_name="base", cache_dir=tmp).transcribe(Path(tmp) / "none.wav")
            self.assertEqual(os.listdir(tmp), [])
        self.assertTrue("not preloaded" in str(caught.exception) or "not installed" in str(caught.exception))


if __name__ == "__main__":
    unittest.main()
