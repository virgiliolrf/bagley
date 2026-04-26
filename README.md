# Bagley

Assistente pessoal de cibersegurança com persona sarcástica britânica. Inspirado no Bagley de *Watch Dogs: Legion*. Roda local: QLoRA sobre [Foundation-Sec-8B](https://huggingface.co/fdtn-ai/Foundation-Sec-8B) (Cisco, base Llama-3.1-8B treinada em corpus de segurança), inferência via Ollama, TUI feita em Textual.

Projeto pessoal. Sem garantia, sem suporte. Use por sua conta e risco.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Base](https://img.shields.io/badge/base-Foundation--Sec--8B-purple)](https://huggingface.co/fdtn-ai/Foundation-Sec-8B)
[![Runtime](https://img.shields.io/badge/runtime-Ollama-black)](https://ollama.com/)

## Setup rápido

```bash
git clone https://github.com/virgiliolrf/bagley
cd bagley

python -m venv .venv
source .venv/bin/activate          # Linux/Mac
.venv\Scripts\activate             # Windows

pip install -e .[dev]
cp .env.example .env

ollama pull bagley:latest          # ou cria via Modelfile, ver DEPLOY.md
bagley                             # abre TUI
```

## O que ele faz

Conversa em texto, sugere comandos de pentest (nmap, sqlmap, gobuster, etc.), pede confirmação `[Y/n]` antes de executar, parseia o output e comenta. Tudo local. Nada vai pra OpenAI, Anthropic ou nenhuma API externa.

A persona BAGLEY recusa em caráter qualquer alvo fora de `10.10.0.0/16` (range TryHackMe) por default. Se quiser outro escopo, edita `src/bagley/agent/safeguards.py`.

Comandos destrutivos passam por blocklist regex hard-coded antes do `[Y/n]`: `rm -rf /`, `dd if=`, `mkfs`, fork bombs. Você não consegue confirmar mesmo querendo. Foi uma decisão consciente porque o LLM já alucinou flags ruins durante testes.

Toda execução vai pra `~/.bagley/audit.log` com timestamp.

## Pré-requisitos

| Componente | Versão | Pra quê |
|---|---|---|
| Python | 3.11 ou 3.12 | runtime |
| Ollama | latest | servir modelo localmente |
| GPU NVIDIA / Apple Metal | opcional | inferência rápida (CPU funciona, ~3 tok/s) |
| `llama.cpp` | latest | converter HF para GGUF (só se for treinar do zero) |
| Conta Modal | free tier | treinar QLoRA em H100 |

## Modelo: usar pronto ou treinar do zero

### A) Usar GGUF pronto (5 GB)

Coloca `bagley-v10-Q4_K_M.gguf` na pasta `~/bagley/` junto com o Modelfile (template completo em [DEPLOY.md](DEPLOY.md)) e:

```bash
ollama create bagley -f Modelfile
ollama run bagley
> escaneie 10.10.10.5
```

### B) Treinar do zero

Roda em ~1h num H100 via Modal (custa uns $3). Tem que ter conta Modal autenticada (`modal token new`).

```bash
huggingface-cli download fdtn-ai/Foundation-Sec-8B --local-dir ./models/foundation-sec-8b

python scripts/build_dataset_v10.py
modal run scripts/modal_train.py::train

modal run scripts/modal_train.py::pull_v10
modal run scripts/modal_train.py::export_v9    # nome legado, exporta v10

ollama create bagley -f Modelfile
```

Hiperparâmetros default em `scripts/modal_train.py`:

```
LoRA: r=16, alpha=32, dropout=0.05
target: q,k,v,o,gate,up,down_proj
lr 2e-4, cosine, warmup 0.03
3 epochs, batch 4, grad_accum 4, max_seq 2048
nf4 4-bit, bf16 compute
```

## Como rodar

```bash
bagley                  # TUI Textual (default)
bagley --simple         # REPL Rich legacy
bagley --stub           # UI sem engine carregado (testes)

OLLAMA_HOST=http://192.168.1.10:11434 bagley   # remoto, ver DEPLOY_MAC_KALI.md
```

## Modos da TUI

Troca com `Ctrl+1` a `Ctrl+5` (ou só `1` a `5`):

| Modo | Pra que serve |
|---|---|
| Chat | conversa livre, sugere comandos quando faz sentido |
| Plan | brainstorm de ataque, lista passos antes de executar |
| Research | OSINT passivo (whois, certtransparency, scraping) |
| Engage | execução ativa com confirmação inline |
| Report | gera markdown do que foi feito, TTS opcional |

## Atalhos principais

| Tecla | Ação |
|---|---|
| `Ctrl+L` | limpa chat |
| `Ctrl+Shift+M` | troca de modelo Ollama |
| `Ctrl+S` | salva sessão |
| `Y` / `N` | aceita ou recusa confirmação inline |
| `Esc` | cancela |
| `?` | help overlay |

## Fluxo típico

```
você > escaneie 10.10.10.5

Bagley > Ah, outro host indefeso. Vamos dar uma olhada.
         <tool_call>{"name":"shell","arguments":{"cmd":"nmap -sC -sV -oN scan.txt 10.10.10.5"}}</tool_call>

[Y/n] confirma execução? > y

[stdout do nmap aparece aqui...]

Bagley > Port 22 open, which is brave of them. SSH com OpenSSH 7.6,
         vintage. Sugiro tentar credenciais default antes de partir
         pra user enumeration. Continua?
```

## Estrutura

```
bagley/
├── src/bagley/
│   ├── persona.py            system prompts NEUTRAL e BAGLEY
│   ├── train/                pipeline QLoRA (PyTorch + peft + bitsandbytes + trl)
│   ├── inference/            wrapper Ollama / transformers + export GGUF
│   ├── agent/                CLI legacy, executor com [Y/n], safeguards regex, parser
│   ├── tui/                  app Textual (entry: `bagley`)
│   │   ├── modes/            Chat, Plan, Research, Engage, Report
│   │   ├── panels/           ChatPanel, ConfirmPanel, etc.
│   │   ├── services/         engine_registry, tour, memory_promoter
│   │   └── widgets/          TourOverlay, palette, statusline, etc.
│   ├── memory/               SQLite + embeddings (sentence-transformers)
│   ├── research/             ferramentas OSINT
│   ├── engage/               módulos de exploração ativa
│   ├── observe/              parsing nmap, sqlmap, etc.
│   ├── tools/                wrappers Kali (nmap, gobuster, sqlmap...)
│   └── voice/                TTS piper-tts (opcional)
├── scripts/
│   ├── build_dataset_v10.py  gera dataset.jsonl atual
│   ├── modal_train.py        treino remoto Modal H100
│   ├── eval_bagley.py        smoke tests + métricas pós-treino
│   └── kali_tools.py         bootstrap ferramentas Kali
├── tests/                    pytest (parser, safeguards, scope, suite TUI completa)
├── data/                     gitignored, datasets brutos e processados
├── models/                   gitignored, base + adapters (~15 GB)
├── runs/                     gitignored, checkpoints LoRA + GGUF
└── PLAN.md, DEPLOY.md, DEPLOY_MAC_KALI.md
```

## Stack

PyTorch 2.5+, HuggingFace `transformers`, `peft`, `bitsandbytes`, `trl` (`SFTTrainer` com packing), Ollama com Metal/CUDA, Textual, Modal pra compute serverless H100, piper-tts pra voz britânica offline.

## Por que essas escolhas

| Decisão | Escolha | Motivo |
|---|---|---|
| Paradigma | Fine-tuning, não pre-train | Pre-train custa milhões |
| Base | Foundation-Sec-8B (Cisco) | Llama-3.1-8B continued-pretrain em corpus security, sem RLHF que recusa pentest |
| Técnica | QLoRA (LoRA + 4-bit) | Cabe em 1× H100 em ~1h |
| Framework | PyTorch + peft + bitsandbytes + trl | Padrão da indústria |
| Runtime | Ollama (Metal/CUDA) | Local, privado, ~30 tok/s em M-series |
| UI | Textual | TUI rica, async, roda sobre SSH |
| Treino | Modal H100 (~$3/run) | Sem GPU local que aguente |

Detalhes completos: [PLAN.md](PLAN.md). Deploy Mac+Kali via Ollama remoto: [DEPLOY_MAC_KALI.md](DEPLOY_MAC_KALI.md).

## Segurança

Bagley é ferramenta de pentest assistida. Use só em:

- Labs autorizados (TryHackMe, HackTheBox, lab pessoal)
- Targets RFC1918 que você possui
- Engagements de bug bounty com escopo escrito

Não use em infra pública sem autorização escrita, IPs residenciais, ou sistemas de terceiros. A persona recusa em caráter (`"That's not our patch, mate."`) qualquer alvo fora de `10.10.0.0/16` por default. Você é o responsável legal pelo que executar.

Garantias técnicas:

- Blocklist regex hard-coded, sempre roda antes do `[Y/n]`
- Audit log append-only em `~/.bagley/audit.log`
- Modelo não recebe credenciais em claro (redact prévio)
- Nada sai da máquina (Ollama localhost por default)

## Treinar e avaliar

```bash
python scripts/build_dataset_v10.py    # build dataset (v10, ~5k exemplos)
modal run scripts/modal_train.py::train

python scripts/eval_bagley.py          # smoke test + métricas persona/scope/refusal
pytest tests/                          # testes unitários
```

## Roadmap

- [x] v0 a v9: dataset iterativo, treino QLoRA local + Modal
- [x] v10: dataset 5k exemplos, treino Modal H100
- [x] TUI Phase 1 a 6: chat, modos, memória, alerts, viz, tour overlay
- [x] Deploy Mac + Kali VM via OLLAMA_HOST remoto
- [ ] Voice streaming: piper-tts pipeline tokens, frase, áudio
- [ ] Plugin system: ferramentas externas via JSON manifest
- [ ] Multi-host pentest: agente persistente entre sessões com state SQLite

## Disclaimer

Projeto pessoal e educacional. Não é produto. Sem garantia, sem suporte. O dataset reflete escolhas pessoais e pode produzir output ruim fora do domínio cyber. Você é legalmente responsável pelo que fizer com ele.

## Licença

[MIT](LICENSE).
