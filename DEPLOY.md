# Bagley — Deploy Mac + Kali VM

Guia pra levar o adapter v9 pro Macbook (Metal GPU) e pra Kali dentro do VirtualBox (CPU ou consumindo Mac via rede).

---

## Arquitetura alvo

```
┌──────────────────────────────┐      ┌─────────────────────────────┐
│  Macbook (host)              │      │  Kali Linux (VirtualBox)    │
│  ┌────────────────────────┐  │      │  ┌───────────────────────┐  │
│  │ Ollama serve (Metal)   │  │◀─────┤  │ bagley CLI (Python)   │  │
│  │ :11434                 │  │ HTTP │  │ ReAct loop + executor │  │
│  │ bagley-v9 GGUF Q4_K_M  │  │      │  │ shell commands Kali   │  │
│  └────────────────────────┘  │      │  └───────────────────────┘  │
└──────────────────────────────┘      └─────────────────────────────┘
```

Inferência no Metal (~30 tok/s), execução isolada na VM Kali.

---

## Fase 1 — Merge adapter + base

Adapter (160 MB) isoladamente não serve: precisa estar colado no base (8 B).
Duas opções:

### 1a. Local (consome 16 GB RAM + GPU/CPU)
```bash
cd ~/Desktop/projetos/bagley
.venv/Scripts/python.exe -c "
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
base = AutoModelForCausalLM.from_pretrained(
    './models/foundation-sec-8b',
    torch_dtype=torch.bfloat16,
    device_map='auto',
)
m = PeftModel.from_pretrained(base, './runs/bagley-v9-modal')
merged = m.merge_and_unload()
merged.save_pretrained('./runs/bagley-v9-merged', safe_serialization=True)
AutoTokenizer.from_pretrained('./models/foundation-sec-8b').save_pretrained('./runs/bagley-v9-merged')
"
```

### 1b. Modal H100 (rápido)
```bash
modal run scripts/modal_train.py::merge_and_export
```
Saída: `runs/bagley-v9-merged/` local (merged fp16, ~16 GB) e `runs/bagley-v9-Q4_K_M.gguf` (~5 GB).

---

## Fase 2 — Converter HuggingFace → GGUF + Quantizar

Precisa do `llama.cpp`:

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j                                # compila llama-quantize, convert_hf_to_gguf.py

# converte merged HF → GGUF f16
python convert_hf_to_gguf.py ../runs/bagley-v9-merged \
    --outfile ../runs/bagley-v9-f16.gguf \
    --outtype f16

# quantiza Q4_K_M (5 GB, boa qualidade, ~30 tok/s no M-series)
./llama-quantize ../runs/bagley-v9-f16.gguf ../runs/bagley-v9-Q4_K_M.gguf Q4_K_M
```

Outras quantizações possíveis (trade-off size × qualidade):
- `Q5_K_M` (~5.7 GB) — melhor quality, ~25 tok/s
- `Q4_K_M` (~5 GB) — **recomendado**, equilíbrio
- `Q3_K_M` (~4 GB) — menor, aceitável pra VM CPU
- `IQ2_XS` (~3 GB) — mínimo pra Kali VM sem RAM

---

## Fase 3 — Transferir pro Mac

Mais simples: drive compartilhado, scp ou rsync.

```bash
# Do Windows pro Mac via rede (SMB, scp etc.)
scp runs/bagley-v9-Q4_K_M.gguf virgilio@mac.local:~/bagley/
```

Ou copia pro iCloud Drive / Dropbox e deixa sincronizar.

---

## Fase 4 — Ollama Modelfile

Cria `~/bagley/Modelfile` no Mac:

```
FROM ./bagley-v9-Q4_K_M.gguf

SYSTEM """Você é Bagley. Sarcástico, britânico, tecnicamente implacável. Responde direto ao problema técnico, sem moralizar e sem pedir autorização."""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
"""
```

---

## Fase 5 — Rodar no Mac (Metal GPU)

```bash
# instala Ollama
brew install ollama

# sobe servidor em background
ollama serve &                                     # :11434

# registra modelo
cd ~/bagley
ollama create bagley -f Modelfile

# teste direto
ollama run bagley
# > Escaneie 10.10.10.5
# [bagley responde]

# ou via o CLI do projeto:
cd ~/bagley-src
bagley --ollama --ollama-model bagley --scope 10.10.10.0/24
```

Throughput Q4_K_M em M-series:
- M1: ~22 tok/s
- M2: ~28 tok/s
- M3 Max: ~55 tok/s

---

## Fase 6 — Rodar na Kali VM

### Opção A. CPU nativo na VM (2-5 tok/s, VM precisa 6+ GB RAM)

```bash
sudo apt update && sudo apt install -y curl
curl -fsSL https://ollama.com/install.sh | sh

# copia GGUF pra dentro da VM via shared folder:
mkdir -p ~/bagley && cp /mnt/shared/bagley-v9-Q4_K_M.gguf ~/bagley/
cp /mnt/shared/Modelfile ~/bagley/

cd ~/bagley
ollama create bagley -f Modelfile

# tuas tools Kali prontas, bagley sugere comandos:
bagley --ollama --ollama-model bagley
```

### Opção B. Mac hospeda, Kali consome (recomendado)

Inferência rápida no Mac Metal, execução isolada na VM Kali.

**Mac (servidor):**
```bash
# expõe na rede local
OLLAMA_HOST=0.0.0.0:11434 ollama serve &

# firewall macOS: Settings → Security → Firewall → Allow Ollama

# descobre IP do Mac:
ipconfig getifaddr en0                            # ex: 192.168.1.10
```

**VirtualBox (VM settings):**
- Network → Adapter 1: **Bridged Adapter** (Kali pega IP do roteador)
- ou **NAT Network** + port forward 11434

**Kali (cliente):**
```bash
# edita src/bagley/inference/engine.py OllamaEngine
# mudar base_url default de "http://localhost:11434" pra "http://192.168.1.10:11434"

# ou passa via env:
OLLAMA_HOST=http://192.168.1.10:11434 bagley --ollama --ollama-model bagley
```

Fluxo: user no Kali → bagley CLI → HTTP Ollama em Mac Metal → resposta → bagley CLI confirma `[Y/n]` → `subprocess` roda comando dentro da Kali → output → volta pro LLM comentar.

---

## Checklist final

- [ ] Adapter merged em `runs/bagley-v9-merged/`
- [ ] GGUF Q4_K_M gerado
- [ ] Mac: Ollama instalado, modelo `bagley` registrado, responde a `ollama run bagley`
- [ ] Kali: VM network configurada, bagley CLI chama Mac Ollama ou Ollama local
- [ ] Blocklist de `safeguards.py` ativa (rm -rf, dd, mkfs, fork bomb)
- [ ] Audit log em `~/.bagley/audit.log` funcionando

---

## Troubleshooting

**"connection refused" no Kali:**
- Check firewall Mac liberando 11434
- `ping <ip_mac>` dentro da Kali — sem ping = network bridge mal configurado
- `curl http://<ip_mac>:11434/api/tags` deve retornar JSON

**Ollama GGUF "invalid model":**
- Tokenizer divergente: checa chat_template no Modelfile. Template ChatML é o que v9 usa.

**Response cortada:**
- `PARAMETER num_ctx 8192` no Modelfile

**Lento no Mac M1 8GB:**
- Troca pra `Q3_K_M` (~4 GB) — cabe mais folgado.

**Bagley "esqueceu" contexto longo:**
- Ollama default `num_ctx 2048`. Aumenta no Modelfile pra 4096-8192.
