# Deploy Bagley — Mac hospeda modelo, Kali consome via rede

Modelo fica no Mac (Ollama + Metal). TUI roda local no Mac pra teste e na Kali VM apontando pro Mac via HTTP. Execução (nmap/sqlmap/etc) isolada na Kali.

---

## Arquitetura

```
Kali VM (TUI + ferramentas) ──HTTP──▶ Mac (Ollama Metal, bagley-v10 GGUF)
         │                                    │
         │  tool_call("shell", "nmap -sC ...")│
         │◀────────────────────────────────────
         ▼
   executa nmap na Kali (scope isolado)
         │ stdout
         └───HTTP──▶ Mac LLM comenta → volta Kali
```

Inferência ~30 tok/s em M-series. Modelo nunca sai do Mac.

---

## 1. Exportar modelo no Windows (origem)

v10 treinou no Modal. Pull + merge + GGUF + quantize:

```bash
cd C:/Users/Virgilio/Desktop/projetos/bagley

# pull adapter da cloud
.venv/Scripts/python.exe -m modal run scripts/modal_train.py::pull_v10

# antes de exportar: em scripts/modal_train.py, no entrypoint export_v9,
# trocar 'bagley-v9-modal' → 'bagley-v10-modal'
.venv/Scripts/python.exe -m modal run scripts/modal_train.py::export_v9
# saída: runs/bagley-v10-Q4_K_M.gguf (~5 GB)
```

Quantizações alternativas em DEPLOY.md (Q5_K_M melhor qualidade, IQ2_XS mínimo).

---

## 2. Transferir Windows → Mac

Qualquer uma:

```bash
# SCP — Mac com SSH ligado (Settings → General → Sharing → Remote Login)
scp runs/bagley-v10-Q4_K_M.gguf virgilio@mac.local:~/bagley/

# Ou USB / iCloud Drive / AirDrop
```

TUI (código) não copia manual — clona do GitHub:

```bash
# no Mac:
git clone https://github.com/virgiliolrf/bagley ~/bagley-src
cd ~/bagley-src
git checkout tui-phase1

python3 -m venv .venv
source .venv/bin/activate
pip install -e . textual pytest pytest-asyncio networkx pyperclip responses
```

---

## 3. Mac — Ollama serve exposto na LAN

```bash
brew install ollama

cd ~/bagley
cat > Modelfile <<'EOF'
FROM ./bagley-v10-Q4_K_M.gguf

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
EOF

ollama create bagley -f Modelfile

# Bind 0.0.0.0 pra Kali acessar via rede
OLLAMA_HOST=0.0.0.0:11434 ollama serve &

# Descobre IP do Mac
ipconfig getifaddr en0        # ex: 192.168.1.10
```

**Firewall macOS:** Settings → Network → Firewall → permitir Ollama.

**Testar local no Mac:**
```bash
cd ~/bagley-src
source .venv/bin/activate
python -m bagley.tui.app      # usa localhost:11434 automático
```

Dentro do TUI: Ctrl+Shift+M abre engine swap modal — `bagley` aparece listado.

---

## 4. Kali VM — TUI cliente via OLLAMA_HOST

**VirtualBox VM Settings:**
- Network → Adapter 1 → **Bridged Adapter** (Kali pega IP da LAN direto)
- Alternativa: NAT Network + port forward 11434

**Instalação Kali:**
```bash
sudo apt update && sudo apt install -y git python3-venv python3-pip

git clone https://github.com/virgiliolrf/bagley ~/bagley-src
cd ~/bagley-src
git checkout tui-phase1

python3 -m venv .venv
source .venv/bin/activate
pip install -e . textual pytest pytest-asyncio networkx pyperclip responses
```

**Aponta pro Mac:**
```bash
export OLLAMA_HOST=http://192.168.1.10:11434     # IP do Mac descoberto na Fase 3

# Persistente (opcional):
echo 'export OLLAMA_HOST=http://192.168.1.10:11434' >> ~/.bashrc

# Valida conexão:
curl $OLLAMA_HOST/api/tags                        # lista modelos do Mac → tem que retornar JSON com "bagley"

# Roda TUI:
python -m bagley.tui.app
```

Patch `OLLAMA_HOST` env var já aplicado em `src/bagley/tui/services/engine_registry.py` e `src/bagley/inference/engine.py` (commit `5fd2ec7`).

---

## Troubleshooting

| Sintoma | Causa | Fix |
|---------|-------|-----|
| `curl` no Kali não responde | firewall Mac bloqueou | Settings → Network → Firewall → allow Ollama |
| Ollama só escuta 127.0.0.1 | `OLLAMA_HOST=0.0.0.0:11434` não setado antes de `ollama serve` | mata processo, relança com env var |
| TUI não vê modelo remoto | env var não exportada na sessão da TUI | `echo $OLLAMA_HOST` deve mostrar IP Mac antes de `python -m bagley.tui.app` |
| Latência alta entre Mac e Kali | NAT com port forward introduz hop | muda VM pra Bridged Adapter |
| Kali sem IP de LAN | VirtualBox NAT default | muda pra Bridged |
| Conflito porta 11434 na Kali | Ollama local rodando | `sudo systemctl stop ollama` ou desinstala |

---

## Fluxo ReAct (runtime)

1. Usuário digita no TUI (Kali): `escaneie 10.10.10.5`
2. TUI envia prompt HTTP POST → Mac Ollama `/api/chat`
3. Mac (Metal GPU) gera resposta com `<tool_call>{"name":"shell","arguments":{"cmd":"nmap -sC -sV 10.10.10.5"}}</tool_call>`
4. TUI extrai tool_call, mostra ConfirmPanel inline (Y/N)
5. Confirma Y → `subprocess.run()` na **Kali** (não Mac)
6. Stdout vai pra memory/SQLite + de volta ao LLM como observation
7. LLM comenta, propõe próximo passo
8. Loop até answer final

Execução sempre na Kali. LLM nunca toca arquivos do Mac/host fora do próprio volume Ollama.
