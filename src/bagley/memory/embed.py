"""Embeddings via Ollama (nomic-embed-text local).

Usage:
    e = OllamaEmbedder()
    vec = e.encode("apache 2.4.49 path traversal")
    len(vec) == 768
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class OllamaEmbedder:
    model: str = "nomic-embed-text"
    host: str = "http://localhost:11434"
    timeout: float = 30.0

    def encode(self, text: str) -> list[float]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.host}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.encode(t) for t in texts]
