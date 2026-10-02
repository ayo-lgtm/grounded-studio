"""Local / internal providers for offline mode (also usable in aws-private).

* :class:`LocalInference` - an OpenAI-compatible server (vLLM, Ollama, TGI)
  on private infrastructure, reached only through :mod:`grounded.net`.
* :class:`LocalHashEmbeddings` - deterministic on-box hashing embedder.
* :class:`LocalWhisper` - faster-whisper with preloaded weights only.
* :class:`LocalPiper` - Piper or Kokoro on the box.
* :class:`LocalOCR` - the ``tesseract`` binary, if installed.

None of these download weights at runtime.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .base import Attachment, InferenceResult, ProviderError


class LocalInference:
    name = "local"

    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str | None = None) -> None:
        from ..egress import EgressError, assert_private_model

        raw = base_url if base_url is not None else os.environ.get("MODEL_BASE_URL", "")
        try:
            self.base_url = assert_private_model(raw)
        except EgressError as exc:
            raise ProviderError(str(exc)) from exc
        self.model_id = model or os.environ.get("MODEL_NAME") or "local-instruct"
        self._api_key = (api_key if api_key is not None else os.environ.get("MODEL_API_KEY", "")).strip()

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 1024,
        attachments: tuple[Attachment, ...] = (),
    ) -> InferenceResult:
        from ..net import NetError, post_json

        if attachments:
            raise ProviderError("the local text model does not accept attachments")
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            body = post_json(
                self.base_url + "/v1/chat/completions",
                {
                    "model": self.model_id,
                    "temperature": 0,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
                headers=headers,
                label="MODEL_BASE_URL",
            )
            text = str(body["choices"][0]["message"]["content"]).strip()
        except (NetError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"internal model request failed ({type(exc).__name__})") from None
        usage = body.get("usage") or {}
        return InferenceResult(
            text=text,
            provider=self.name,
            model_id=self.model_id,
            usage={k: int(v) for k, v in usage.items() if isinstance(v, int)},
        )


class LocalHashEmbeddings:
    name = "local-hash"
    model_id = "sha256-bag-768"
    dims = 768

    def embed(self, texts: list[str]) -> list[list[float]]:
        from ..knowledge import embed

        return [embed(text, self.dims) for text in texts]


class LocalWhisper:
    name = "local"

    def __init__(self, model_name: str | None = None, cache_dir: str | None = None) -> None:
        self.model_id = model_name or os.environ.get("WHISPER_MODEL") or "base"
        self.cache_dir = cache_dir or os.environ.get("WHISPER_CACHE") or "/opt/whisper"

    def transcribe(self, path: Path, language: str = "en") -> list[dict[str, Any]]:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ProviderError("faster-whisper is not installed; cloud ASR is not a fallback") from exc
        try:
            model = WhisperModel(
                self.model_id,
                device="cpu",
                compute_type="int8",
                download_root=self.cache_dir,
                local_files_only=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"faster-whisper weights are not preloaded ({type(exc).__name__})") from None
        try:
            segments, _info = model.transcribe(str(path), language=(language or "en")[:2], vad_filter=True)
            rows = list(segments)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"local transcription failed ({type(exc).__name__})") from None
        parsed: list[dict[str, Any]] = []
        for segment in rows:
            text = str(getattr(segment, "text", "") or "").strip()
            if not text:
                continue
            start = float(getattr(segment, "start", 0.0))
            end = float(getattr(segment, "end", start))
            parsed.append(
                {
                    "t_start_ms": int(start * 1000),
                    "t_end_ms": int(max(end, start + 0.2) * 1000),
                    "text": text,
                }
            )
        if not parsed:
            raise ProviderError("local transcription returned no speech")
        return parsed


class LocalPiper:
    name = "local"

    def __init__(self) -> None:
        from ..local_voice import engine_name

        self.model_id = engine_name()

    def narrate(self, script: dict[str, Any], out_path: Path) -> Path:
        from ..local_voice import LocalVoiceError, narrate_local

        try:
            return narrate_local(script, out_path)
        except LocalVoiceError as exc:
            raise ProviderError(str(exc)) from exc


class LocalOCR:
    name = "local-ocr"
    model_id = "tesseract"

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or os.environ.get("TESSERACT_BIN") or shutil.which("tesseract") or ""
        if not self.binary:
            raise ProviderError("local OCR requires the tesseract binary")

    def extract_text(self, data: bytes, fmt: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / f"image.{fmt or 'png'}"
            src.write_bytes(data)
            proc = subprocess.run(
                [self.binary, str(src), "stdout"],
                capture_output=True,
                timeout=120,
                check=False,
            )
        if proc.returncode != 0:
            raise ProviderError("local OCR failed")
        text = proc.stdout.decode("utf-8", "replace")
        return [part.strip() for part in text.split("\n\n") if part.strip()]
