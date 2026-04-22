# Bagley

IA pessoal de cibersegurança com persona sarcástica britânica (inspirada em Watch Dogs: Legion).
Roda local. Fine-tune QLoRA sobre **Foundation-Sec-8B** (Cisco, base model Llama-3.1-8B continued-pretrain em corpus de segurança).

Detalhes completos de arquitetura, roadmap e decisões: ver [`PLAN.md`](./PLAN.md).

## Setup rápido

```bash
python -m venv .venv
. .venv/Scripts/activate    # Windows
pip install -e .[dev]
cp .env.example .env        # preencha HF_TOKEN
```

## Estrutura

- `src/bagley/persona.py` — system prompt
- `src/bagley/train/` — pipeline QLoRA
- `src/bagley/inference/` — wrapper Ollama / transformers
- `src/bagley/agent/` — CLI + executor com human-in-the-loop
- `scripts/build_dataset.py` — gera JSONL de treino
- `scripts/eval.py` — smoke tests pós-treino

## Segurança

Toda execução de comando passa por confirmação `[Y/n]`. Blocklist regex em `src/bagley/agent/safeguards.py`.

## CLI

- `bagley` — Textual TUI (default).
- `bagley --simple` — legacy Rich REPL.
- `bagley --stub` — skip engine load for UI-only testing.
