"""Research agent — orquestra: detect "don't know" → browse → summarize → store.

Integra com:
- BrowserTool pra web_research
- MemoryStore pra cache de pesquisas
- OllamaEmbedder pra indexar resultados

Trigger típico: Bagley gera resposta admitindo não saber, ReActLoop detecta isso e invoca:
    research_agent.investigate(user_query)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from bagley.memory.embed import OllamaEmbedder
from bagley.memory.store import MemoryStore
from bagley.tools.browser import BrowserTool, BrowseResult


DONT_KNOW_PATTERNS = [
    re.compile(r"\b(I have no record|don'?t recognize|not familiar|don'?t know|no such|fabricated|not a real)\b",
               re.IGNORECASE),
    re.compile(r"\b(cannot confirm|no information|uncertain about)\b", re.IGNORECASE),
]


def detect_knowledge_gap(assistant_text: str) -> bool:
    return any(p.search(assistant_text) for p in DONT_KNOW_PATTERNS)


@dataclass
class ResearchFinding:
    query: str
    url: str
    title: str
    excerpt: str
    score: float = 0.0


@dataclass
class ResearchAgent:
    browser: BrowserTool = field(default_factory=BrowserTool)
    embedder: OllamaEmbedder | None = None
    store: MemoryStore | None = None

    def investigate(self, query: str, save: bool = True,
                    max_pages: int = 3) -> list[ResearchFinding]:
        # Check cache first
        if self.store and self.embedder:
            q_vec = self.embedder.encode(query)
            similar = self.store.similar(q_vec, k=3, kind_filter="research")
            if similar and similar[0]["score"] > 0.92:
                # Hit de cache suficiente — reaproveita
                return [ResearchFinding(query=query, url="cache://", title=r["ref_id"],
                                        excerpt=r["text"][:800], score=r["score"])
                        for r in similar]

        # Browse live
        results = self.browser.research(query, max_pages=max_pages)
        findings: list[ResearchFinding] = []
        for br in results:
            if br.blocked or br.error or not br.text:
                continue
            excerpt = self._extract_relevant(br.text, query)
            findings.append(ResearchFinding(
                query=query, url=br.url, title=br.title, excerpt=excerpt,
            ))
            if save and self.store and self.embedder:
                ref_id = hashlib.sha256(br.url.encode()).hexdigest()[:16]
                text = f"{br.title}\n{excerpt}"
                vec = self.embedder.encode(text)
                self.store.add_vector(kind="research", ref_id=ref_id,
                                      text=text, embedding=vec)
        return findings

    def _extract_relevant(self, text: str, query: str, window: int = 1500) -> str:
        """Encontra a janela de texto mais relevante pra query (pico de overlap)."""
        words = set(re.findall(r"\w+", query.lower()))
        if not words:
            return text[:window]
        # Slide janela de 500 chars, conta matches
        best_score = 0
        best_pos = 0
        step = 200
        for i in range(0, max(1, len(text) - window), step):
            segment = text[i:i + window].lower()
            score = sum(1 for w in words if w in segment)
            if score > best_score:
                best_score = score
                best_pos = i
        return text[best_pos:best_pos + window]
