"""Commentator — decide se uma linha de output merece comentário do Bagley.

Regras leves (sem LLM) pra filtrar signal/ruído, depois LLM curto pra gerar quip.

Padrões que disparam commentary:
- nmap: porta aberta, OS detect, script vuln encontrado
- http response: status interessante (200 em admin, 500, redirect)
- hash crack: "Cracked" / "KEY FOUND"
- shell obtido: "uid=" / "Meterpreter session opened"
- falhas: "denied", "refused", "timeout"

Throttling: max 1 comentário por N segundos pra não virar motor-mouth.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass


@dataclass
class CommentaryConfig:
    min_interval_s: float = 3.0        # espaçamento mínimo entre comentários
    quip_max_tokens: int = 60          # quip curto


INTERESTING_PATTERNS = [
    (re.compile(r"\b\d+/tcp\s+open\b", re.IGNORECASE), "port_open"),
    (re.compile(r"\b\d+/udp\s+open\b", re.IGNORECASE), "port_open"),
    (re.compile(r"VULNERABLE", re.IGNORECASE), "vuln_confirmed"),
    (re.compile(r"uid=\d+.*gid=\d+", re.IGNORECASE), "shell_obtained"),
    (re.compile(r"root@[\w\-.]+:", re.IGNORECASE), "root_shell"),
    (re.compile(r"meterpreter session \d+ opened", re.IGNORECASE), "meterpreter"),
    (re.compile(r"KEY FOUND", re.IGNORECASE), "crack_success"),
    (re.compile(r"^\S+:\S+\s*$"), "credential_pair"),
    (re.compile(r"HTTP/\d\.\d\s+200", re.IGNORECASE), "http_200"),
    (re.compile(r"HTTP/\d\.\d\s+500", re.IGNORECASE), "http_500"),
    (re.compile(r"Status:\s*2\d\d", re.IGNORECASE), "web_200"),
    (re.compile(r"Status:\s*403", re.IGNORECASE), "web_403"),
    (re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE), "cve_ref"),
    (re.compile(r"anonymous\s+login\s+ok", re.IGNORECASE), "anon_login"),
    (re.compile(r"null\s+session", re.IGNORECASE), "null_session"),
    (re.compile(r"connection\s+refused", re.IGNORECASE), "conn_refused"),
    (re.compile(r"permission\s+denied", re.IGNORECASE), "perm_denied"),
]


class LineClassifier:
    """Classifica linha em categoria de interesse (ou None)."""

    def classify(self, line: str) -> str | None:
        for pat, label in INTERESTING_PATTERNS:
            if pat.search(line):
                return label
        return None


class StreamCommentator:
    """Observa stream linha-a-linha, decide se deve falar, gera quip via engine.

    engine: objeto com .generate(messages) -> Reply (LocalEngine / OllamaEngine)
    tts: objeto com .say(text). Se None, só imprime.
    """

    def __init__(self, engine, tts=None, cfg: CommentaryConfig = CommentaryConfig()) -> None:
        self.engine = engine
        self.tts = tts
        self.cfg = cfg
        self.classifier = LineClassifier()
        self._last_time = 0.0

    def on_line(self, line: str, context: str = "") -> None:
        label = self.classifier.classify(line)
        if label is None:
            return
        now = time.monotonic()
        if now - self._last_time < self.cfg.min_interval_s:
            return
        self._last_time = now
        self._speak(label, line, context)

    def _speak(self, label: str, line: str, context: str) -> None:
        prompt = (
            f"You just observed this in the live output of a tool Bagley is running. "
            f"Category: {label}. Line: '{line.strip()[:200]}'. "
            f"Context: {context or 'pentest engagement in progress'}. "
            f"Comment in one brief Bagley-voice sentence. Do not suggest next steps."
        )
        messages = [
            {"role": "system", "content": "You are Bagley. British, dry, brief. One sentence."},
            {"role": "user", "content": prompt},
        ]
        try:
            reply = self.engine.generate(messages, max_new_tokens=self.cfg.quip_max_tokens,
                                         temperature=0.8)
            quip = reply.text.strip().split("\n")[0][:200]
        except TypeError:
            # engines que não aceitam kwargs extra
            reply = self.engine.generate(messages)
            quip = reply.text.strip().split("\n")[0][:200]
        except Exception:
            return
        if self.tts:
            self.tts.say(quip)
        else:
            print(f"[bagley] {quip}")
