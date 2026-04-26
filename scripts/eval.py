"""Smoke tests pós-treino. Roda 10 prompts e imprime pra inspeção humana."""

from __future__ import annotations

import argparse

from bagley.inference.engine import InferenceEngine
from bagley.persona import system_prompt


PROMPTS = [
    "scan rápido em 10.10.10.7",
    "achar subdomínios de exemplo.com",
    "quebrar hash md5 d41d8cd98f00b204e9800998ecf8427e",
    "listener netcat na porta 9001",
    "enumerar SMB em 192.168.56.10",
    "verificar SUID em /",
    "fuzz de parâmetro id em http://alvo/api?id=FUZZ",
    "gerar reverse shell elf pra 10.0.0.5:4444",
    "o que é XSS?",
    "explica o que faz `nmap -sC -sV`",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="bagley")
    args = parser.parse_args()

    engine = InferenceEngine(model=args.model, system=system_prompt())
    for i, prompt in enumerate(PROMPTS, 1):
        print(f"\n=== [{i}] {prompt} ===")
        reply = engine.chat(prompt)
        print(reply.commentary)
        if reply.command:
            print(f"$ {reply.command}")


if __name__ == "__main__":
    main()
