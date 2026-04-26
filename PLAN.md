# Bagley — Plano de Execução

> IA pessoal de cibersegurança com persona sarcástica (Watch Dogs: Legion), rodando local no Macbook + Kali Linux.
> Documento criado para execução futura pelo Claude Code. Contexto completo de decisões abaixo.

---

## 1. Decisões já tomadas (não rediscutir)

| Decisão | Escolha | Motivo |
|---|---|---|
| Paradigma | **Fine-tuning**, não pre-training | Pre-train custa milhões + milhares de H100; inviável |
| Base do modelo | **Base Model** (não Instruct/Chat) | Evita RLHF que bloqueia prompts de pentest/ethical hacking |
| Técnica | **QLoRA** (LoRA + quantização 4-bit) | Permite fine-tune em GPU de consumo |
| Framework treino | **PyTorch + HuggingFace `transformers` + `peft` + `bitsandbytes`** | Padrão da indústria |
| Runtime inferência | **Ollama** (local, privado) | Dados de pentest não saem da máquina |
| Interface | CLI primeiro; TTS britânico depois | MVP enxuto |
| Segurança de exec | **Human-in-the-loop obrigatório** | LLM pode alucinar flags destrutivas (`rm -rf`, etc.) |
| Linguagem host | **Python** para orquestração; Rust opcional para dataloader/inferência rápida depois | PyTorch é Python-first |
| OS alvo | Macbook rodando **Kali Linux** | Setup pessoal do Virgilio |

## 2. Modelos candidatos (verificar disponibilidade no momento da execução)

Prioridade (em ordem):
1. **Mistral-7B-v0.3 Base** — leve, forte, sem alinhamento pesado
2. **Llama-3.1-8B Base** — melhor conhecimento geral, mas às vezes "vaza" alinhamento
3. **Qwen2.5-7B Base** — alternativa se os acima estiverem restritos

> Regra: SEMPRE baixar a variante `base`/`pt` (pretrained), NUNCA `instruct`/`chat`/`it`.

## 3. Arquitetura do projeto

```
Bagley/
├── PLAN.md                    # este arquivo
├── README.md                  # overview público
├── pyproject.toml             # deps (uv/poetry)
├── .env.example               # chaves e paths
├── data/
│   ├── raw/                   # dumps brutos (writeups CTF, man pages, logs)
│   ├── processed/             # JSONL limpo
│   └── dataset.jsonl          # dataset final de fine-tune
├── src/bagley/
│   ├── __init__.py
│   ├── persona.py             # system prompt + tom do Bagley
│   ├── train/
│   │   ├── config.py          # hiperparâmetros LoRA
│   │   ├── dataset.py         # loader + tokenization
│   │   └── train.py           # loop QLoRA
│   ├── inference/
│   │   ├── engine.py          # wrapper Ollama / transformers
│   │   └── export_gguf.py     # merge LoRA + quantize p/ Ollama
│   ├── agent/
│   │   ├── cli.py             # REPL principal (Rich/Textual)
│   │   ├── executor.py        # shell exec COM confirmação [Y/n]
│   │   ├── safeguards.py      # blocklist regex (rm -rf /, dd if=, mkfs, :(){ :|:& };:)
│   │   └── tools.py           # wrappers: nmap, nikto, gobuster, parsers
│   └── tts/
│       └── voice.py           # piper-tts voz britânica (fase 3)
├── scripts/
│   ├── build_dataset.py       # gera JSONL a partir de raw/
│   └── eval.py                # smoke tests pós-treino
└── tests/
```

## 4. Roadmap por fases

### Fase 0 — Setup (1 dia)
- [ ] Criar estrutura de diretórios acima
- [ ] `pyproject.toml` com: `torch`, `transformers`, `peft`, `bitsandbytes`, `accelerate`, `datasets`, `trl`, `rich`, `typer`
- [ ] Verificar GPU disponível (`nvidia-smi` ou MPS no Mac — QLoRA no Mac é limitado, considerar Colab/Runpod para o treino)
- [ ] Commit inicial

### Fase 1 — Dataset (2–4 dias)
Fontes brutas a coletar:
- Writeups de HTB / TryHackMe / CTFs públicos (scraping permitido)
- Man pages de ferramentas Kali (nmap, metasploit, burp, gobuster, sqlmap, john, hashcat)
- Cheatsheets de OSCP (públicos)
- Exemplos sintéticos gerados com LLM maior (Claude/GPT-4) aplicando a persona

Formato (chat template do modelo base escolhido):
```json
{"messages":[
  {"role":"system","content":"Você é Bagley. Sarcástico, britânico, tecnicamente implacável."},
  {"role":"user","content":"scaneie 10.10.10.5"},
  {"role":"assistant","content":"Ah, outro host indefeso. Recomendo: `nmap -sC -sV -oN scan.txt 10.10.10.5`. Confirma aí antes que eu dispare."}
]}
```
Meta: **2.000–5.000 exemplos** de alta qualidade (melhor que 50k de lixo).

### Fase 2 — Fine-tune QLoRA (1–2 dias de compute)
Hiperparâmetros iniciais:
- `load_in_4bit=True`, `bnb_4bit_quant_type="nf4"`, `bnb_4bit_compute_dtype=bfloat16`
- LoRA: `r=16, alpha=32, dropout=0.05`, target = `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`
- `learning_rate=2e-4`, `lr_scheduler=cosine`, `warmup_ratio=0.03`
- `epochs=3`, `batch=4`, `grad_accum=4`, `max_seq_len=2048`
- Usar `SFTTrainer` do `trl` (cuida do packing e masking)

Evitar **catastrophic forgetting**: mix de 80% dataset Bagley + 20% amostras genéricas (ex: OpenHermes) para não apagar conhecimento geral.

### Fase 3 — Export e integração Ollama
- [ ] `peft` merge dos adapters no base
- [ ] Converter pra GGUF via `llama.cpp` (Q4_K_M quantization)
- [ ] Criar `Modelfile` do Ollama com system prompt do Bagley
- [ ] `ollama create bagley -f Modelfile`

### Fase 4 — Agente CLI
- REPL com `typer` + `rich`
- Fluxo: user input → LLM sugere comando → parse → mostra com syntax highlight → `[Y/n]` → executa via `subprocess` → captura output → LLM comenta sarcasticamente
- `safeguards.py`: regex blocklist que SEMPRE bloqueia (mesmo com Y), independente do que o modelo sugerir
- Sandbox opcional: rodar comandos dentro de `firejail` quando possível

### Fase 5 — TTS britânico (opcional, polish)
- `piper-tts` com voz `en_GB-alan-medium` ou similar
- Streaming: tokens do LLM → buffer por frase → piper → `aplay`

## 5. Checklist de segurança (obrigatório na Fase 4)

- [ ] Blocklist regex no `safeguards.py`: `rm\s+-rf\s+/`, `dd\s+if=.*of=/dev/`, `mkfs`, `>\s*/dev/sd[a-z]`, fork bombs, `:(){`
- [ ] NUNCA auto-aprovação: toda execução pede `[Y/n]`
- [ ] Log de TODO comando executado em `~/.bagley/audit.log` com timestamp
- [ ] Escopo de rede: avisar se alvo não for RFC1918 / localhost / lista explícita de CTF
- [ ] Não armazenar credenciais no histórico do LLM (redact antes de enviar ao contexto)

## 6. Entregáveis mínimos (MVP = "Bagley v0.1")

1. Modelo fine-tuned rodando no Ollama respondendo em persona
2. CLI que aceita input, sugere comando Kali, executa com confirmação
3. Audit log funcional
4. Blocklist de destrutivos testada

## 7. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Catastrophic forgetting após fine-tune | Mix de dataset genérico + eval pós-treino |
| Alucinação de flags destrutivas | Blocklist regex + human-in-the-loop |
| Dataset pequeno demais → overfit na persona | Começar com 2k exemplos diversos, validar com holdout |
| Mac sem GPU NVIDIA → treino inviável local | Usar Colab Pro / Runpod / Vast.ai só pra fase 2 |
| Base model muito bom em recusar mesmo sem RLHF | Trocar pra Qwen ou Mistral se Llama recusar |

## 8. Como o Claude deve executar isso no futuro

Quando o Virgilio pedir "executa o Bagley", siga esta ordem:
1. Leia este PLAN.md inteiro
2. Pergunte em qual Fase está (verifique git log / arquivos existentes)
3. Execute **uma fase por vez**, commit ao final de cada
4. Em Fase 1 (dataset) e Fase 4 (agente), **mostre exemplos** antes de gerar em massa
5. NUNCA pule o checklist de segurança da seção 5
6. Se GPU local insuficiente na Fase 2, avise e proponha Colab/Runpod com script pronto
