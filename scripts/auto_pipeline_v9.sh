#!/usr/bin/env bash
# Pipeline autônomo: aguarda v8.1 terminar, roda eval, constrói v9 dataset, treina v9, avalia v9.
# Rode em background: nohup bash scripts/auto_pipeline_v9.sh > runs/auto_pipeline.log 2>&1 &

set -u
cd "$(dirname "$0")/.."

PY=".venv/Scripts/python.exe"
export PYTHONUNBUFFERED=1
export PYTHONUTF8=1

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

wait_for_training_done() {
    local run_dir="$1"
    local log_file="$2"
    local label="$3"
    log "AUTO: esperando $label terminar..."
    local last_step=""
    while true; do
        # Check se há train_runtime no log (indica completion)
        if grep -q "train_runtime" "$log_file" 2>/dev/null; then
            log "AUTO: $label terminou (train_runtime encontrado)"
            return 0
        fi
        # Check se processo morreu sem completar
        if ! pgrep -f "bagley.train.train.*$(basename $run_dir)" >/dev/null 2>&1; then
            # Processo não tá rodando; pode ter terminado ou crashado
            if [ -f "$run_dir/adapter_model.safetensors" ]; then
                log "AUTO: $label completou (adapter presente, sem train_runtime no log)"
                return 0
            fi
            # Pode estar em fase de save final — aguarda mais
            local cur_step=$(grep -oE '[0-9]+/[0-9]+ \[' "$log_file" 2>/dev/null | tail -1 | head -c 10)
            if [ "$cur_step" = "$last_step" ] && [ -n "$cur_step" ]; then
                # Sem progresso há X ciclos = provavelmente morreu
                local stalled_checks=${stalled_checks:-0}
                stalled_checks=$((stalled_checks + 1))
                if [ "$stalled_checks" -gt 10 ]; then
                    log "AUTO: $label parece ter morrido (sem progresso). Usando último checkpoint."
                    return 1
                fi
            else
                stalled_checks=0
            fi
            last_step="$cur_step"
        fi
        sleep 60
    done
}

promote_last_checkpoint() {
    # Se top-level dir não tem adapter mas checkpoint-X tem, copia
    local run_dir="$1"
    if [ ! -f "$run_dir/adapter_model.safetensors" ]; then
        local last_ckpt=$(ls -d "$run_dir"/checkpoint-* 2>/dev/null | sort -V | tail -1)
        if [ -n "$last_ckpt" ] && [ -f "$last_ckpt/adapter_model.safetensors" ]; then
            log "AUTO: promovendo $last_ckpt para top-level"
            cp "$last_ckpt/adapter_model.safetensors" "$run_dir/"
            cp "$last_ckpt/adapter_config.json" "$run_dir/"
            cp "$last_ckpt/tokenizer"* "$run_dir/" 2>/dev/null || true
            cp "$last_ckpt/chat_template.jinja" "$run_dir/" 2>/dev/null || true
        fi
    fi
}

# ============================================================================
# FASE 1: aguardar v8.1
# ============================================================================

log "=============================================="
log "AUTO_PIPELINE_V9 iniciando"
log "=============================================="

wait_for_training_done "runs/bagley-v8.1" "runs/bagley-v8.1-resume.log" "v8.1 (resume)"
promote_last_checkpoint "runs/bagley-v8.1"

# ============================================================================
# FASE 2: eval v8.1
# ============================================================================

log "AUTO: rodando eval v8.1"
$PY scripts/eval_bagley.py --adapter ./runs/bagley-v8.1 --out-dir ./runs/eval-v8.1 > runs/eval-v8.1-run.log 2>&1
log "AUTO: eval v8.1 concluída → runs/eval-v8.1/report.md"

# ============================================================================
# FASE 3: construir dataset v9
# ============================================================================

log "AUTO: construindo dataset v9"
$PY scripts/build_dataset_v9.py > runs/build_v9.log 2>&1
log "AUTO: dataset v9 built → $(tail -2 runs/build_v9.log | head -1)"

# ============================================================================
# FASE 4: treinar v9
# ============================================================================

log "AUTO: iniciando treino v9 (3 epochs)"
$PY -m bagley.train.train --output-dir ./runs/bagley-v9 --epochs 3 > runs/bagley-v9-train.log 2>&1
log "AUTO: treino v9 finalizado (exit $?)"
promote_last_checkpoint "runs/bagley-v9"

# ============================================================================
# FASE 5: eval v9
# ============================================================================

log "AUTO: rodando eval v9"
$PY scripts/eval_bagley.py --adapter ./runs/bagley-v9 --out-dir ./runs/eval-v9 > runs/eval-v9-run.log 2>&1
log "AUTO: eval v9 concluída → runs/eval-v9/report.md"

# ============================================================================
# FASE 6: sumário final
# ============================================================================

log "=============================================="
log "PIPELINE COMPLETO"
log ""
log "Artefatos finais:"
log "  - runs/bagley-v8.1/adapter_model.safetensors"
log "  - runs/bagley-v9/adapter_model.safetensors"
log ""
log "Reports:"
log "  - runs/eval-v8.1/report.md"
log "  - runs/eval-v9/report.md"
log "=============================================="

# Dump scores finais pra quick scan
echo "--- v8.1 scores ---"
tail -20 runs/eval-v8.1-run.log | grep -E "(10|OVERALL|hallucin|must-not)"
echo "--- v9 scores ---"
tail -20 runs/eval-v9-run.log | grep -E "(10|OVERALL|hallucin|must-not)"
