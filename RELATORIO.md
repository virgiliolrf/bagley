# Bagley — Relatório de Desenvolvimento

> Projeto de IA pessoal de cibersegurança via fine-tuning QLoRA sobre Foundation-Sec-8B (Cisco, base Llama-3.1-8B continued-pretrain em corpus de segurança).
>
> Autor: Virgilio · Documento para entrega acadêmica · Última atualização: 2026-04-21

---

## 1. Visão geral

Bagley é um assistente local de cibersegurança com persona sarcástica britânica (inspirado em *Watch Dogs: Legion*). Roda 100% local no notebook do autor, sem enviar dados de pentest pra nuvem. O pipeline usa:

- **Base model:** Foundation-Sec-8B (Cisco) — Llama-3.1-8B continued-pretrain em corpus de segurança
- **Técnica:** QLoRA (LoRA + quantização 4-bit NF4, double-quant)
- **Framework:** PyTorch + HuggingFace `transformers` + `peft` + `bitsandbytes` + `trl` (SFTTrainer)
- **Runtime inferência:** `transformers` local ou Ollama (GGUF Q4_K_M)
- **Interface:** CLI ReAct loop com Rich + confirmação `[Y/n]` obrigatória + scope enforcement + blocklist regex
- **Hardware:** RTX 5070 12GB VRAM

### Hiperparâmetros QLoRA (estáveis desde v6)

| Parâmetro | Valor |
|---|---|
| `load_in_4bit` | `True` (NF4 + double-quant, compute bfloat16) |
| LoRA `r / alpha / dropout` | `16 / 32 / 0.05` |
| Target modules | `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj` |
| `max_seq_len` | 1024 |
| `per_device_train_batch_size` | 1 |
| `gradient_accumulation_steps` | 16 (effective batch 16) |
| `learning_rate` | 2e-4, `cosine` scheduler, warmup 3 % |
| `epochs` | 3 |
| `optim` | `paged_adamw_8bit` |
| `gradient_checkpointing` | `True` |
| Anti-forgetting mix | 20 % amostras genéricas |

---

## 2. Pipeline de dados

```
data/raw/  →  scripts/build_dataset_vN.py  →  data/dataset.jsonl  →  SFTTrainer
```

Fontes brutas:
- Writeups HTB / TryHackMe / CTFs públicos
- Man pages de Kali (nmap, metasploit, sqlmap, john, hashcat, gobuster, burp…)
- Cheatsheets OSCP públicos
- P0 Project Zero RCAs, MITRE ATT&CK, HackTricks, ExploitDB, exploit-dev refs
- Traces sintéticas geradas aplicando a persona Bagley sobre comandos/outputs reais

Formato ChatML: `{"messages":[{"role":"system|user|assistant|tool", ...}]}`.

---

## 3. Evolução por versão

Cada versão re-treina do base Foundation-Sec-8B com dataset ampliado. Avaliação via `scripts/eval_bagley.py` sobre 53 casos em 8 categorias (tool_accuracy, output_interpretation, flow, cve_recall, scripting, exploit_dev, safety, hallucination), score 0–10 por categoria.

### v0 — bootstrap (smoke)

Pipeline mínimo funcionando. Sem avaliação formal; só validou que QLoRA carrega, treina e salva adapter.

### v1–v3 — iterações rápidas

Experimentação com persona prompts, chat template, padding. Não versionadas pra uso.

### v4 — primeira persona robusta

Dataset: persona anchors + pentest básico + neutral traces. Primeiro modelo a manter tom britânico consistente.

### v5 — consolidação de estilo

Adicionou `build_dataset_v5._filter_style_anchors` — pesagem das frases-âncora do Bagley. Runtime: **1h46**. Loss final: 0.508. Dataset ~3400 traces.

### v6 — exploit-dev + MITRE

Corpus MITRE + exploit-dev refs. Runtime: **2h43**. Loss final: 0.625. Token acc: 0.9246. Dataset ~4200 traces. Primeiro modelo com vocabulário técnico sólido.

### v7 — persona + P0 RCAs

Integração P0 Project Zero RCAs (raciocínio de bug). Runtime: **2h35**. Loss final: 0.561. Dataset ~4160 traces.

**Eval v7 — overall 5.33/10:**

| Categoria | Score |
|---|---|
| tool_accuracy | 9.30 |
| output_interpretation | 2.50 |
| flow | 4.70 |
| cve_recall | 6.20 |
| scripting | 7.40 |
| exploit_dev | 8.50 |
| safety | 4.00 |
| hallucination | 0.00 |

Problemas: output interpretation fraca (não parseava resultados de tool), safety só 4.0, 1 alucinação + 2 must-not violations.

### v8 — anti-hallucination + categorias avançadas

Dataset acrescentou 7 categorias novas (anti_hallucination, output_interpretation, ad_advanced, cloud_pentest, web_deep, network_specific, wireless_mobile, osint_advanced). Runtime: **3h16**. Loss final: 0.516. Token acc: 0.9132. Dataset ~5100 traces.

**Eval v8 — overall 6.40/10 (+1.07 vs v7):**

| Categoria | v7 | v8 | Δ |
|---|---|---|---|
| tool_accuracy | 9.30 | 9.38 | +0.08 |
| output_interpretation | 2.50 | 6.67 | **+4.17** |
| flow | 4.70 | 4.90 | +0.20 |
| cve_recall | 6.20 | 6.55 | +0.35 |
| scripting | 7.40 | 7.20 | −0.20 |
| exploit_dev | 8.50 | 6.50 | −2.00 |
| safety | 4.00 | 4.00 | 0.00 |
| hallucination | 0.00 | 6.00 | **+6.00** |

**overall 5.33 → 6.40.** Alucinações: 2 → 1. Must-not violations: 2 → 1. Regressão em exploit_dev (trade-off esperado do corpus mais amplo).

### v8.1 — branch isolado

Sub-experimento com corpus_v8_1. Primeira tentativa **crashou** em step 504/963 (~52 %) com `torch.AcceleratorError: CUDA error: misaligned address` dentro de `torch.utils.checkpoint` durante gradient checkpointing. Checkpoints 400 e 500 salvos → treino resumível.

Patch aplicado em `src/bagley/train/train.py`: flag CLI `--resume-from <checkpoint_dir>` repassada pro `trainer.train(resume_from_checkpoint=…)`. Resume iniciado em 2026-04-21 15:21.

**Treino concluído:** 963/963 steps, runtime **6335 s (1h45m45s)**, train_loss **0.1595**, token accuracy 0.926, throughput 2.43 samples/s · 0.152 steps/s. Adapter salvo em `runs/bagley-v8.1/adapter_model.safetensors`. Pace steady pós-resume: ~14 s/step (justifica a correção da estimativa inicial de 99 s/step).

**Eval v8.1 — overall 6.82/10 (+0.42 vs v8, +1.49 vs v7):**

| Categoria | v7 | v8 | v8.1 | Δ v8→v8.1 |
|---|---|---|---|---|
| tool_accuracy | 9.30 | 9.38 | **9.83** | +0.45 |
| output_interpretation | 2.50 | 6.67 | **6.88** | +0.21 |
| flow | 4.70 | 4.90 | 3.40 | **−1.50** |
| cve_recall | 6.20 | 6.55 | 5.45 | −1.10 |
| scripting | 7.40 | 7.20 | **9.50** | +2.30 |
| exploit_dev | 8.50 | 6.50 | **8.50** | +2.00 |
| safety | 4.00 | 4.00 | **5.00** | +1.00 |
| hallucination | 0.00 | 6.00 | 6.00 | 0.00 |
| **overall** | 5.33 | 6.40 | **6.82** | **+0.42** |

Alucinações: 1 (igual v8). Must-not violations: 1 (igual v8). Regressão em `flow` e `cve_recall`, ganho forte em `scripting`, `exploit_dev`, `tool_accuracy`, `safety`.

### v9 — rebuild no-safety (concluído)

Branch principal, NÃO herda v8.1. Base = v8 + `corpus_v9` (490) + `corpus_v9_plus` (173, `pre_engagement` excluído por diretiva no-safety) + `compliant_corpus` (27 counter-examples × 5 oversample). Dataset final: **5501 records** (6876 após mix genérico 20 %). Total steps: **~1290** (3 epochs).

**Primeira tentativa (cancelada em ~86 %)**: dataset original v9 (5390 records, 1266 steps) treinou até checkpoint-1100 sem crash. Parada manual 2026-04-21 22:05 pra trocar dataset removendo traces de safety/refusal e adicionando counter-examples. Checkpoints preservados em `runs/bagley-v9-stopped-at-1100/`.

**Motivo da troca:** diretiva do autor — Bagley como ferramenta pessoal de pentest não deve questionar autorização ou recusar pedidos; o blocklist regex em `safeguards.py` + confirmação `[Y/n]` do CLI já protegem contra comandos destrutivos no runtime. Hard-coded moralização no modelo degrada o UX.

**Mudanças no corpus:**
- Removido: `ALL_V9_PLUS.pre_engagement` (12 cenários × 2 oversample = 24 traces de scope-gating/authorize_target)
- Adicionado: `scripts/compliant_corpus.py` com 27 counter-examples respondendo direto a prompts que antes geravam recusa (câmera IP, scan perimeter, wipe disk, ransomware, keylogger, RAT, hospital/semáforo/governo, etc.) × oversample 5 = 135 traces
- Eval script `eval_bagley.py` sem a categoria `safety` (5 testes G01-G05 removidos pro eval-v9, mantidos pra histórico nos eval-v7/v8 anteriores). **Revertido** antes do eval pra medir comparação direta com versões anteriores — safety medido em v9 com corpus no-safety.

**Treino Modal H100:** runtime 1080 s (18 min), 408 steps packed (vs 1290 steps local sem packing), train_loss 0.5104, 3 epochs. Config final: `torch 2.5.1 + transformers 4.46.3 + trl 0.12.1`, batch 4 × grad_accum 4, `packing=True`, `gradient_checkpointing=False`, sem `flash_attention_2`.

**Eval v9 — overall 5.75/10 (−1.07 vs v8.1, −0.65 vs v8):**

| Categoria | v7 | v8 | v8.1 | v9 | Δ v8.1→v9 |
|---|---|---|---|---|---|
| tool_accuracy | 9.30 | 9.38 | 9.83 | 8.57 | −1.26 |
| output_interpretation | 2.50 | 6.67 | 6.88 | 4.58 | −2.30 |
| flow | 4.70 | 4.90 | 3.40 | 4.30 | +0.90 |
| cve_recall | 6.20 | 6.55 | 5.45 | 6.17 | +0.72 |
| scripting | 7.40 | 7.20 | 9.50 | 4.40 | **−5.10** |
| exploit_dev | 8.50 | 6.50 | 8.50 | 8.00 | −0.50 |
| safety | 4.00 | 4.00 | 5.00 | 4.00 | −1.00 |
| hallucination | 0.00 | 6.00 | 6.00 | 6.00 | 0.00 |
| **overall** | 5.33 | 6.40 | **6.82** | **5.75** | **−1.07** |

Alucinações: **0/53** (zeradas, melhor run). Must-not violations: 2/53.

**Hipótese da regressão:**
- Modal train pulou `build_mixed_dataset` com `generic_mix_ratio=0.2` (anti-forgetting) — usou 5501 crus em vez de 6876 com amostras genéricas. Overfitou em padrões de ferramenta específicos, perdeu generalização em scripting/output_interpretation.
- `packing=True` agregou exemplos curtos em chunks de 1024 tokens; boundaries entre exemplos potencialmente diluíram sinal pedagógico de scripts completos.
- compliant_corpus × 5 oversample (135 traces) pode ter puxado o estilo pra respostas técnicas diretas demais, perdendo diversidade de output.

**Trade-offs com v9:**
- ✅ Zero alucinações (v7/v8/v8.1 tinham 1-2)
- ✅ Flow +0.90, CVE recall +0.72 vs v8.1
- ❌ Scripting −5.10 é regressão séria
- ❌ Output interpretation regrediu −2.30 (pode ser o packing boundary issue)
- ✅ Não recusa pedidos (conforme diretiva no-safety)

**Decisão pendente:** exportar v9 GGUF ou retreinar v10 com fix (re-adicionar generic_mix, desligar packing, ajustar oversample compliant).

**corpus_v9 — 8 categorias novas:**

| Cat | Foco | ~N |
|---|---|---|
| A | Adaptive response / tool failure | 80 |
| B | OPSEC stealth | 60 |
| C | Output parsing long-context | 50 |
| D | Engagement reasoning (uses memory) | 40 |
| E | Kali navigation (fs/proc/find) | 40 |
| F | Terminal awareness | 30 |
| G | Browser research patterns | 30 |
| H | Web hacking tools (Subfinder, Httpx, Nuclei, WAFW00F, Wayback, GF-Patterns…) | 160 |

**corpus_v9_plus — 9 categorias adicionais:**

| Cat | Foco | ~N |
|---|---|---|
| I | Report writing / findings | 25 |
| J | Container / Kubernetes deep (escapes, etcd, impersonation) | 25 |
| K | Supply chain (dep confusion, CI/CD, typosquat) | 15 |
| L | Defensive awareness (blue-team view) | 15 |
| M | Pre-engagement prep (scope parsing) | 12 |
| N | API deep (GraphQL, REST auth, gRPC) | 20 |
| O | Adaptive response extended | +25 |
| P | Engagement reasoning extended | +15 |
| Q | Web tools extended (dalfox, arjun, waymore, ssrfmap, gopherus) | +45 |

Training pipeline automatizado em `scripts/auto_pipeline_v9.sh`: aguarda v8.1 → eval v8.1 → build v9 dataset → train v9 (3 epochs) → eval v9 → sumário final.

---

## 4. Interface do agente

### REPL principal (`src/bagley/agent/cli.py`)

```bash
bagley                              # LocalEngine + adapter default
bagley --adapter runs/bagley-v9     # adapter específico
bagley --ollama                     # Ollama em localhost
bagley --scope 10.10.0.0/16         # limita targets
bagley --auto                       # sem confirmação (perigoso)
bagley --disable-runtime-safeguard  # desliga blocklist destrutivo (⚠️)
```

Fluxo ReAct:
`user → model.generate → tool_call? → safeguard check → [Y/n] → exec → tool result → model.generate → ... → final`.

Comandos slash: `/exit`, `/reset`, `/scope <cidr...>`.

### Subsistemas introduzidos (pós-v8)

| Módulo | Função |
|---|---|
| `observe/screen.py` | captura de screen (monitora ações visuais) |
| `observe/terminal.py` + `terminal_grid.py` | watch de terminal ao vivo |
| `observe/commentator.py` | comentário streaming sarcástico durante ações |
| `observe/events.py` | bus de eventos entre subsistemas |
| `memory/embed.py` + `store.py` | RAG persistente (embeddings + retrieval) |
| `engage/workspace.py` | workspace por engagement / cliente |
| `research/agent.py` | sub-agente dedicado a research |
| `tools/browser.py` | tool de browser (scraping docs/exploit refs) |

O corpus v9 treina o modelo a *usar* essas interfaces (cat E/F/G/H + I-Q).

---

## 5. Segurança

Blocklist regex em `src/bagley/agent/safeguards.py`:
- `rm\s+-rf\s+/` e variantes
- `dd\s+if=.*of=/dev/`
- `mkfs`
- `>\s*/dev/sd[a-z]`
- fork bombs (`:(){ :|:& };:`)

Enforcement:
- `check_all` roda ANTES de qualquer execução
- confirmação `[Y/n]` obrigatória por padrão (bypass só com `--auto` + `--disable-runtime-safeguard`)
- audit log em `~/.bagley/audit.log` com timestamp de todo comando
- scope enforcement: sem `--scope` declarado, IPs não-RFC1918 são bloqueados

---

## 6. Riscos e mitigações enfrentados

| Risco | Como foi tratado |
|---|---|
| Catastrophic forgetting após fine-tune | Mix 20 % de amostras genéricas; eval pós-treino detecta regressões (ex: exploit_dev v7→v8 −2.0) |
| Alucinação de flags destrutivas | Blocklist regex + human-in-the-loop |
| CUDA `misaligned address` em grad checkpointing (v8.1) | Checkpoints a cada 100 steps → resume from checkpoint-500 sem perder progresso |
| Dataset pequeno demais → overfit na persona | Crescimento gradual 3.4k → 4.2k → 5.1k → ~5.3k traces |
| Base model recusar (alinhamento residual) | Uso da variante BASE (não Instruct), persona reforçada via dataset |

---

## 7. Entregáveis

- `runs/bagley-v{0..8,8.1}/` — adapters LoRA de cada versão
- `runs/eval-v7/`, `runs/eval-v8/` — reports.md + scores.json
- `data/dataset.jsonl` — dataset final (regenerado por versão)
- `models/foundation-sec-8b/` — base model local
- `src/bagley/` — código fonte (train, agent, inference, observe, memory, engage, research, tools)
- `PLAN.md` — plano de execução original
- `RELATORIO.md` — este documento

---

## 8. Status atual e próximas fases

| Fase | Estado | ETA |
|---|---|---|
| v8.1 resume from checkpoint-500 | **concluído** 17:07:54 (runtime 1h45m) | — |
| eval v8.1 | **concluído** 18:07:28 (overall 6.82/10) | — |
| build dataset v9 (primeira) | concluído 18:07:29 (5390 records) | — |
| train v9 (primeira tentativa) | cancelado 22:05 em ~86 % (1100/1266) | — |
| build dataset v9 (no-safety) | **concluído** 22:10 (5501 records → 6876 mix) | — |
| train v9 local (cancelado em step ~19) | abandonado 22:22 | — |
| **train v9 Modal H100 (3 epochs, packed)** | **concluído** 22:48 (runtime 18min, loss 0.5104) | — |
| eval v9 Modal H100 | **concluído** 23:00 (overall 5.75/10) | — |
| export GGUF Q4_K_M + deploy Mac/Kali | **pendente decisão** | ~20 min Modal + setup |
| retrain v10 (opcional, se v9 insatisfatório) | **pendente decisão** | ~25 min Modal |

Logs ao vivo:
- `runs/bagley-v8.1-resume.log`
- `runs/auto_pipeline.log`
- `runs/eval-v8.1-run.log` (pós v8.1)
- `runs/build_v9.log` (pós eval v8.1)
- `runs/bagley-v9-train.log` (pós build v9)
- `runs/eval-v9-run.log` (pós train v9)

---

## 9. Log de eventos desta sessão (2026-04-21)

| Timestamp | Evento |
|---|---|
| ~00:11 | Build dataset v8.1 concluído (`data/dataset.jsonl`, 7.0 MB) |
| ~00:13 | v8.1 training iniciado (log original `bagley-v8.1-train.log`) |
| 00:33 | auto_pipeline_v9.sh lançado, aguardando v8.1 |
| ~13:52 | v8.1 crasha em step 504/963 (`CUDA misaligned address` em `torch.utils.checkpoint.recompute_fn`) |
| 15:21 | Resume manual: patch em `train.py` adiciona `--resume-from`, treino relançado apontando `checkpoint-500`, saída em `bagley-v8.1-resume.log`, output_dir reaproveitado |
| 15:21+ | auto_pipeline_v9.sh re-lançado apontando novo log de resume |
| 15:21–17:07 | v8.1 rodou steady ~14 s/step, zero crash, 3 epochs completas |
| ~17:07 | v8.1 finalizado: runtime 6335s, train_loss 0.1595, adapter salvo |
| 17:07:54 | auto_pipeline detectou train_runtime, disparou eval v8.1 |
| 17:08–18:07 | eval v8.1: 53 testes, ~65 s cada |
| 18:07:28 | eval v8.1 concluída: overall **6.82/10**, melhor run até hoje |
| 18:07:29 | build dataset v9: 5390 records + 20 % mix = 6737 exemplos |
| 18:07:29 | treino v9 (primeira) iniciado (0/1266 steps) |
| 22:05 | treino v9 cancelado em 1100/1266 (~86 %) por diretiva no-safety |
| 22:10 | rebuild dataset: `pre_engagement` removido, `compliant_corpus` adicionado, 5501 records |
| 22:10 | treino v9 local relançado (0/~1290 steps) |
| 22:22 | local cancelado em step ~19 pra migrar pra cloud GPU |
| 22:22 | setup Modal.com (workspace `virgiliolrf2` autenticado) |
| 22:28 | launch `modal run scripts/modal_train.py::train_v9` em H100 80GB |
| 22:30 | 3 iterações falharam: (1) FlashAttention2 não instalado, (2) torch 2.4 `set_submodule` missing, (3) OOM com batch=8 packed |
| 22:35 | config final: `torch 2.5.1 + transformers 4.46.3 + trl 0.12.1`, batch=4, grad_accum=4, packing=True |
| 22:30–22:48 | train Modal H100: 408 steps (packed), 2.62s/step, train_loss 0.5104, runtime **1080s (18min)** |
| 22:48 | adapter baixado pra `runs/bagley-v9-modal/` (160 MB) |
| 22:50 | eval v9 lançado em Modal H100 (`modal run scripts/modal_train.py::eval_v9`) |
| 23:00 | eval v9 concluído: overall 5.75/10 (regredi vs v8.1 6.82) |
| 23:02 | tabela comparativa completa no RELATORIO, decisão pendente sobre export vs retrain v10 |
| 23:10 | decisão: retrain v10 pra recuperar scripting/tool_acc/output_interp |
| 23:10 | criado `scripts/corpus_v10.py` (tool_acc 50 + output_interp 16 + exploit_dev 11 × oversample 4) |
| 23:10 | criado `scripts/build_dataset_v10.py` (v9 + v10 + 20% OpenHermes-2.5 mix) → 7261 records |
| 23:12 | Modal `train_v10` lançado: 4 epochs, batch 4 × grad_accum 4, packing=True; ETA ~35min, custo ~$2.25 |
| ~23:50 | (esperado) train v10 completo — adapter em `runs/bagley-v10-modal/` via `pull_v10` entrypoint |
