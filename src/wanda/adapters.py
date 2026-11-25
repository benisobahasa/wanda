"""Build ready-to-send request payloads for common LLM APIs. Wanda never sends anything itself.

You send the payload with your own client and your own API key. Nothing leaves your machine
unless you choose to send it.
"""
from __future__ import annotations

from typing import Dict, Optional

from .normalizer import Normalizer

SYSTEM = {
    "id": ("Pengguna berbicara bahasa Jawa atau dialek. Teks berasal dari speech-to-text dan mungkin salah dengar. "
           "Gunakan 'Probable Indonesian meaning' sebagai petunjuk, tetapi periksa kembali. Jika sebuah kata ditandai "
           "ambigu atau ragu, tanyakan atau sebutkan ketidakpastiannya, jangan menebak. Jawab dalam bahasa yang dipakai pengguna."),
    "en": ("The user speaks Javanese or a dialect. The text comes from speech-to-text and may be misheard. Use the "
           "'Probable Indonesian meaning' as a hint but double-check it. If a word is flagged ambiguous or uncertain, "
           "say so instead of guessing. Reply in the language the user used."),
}
PROVIDERS = ("generic", "openai", "anthropic")


def build_payload(text: str, provider: str = "generic", model: Optional[str] = None,
                  language: str = "id", normalizer: Optional[Normalizer] = None) -> Dict:
    if provider not in PROVIDERS:
        raise ValueError(f"provider must be one of {PROVIDERS}")
    if language not in SYSTEM:
        raise ValueError("language must be 'id' or 'en'")
    context = (normalizer or Normalizer()).annotate(text)["llm_context"]
    system = SYSTEM[language]
    if provider == "anthropic":
        return {"model": model or "<model>", "max_tokens": 1024, "system": system,
                "messages": [{"role": "user", "content": context}]}
    payload = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": context}]}
    if provider == "openai":  # also accepted by Ollama, vLLM, llama.cpp servers
        payload["model"] = model or "<model>"
    return payload
