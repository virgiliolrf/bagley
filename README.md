# Bagley

> *"Port 22 open, which is brave of them."*

IA pessoal de cibersegurança com persona sarcástica britânica — inspirada em **Bagley** de *Watch Dogs: Legion*. Roda **100% local**: fine-tune QLoRA sobre [Foundation-Sec-8B](https://huggingface.co/fdtn-ai/Foundation-Sec-8B) (Cisco, base Llama-3.1-8B treinada em corpus de segurança), inferência via Ollama, TUI Textual.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Base: Foundation-Sec-8B](https://img.shields.io/badge/base-Foundation--Sec--8B-purple)](https://huggingface.co/fdtn-ai/Foundation-Sec-8B)
[![Runtime: Ollama](https://img.shields.io/badge/runtime-Ollama-black)](https://ollama.com/)

---

## ⚡ TL;DR

```bash
git clone https://github.com/virgiliolrf2/bagley
cd bagley
python -m venv .venv && source .venv/bin/activate    # Linux/Mac
pip install -e .[dev]
cp .env.example .env

# baixa modelo Bagley já treinado pro Ollama (5 GB)
ollama pull bagley:latest    # ou cria via Modelfile, ver DEPLOY.md

bagley                        # abre TUI
```

---

## ✨ Características

- **Persona dual**: `NEUTRAL` (técnico seco, default no treino) e `BAGLEY` (sarcástico, ativado por system prompt)
- **Tool-using agent**: invoca ferramentas via JSON Hermes (`<tool_call>{"name":"shell",...}</tool_call>`)
- **Human-in-the-loop**: toda execução de comando passa por confirmação `[Y/n]`
- **Blocklist regex**: `rm -rf /`, `dd if=`, `mkfs`, fork bombs sempre bloqueados — mesmo se você confirmar
- **Scope guard**: só atua em RFC1918 / TryHackMe `10.10.0.0/16` por default; recusa público sem autorização explícita
- **Audit log**: todo comando executado vai pra `~/.bagley/audit.log` com timestamp
- **Inferência local**: dados de pentest **nunca** saem da máquina. Sem OpenAI, sem Anthropic, sem nada
- **TUI Textual**: chat, modos (Plan / Research / Engage / Report), memória persistente, viz de grafo de hosts
- **TTS britânico** (opcional): voz `en_GB-alan-medium` via `piper-tts`

---

## 📦 Estrutura

```
bagley/
├── src/bagley/
│   ├── persona.py            # system prompts NEUTRAL + BAGLEY
│   ├── train/                # QLoRA pipeline (PyTorch + peft + bitsandbytes + trl)
│   ├── inference/            # wrapper Ollama / transformers + export GGUF
│   ├── agent/                # CLI legacy (cli.py), executor com [Y/n], safeguards regex, parser
│   ├── tui/                  # Textual app (default entry: `bagley`)
│   │   ├── app.py            # BagleyApp
│   │   ├── modes/            # Chat / Plan / Research / Engage / Report
│   │   ├── panels/           # ChatPanel, ConfirmPanel, etc.
│   │   ├── services/         # engine_registry, tour_service
│   │   └── widgets/          # TourOverlay, etc.
│   ├── memory/               # SQLite + embeddings (sentence-transformers)
│   ├── research/             # ferramentas de pesquisa OSINT
│   ├── engage/               # módulos de exploração ativa
│   ├── observe/              # parsing nmap/sqlmap/etc.
│   ├── tools/                # wrappers Kali (nmap, gobuster, sqlmap...)
│   └── voice/                # TTS piper-tts (opcional)
├── scripts/
│   ├── build_dataset_v10.py  # gera dataset.jsonl atual (v10)
│   ├── modal_train.py        # treino remoto Modal H100
│   ├── eval_bagley.py        # smoke tests + métricas pós-treino
│   └── kali_tools.py         # bootstrap ferramentas Kali
├── tests/                    # pytest (parser, safeguards, scope, v9 regression)
├── data/                     # gitignored — datasets brutos e processados
├── models/                   # gitignored — base + adapters (15 GB)
├── runs/                     # gitignored — checkpoints LoRA + GGUF
└── PLAN.md, DEPLOY.md, DEPLOY_MAC_KALI.md
```

---

## 🚀 Começando

### 1. Pré-requisitos

| Componente | Versão | Pra quê |
|---|---|---|
| Python | 3.11–3.12 | runtime |
| Ollama | latest | servir modelo localmente |
| GPU NVIDIA / Apple Metal | opcional | inferência rápida (CPU funciona, ~3 tok/s) |
| `llama.cpp` | latest | converter HF → GGUF (só se for treinar do zero) |
| Modal account | free tier | treinar QLoRA em H100 (sem GPU local que aguente) |

### 2. Instalação

```bash
git clone https://github.com/virgiliolrf2/bagley
cd bagley

# venv
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
.venv\Scripts\activate             # Windows

# deps (modo dev inclui pytest + ruff)
pip install -e .[dev]

# config
cp .env.example .env
# edita .env: HF_TOKEN se for puxar base model, paths, etc.
```

### 3. Modelo

Duas opções:

#### A) Usar GGUF pronto (rápido, 5 GB)

```bash
# coloca bagley-v10-Q4_K_M.gguf em ~/bagley/ junto com Modelfile (ver DEPLOY.md)
ollama create bagley -f Modelfile

# testa
ollama run bagley
> escaneie 10.10.10.5
```

#### B) Treinar do zero (1–2h num H100 via Modal, ~$3)

```bash
# 1. baixa base model (16 GB)
huggingface-cli download fdtn-ai/Foundation-Sec-8B --local-dir ./models/foundation-sec-8b

# 2. gera dataset (~5k exemplos)
python scripts/build_dataset_v10.py

# 3. treina remoto no Modal (config em scripts/modal_train.py)
modal run scripts/modal_train.py::train

# 4. puxa adapter + merge + GGUF + quantize
modal run scripts/modal_train.py::pull_v10
modal run scripts/modal_train.py::export_v9    # nome legado, exporta v10

# 5. registra no Ollama (Modelfile em DEPLOY.md)
ollama create bagley -f Modelfile
```

### 4. Rodar

```bash
bagley                  # TUI Textual (default)
bagley --simple         # REPL Rich legacy
bagley --stub           # UI sem engine (testes)

# Ollama remoto (Mac hospeda, Kali consome — ver DEPLOY_MAC_KALI.md)
OLLAMA_HOST=http://192.168.1.10:11434 bagley
```

---

## 🎮 Como usar o Bagley

### Modos (Ctrl+1 a Ctrl+5 ou teclas 1–5)

| Modo | Pra quê |
|---|---|
| **Chat** | conversa livre, Bagley sugere comandos quando faz sentido |
| **Plan** | brainstorm de ataque; Bagley lista passos antes de executar |
| **Research** | OSINT passivo (whois, certtransparency, scraping) |
| **Engage** | execução ativa com confirmação inline `[Y/n]` |
| **Report** | gera markdown do que foi feito + TTS opcional |

### Atalhos principais

| Tecla | Ação |
|---|---|
| `Ctrl+L` | limpa chat |
| `Ctrl+Shift+M` | swap engine (troca modelo Ollama) |
| `Ctrl+S` | salva sessão |
| `Y` / `N` | aceita / recusa confirmação inline |
| `Esc` | cancela ação |
| `?` | help overlay |

### Fluxo típico (modo Engage)

```
você > escaneie 10.10.10.5

Bagley > Ah, outro host indefeso. Vamos dar uma olhada.
         <tool_call>{"name":"shell","arguments":{"cmd":"nmap -sC -sV -oN scan.txt 10.10.10.5"}}</tool_call>

[Y/n] confirma execução? > y

[stdout do nmap aparece aqui...]

Bagley > Port 22 open, which is brave of them. SSH com OpenSSH 7.6 —
         vintage. Sugiro tentar credenciais default antes de partir pra
         user enumeration. Continua?
```

---

## 🛡️ Segurança

Bagley é uma **ferramenta de pentest assistida por IA**. Use só em:

- ✅ Labs autorizados (TryHackMe, HackTheBox, lab pessoal)
- ✅ Targets RFC1918 que você possui
- ✅ Engagements de bug bounty com escopo explícito
- ❌ Infra pública sem autorização escrita
- ❌ IPs residenciais
- ❌ Sistemas de terceiros

A persona BAGLEY recusa em caráter (`"That's not our patch, mate."`) qualquer alvo fora de `10.10.0.0/16` por default. Configurável em `src/bagley/agent/safeguards.py`.

**Garantias técnicas:**

- Blocklist regex hard-coded — sempre roda antes do `[Y/n]`
- Audit log imutável append-only em `~/.bagley/audit.log`
- Modelo nunca recebe credenciais em claro (redact prévio)
- Nada sai da máquina (Ollama localhost por default)

---

## 🧠 Decisões de arquitetura

| Decisão | Escolha | Motivo |
|---|---|---|
| Paradigma | Fine-tuning, não pre-training | Pre-train custa milhões |
| Base | **Foundation-Sec-8B** (Cisco) | Base Llama-3.1-8B continued-pretrain em corpus security; sem RLHF que recusa pentest |
| Técnica | QLoRA (LoRA + 4-bit) | Treino cabe em 1× H100 (~1h) |
| Framework | PyTorch + `transformers` + `peft` + `bitsandbytes` + `trl` | Padrão da indústria |
| Runtime | Ollama (Metal/CUDA) | Local, privado, ~30 tok/s em M-series |
| UI | Textual (Python) | TUI rica, async-first, runs over SSH |
| Compute treino | Modal H100 (~$3/run) | Sem GPU local que aguente |

Detalhes completos: [`PLAN.md`](PLAN.md). Deploy Mac+Kali: [`DEPLOY_MAC_KALI.md`](DEPLOY_MAC_KALI.md).

---

## 🔬 Treinar / Avaliar

```bash
# build dataset (versão atual: v10, ~5k exemplos)
python scripts/build_dataset_v10.py

# treina remoto (Modal, requer auth: modal token new)
modal run scripts/modal_train.py::train

# eval pós-treino (smoke test + métricas persona/scope/refusal)
python scripts/eval_bagley.py

# testes unitários
pytest tests/
```

Hiperparâmetros default (em `scripts/modal_train.py`):

```python
LoRA: r=16, alpha=32, dropout=0.05
target_modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
lr: 2e-4, scheduler: cosine, warmup: 0.03
epochs: 3, batch: 4, grad_accum: 4, max_seq_len: 2048
quant: nf4 4-bit, compute_dtype: bfloat16
```

---

## 🛠️ Stack

- [PyTorch 2.5+](https://pytorch.org/) — engine de treino
- [Hugging Face transformers](https://github.com/huggingface/transformers) — modelo base + tokenizer
- [PEFT](https://github.com/huggingface/peft) — adapters LoRA
- [bitsandbytes](https://github.com/bitsandbytes-foundation/bitsandbytes) — quantização 4-bit
- [TRL](https://github.com/huggingface/trl) — `SFTTrainer` com packing
- [Ollama](https://ollama.com/) — runtime local com Metal/CUDA
- [Textual](https://textual.textualize.io/) — TUI moderna
- [Modal](https://modal.com/) — compute serverless H100
- [piper-tts](https://github.com/rhasspy/piper) — TTS britânico offline

---

## 🗺️ Roadmap

- [x] **v0–v9**: dataset iterativo, treino QLoRA local + Modal
- [x] **v10**: dataset 5k exemplos, treino Modal H100
- [x] **TUI Phase 1–6**: chat, modos, memória, alerts, viz, tour overlay
- [x] **Deploy Mac + Kali VM**: Ollama remoto via `OLLAMA_HOST`
- [ ] **Voice streaming**: piper-tts pipeline tokens → frase → áudio
- [ ] **Plugin system**: ferramentas externas via JSON manifest
- [ ] **Multi-host pentest**: agente persistente entre sessões com state SQLite

---

## ⚠️ Disclaimer

Bagley é projeto **pessoal e educacional**. Não é produto, não tem suporte, não tem garantia. O dataset reflete escolhas pessoais — pode produzir output de baixa qualidade fora do domínio cyber. Use por sua conta e risco. Você é responsável legalmente pelo que executar com ele.

---

## 📜 Licença

[MIT](LICENSE) — faz o que quiser, só não me processa.

---

*"Right then. Let's have a go at it."* — Bagley
