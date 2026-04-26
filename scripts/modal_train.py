"""Modal.com training runner — treina adapter QLoRA do Bagley em H100.

Uso local (depois de `pip install modal` + `modal setup`):

    modal run scripts/modal_train.py::train_v9

Faz:
  1. Sobe dataset.jsonl local → Modal Volume
  2. Baixa Foundation-Sec-8B do HF (primeira vez; cacheado no Volume depois)
  3. Treina com H100 80GB (batch 8 × grad_accum 2, sem gradient_checkpointing)
  4. Baixa adapter pra runs/bagley-v9-modal/
"""

from __future__ import annotations

import os
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Image + volumes
# ---------------------------------------------------------------------------

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch==2.5.1",
        "transformers==4.46.3",
        "peft==0.13.2",
        "bitsandbytes==0.44.1",
        "accelerate==1.0.1",
        "trl==0.12.1",
        "datasets==3.1.0",
        "huggingface_hub==0.26.2",
        "sentencepiece",
        "protobuf",
    )
)

volume = modal.Volume.from_name("bagley-vol", create_if_missing=True)

app = modal.App("bagley-train", image=image)


LOCAL_ROOT = Path(__file__).parent.parent
LOCAL_DATASET = LOCAL_ROOT / "data" / "dataset.jsonl"
LOCAL_OUT = LOCAL_ROOT / "runs" / "bagley-v9-modal"


# ---------------------------------------------------------------------------
# Remote training function
# ---------------------------------------------------------------------------

@app.function(
    gpu="H100",
    volumes={"/vol": volume},
    timeout=3 * 3600,   # 3h
)
def train_remote(
    dataset_bytes: bytes,
    output_dir_name: str = "bagley-v9-modal",
    epochs: int = 3,
    batch_size: int = 4,
    grad_accum: int = 4,
    max_seq_len: int = 1024,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lr: float = 2e-4,
    seed: int = 42,
) -> dict:
    import json
    import pathlib
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer
    from datasets import load_dataset
    from huggingface_hub import snapshot_download

    # ---- write dataset to volume ----
    data_path = pathlib.Path("/vol/dataset.jsonl")
    data_path.write_bytes(dataset_bytes)
    print(f"[modal] dataset written: {data_path} ({len(dataset_bytes)/1024/1024:.2f} MB)")

    # ---- download base model if not cached ----
    base_dir = pathlib.Path("/vol/foundation-sec-8b")
    if not (base_dir / "config.json").exists():
        print("[modal] downloading Foundation-Sec-8B from HF (one-time, ~16 GB)")
        snapshot_download(
            "fdtn-ai/Foundation-Sec-8B",
            local_dir=str(base_dir),
            token=os.getenv("HF_TOKEN"),
        )
        volume.commit()
    else:
        print(f"[modal] base model cached at {base_dir}")

    # ---- tokenizer ----
    tok = AutoTokenizer.from_pretrained(str(base_dir))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    if not getattr(tok, "chat_template", None):
        tok.chat_template = (
            "{% for m in messages %}"
            "<|im_start|>{{ m['role'] }}\n{{ m['content'] }}<|im_end|>\n"
            "{% endfor %}"
            "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
        )

    # ---- 4-bit quant base ----
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(base_dir),
        quantization_config=bnb,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)

    lora = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    # ---- dataset ----
    ds = load_dataset("json", data_files=str(data_path), split="train")
    print(f"[modal] train examples: {len(ds)}")

    out_dir = pathlib.Path("/vol/runs") / output_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    sft = SFTConfig(
        output_dir=str(out_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        weight_decay=0.0,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        bf16=True,
        gradient_checkpointing=False,
        optim="paged_adamw_8bit",
        max_seq_length=max_seq_len,
        packing=True,   # H100 aguenta packing; +20 % throughput
        report_to="none",
        seed=seed,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft,
        train_dataset=ds,
        processing_class=tok,
    )
    trainer.train()
    trainer.save_model(str(out_dir))
    tok.save_pretrained(str(out_dir))
    volume.commit()

    metrics = trainer.state.log_history[-1] if trainer.state.log_history else {}
    return {
        "output_dir": str(out_dir),
        "train_runtime": metrics.get("train_runtime"),
        "train_loss": metrics.get("train_loss"),
    }


# ---------------------------------------------------------------------------
# Artifact download
# ---------------------------------------------------------------------------

@app.function(volumes={"/vol": volume})
def download_adapter(remote_dir: str) -> dict[str, bytes]:
    import pathlib
    out: dict[str, bytes] = {}
    root = pathlib.Path("/vol/runs") / remote_dir
    for p in root.rglob("*"):
        if p.is_file() and p.stat().st_size < 500 * 1024 * 1024:
            out[str(p.relative_to(root))] = p.read_bytes()
    return out


# ---------------------------------------------------------------------------
# Eval function on H100
# ---------------------------------------------------------------------------

eval_image = (
    image
    .add_local_file(str(LOCAL_ROOT / "scripts" / "eval_bagley.py"),
                     remote_path="/root/eval_bagley.py")
    .add_local_file(str(LOCAL_ROOT / "src" / "bagley" / "persona.py"),
                     remote_path="/root/bagley/persona.py")
    .add_local_file(str(LOCAL_ROOT / "src" / "bagley" / "__init__.py"),
                     remote_path="/root/bagley/__init__.py")
)


@app.function(
    image=eval_image,
    gpu="H100",
    volumes={"/vol": volume},
    timeout=2 * 3600,
)
def eval_remote(adapter_dir_name: str = "bagley-v9-modal") -> dict:
    import sys
    import json as _json
    import pathlib
    sys.path.insert(0, "/root")
    import eval_bagley as eb

    base_dir = pathlib.Path("/vol/foundation-sec-8b")
    adapter_dir = pathlib.Path("/vol/runs") / adapter_dir_name
    out_dir = pathlib.Path("/vol/runs") / f"eval-{adapter_dir_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    orig_argv = sys.argv
    sys.argv = ["eval_bagley.py",
                "--adapter", str(adapter_dir),
                "--base", str(base_dir),
                "--out-dir", str(out_dir)]
    try:
        eb.main()
    finally:
        sys.argv = orig_argv

    volume.commit()

    scores_path = out_dir / "scores.json"
    if scores_path.exists():
        return _json.loads(scores_path.read_text(encoding="utf-8"))["aggregate"]
    return {"error": "scores.json not found"}


merge_image = (
    image
    .apt_install("git", "build-essential", "cmake", "curl", "libcurl4-openssl-dev")
    .pip_install("gguf>=0.10.0", "numpy<2")
    .run_commands(
        "git clone --depth 1 https://github.com/ggerganov/llama.cpp /opt/llama.cpp",
        "cd /opt/llama.cpp && cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF && cmake --build build --config Release -j --target llama-quantize",
    )
)


@app.function(
    image=merge_image,
    gpu="H100",
    volumes={"/vol": volume},
    timeout=2 * 3600,
)
def merge_and_export(
    adapter_dir_name: str = "bagley-v9-modal",
    quant: str = "Q4_K_M",
) -> dict:
    import subprocess
    import pathlib
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_dir = pathlib.Path("/vol/foundation-sec-8b")
    adapter_dir = pathlib.Path("/vol/runs") / adapter_dir_name
    merged_dir = pathlib.Path("/vol/runs") / f"{adapter_dir_name}-merged"
    gguf_f16 = pathlib.Path("/vol/runs") / f"{adapter_dir_name}-f16.gguf"
    gguf_q = pathlib.Path("/vol/runs") / f"{adapter_dir_name}-{quant}.gguf"

    print(f"[modal] loading base + adapter")
    base = AutoModelForCausalLM.from_pretrained(
        str(base_dir),
        torch_dtype=torch.bfloat16,
        device_map="cuda:0",
    )
    m = PeftModel.from_pretrained(base, str(adapter_dir))
    print(f"[modal] merging LoRA into base")
    merged = m.merge_and_unload()
    merged.save_pretrained(str(merged_dir), safe_serialization=True)
    AutoTokenizer.from_pretrained(str(base_dir)).save_pretrained(str(merged_dir))
    del merged, m, base
    torch.cuda.empty_cache()

    print(f"[modal] converting HF → GGUF f16")
    subprocess.run([
        "python", "/opt/llama.cpp/convert_hf_to_gguf.py",
        str(merged_dir),
        "--outfile", str(gguf_f16),
        "--outtype", "f16",
    ], check=True)

    print(f"[modal] quantizing {quant}")
    subprocess.run([
        "/opt/llama.cpp/build/bin/llama-quantize",
        str(gguf_f16), str(gguf_q), quant,
    ], check=True)

    gguf_f16.unlink(missing_ok=True)   # economiza storage

    volume.commit()
    return {
        "merged_dir": str(merged_dir),
        "gguf_quantized": str(gguf_q),
        "size_bytes": gguf_q.stat().st_size,
    }


@app.function(volumes={"/vol": volume}, timeout=1800)
def download_gguf(gguf_name: str) -> bytes:
    import pathlib
    p = pathlib.Path("/vol/runs") / gguf_name
    return p.read_bytes()


@app.function(volumes={"/vol": volume})
def download_eval(remote_dir: str) -> dict[str, bytes]:
    import pathlib
    out: dict[str, bytes] = {}
    root = pathlib.Path("/vol/runs") / f"eval-{remote_dir}"
    if not root.exists():
        return {}
    for p in root.rglob("*"):
        if p.is_file() and p.stat().st_size < 200 * 1024 * 1024:
            out[str(p.relative_to(root))] = p.read_bytes()
    return out


# ---------------------------------------------------------------------------
# Local entry point
# ---------------------------------------------------------------------------

@app.local_entrypoint()
def eval_v9():
    """Roda eval_bagley.py na H100 sobre o adapter v9 já no Volume."""
    print("[local] launching eval on H100...")
    agg = eval_remote.remote("bagley-v9-modal")
    print(f"[local] eval aggregate: {agg}")

    out_local = LOCAL_ROOT / "runs" / "eval-v9"
    out_local.mkdir(parents=True, exist_ok=True)
    files = download_eval.remote("bagley-v9-modal")
    for rel, content in files.items():
        dst = out_local / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
        print(f"  {rel} ({len(content)/1024:.0f} KB)")
    print(f"[local] eval ready: {out_local}")


@app.local_entrypoint()
def train_v10():
    """Trainamento v10: dataset_v10.jsonl (5501 v9 + corpus_v10 + 20% OpenHermes), 4 epochs."""
    dataset_path = LOCAL_ROOT / "data" / "dataset_v10.jsonl"
    if not dataset_path.exists():
        print(f"[local] ERRO: {dataset_path} não existe. Rode scripts/build_dataset_v10.py primeiro.")
        return
    print(f"[local] reading {dataset_path}")
    data = dataset_path.read_bytes()
    print(f"[local] dataset size: {len(data)/1024/1024:.2f} MB")

    print("[local] launching remote train on H100...")
    result = train_remote.remote(
        dataset_bytes=data,
        output_dir_name="bagley-v10-modal",
        epochs=4,
        batch_size=4,
        grad_accum=4,
    )
    print(f"[local] train done: {result}")

    out_local = LOCAL_ROOT / "runs" / "bagley-v10-modal"
    out_local.mkdir(parents=True, exist_ok=True)
    files = download_adapter.remote("bagley-v10-modal")
    for rel, content in files.items():
        dst = out_local / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
        print(f"  {rel} ({len(content)/1024:.0f} KB)")
    print(f"[local] adapter ready: {out_local}")


@app.local_entrypoint()
def eval_v10():
    print("[local] launching eval v10 on H100...")
    agg = eval_remote.remote("bagley-v10-modal")
    print(f"[local] eval aggregate: {agg}")
    out_local = LOCAL_ROOT / "runs" / "eval-v10"
    out_local.mkdir(parents=True, exist_ok=True)
    files = download_eval.remote("bagley-v10-modal")
    for rel, content in files.items():
        dst = out_local / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
    print(f"[local] eval ready: {out_local}")


@app.local_entrypoint()
def export_v9(quant: str = "Q4_K_M"):
    """Merge adapter + base, converte GGUF, quantiza, baixa pra local."""
    print(f"[local] launching merge_and_export on H100 (quant={quant})")
    info = merge_and_export.remote("bagley-v9-modal", quant)
    print(f"[local] export done: {info}")

    gguf_name = f"bagley-v9-modal-{quant}.gguf"
    out_path = LOCAL_ROOT / "runs" / gguf_name
    print(f"[local] downloading {gguf_name} ({info['size_bytes']/1024/1024:.0f} MB)")
    data = download_gguf.remote(gguf_name)
    out_path.write_bytes(data)
    print(f"[local] GGUF ready: {out_path}")


@app.local_entrypoint()
def pull_v10():
    """Baixa adapter v10 do Modal Volume após train concluir na cloud."""
    print(f"[local] downloading adapter bagley-v10-modal")
    out_local = LOCAL_ROOT / "runs" / "bagley-v10-modal"
    out_local.mkdir(parents=True, exist_ok=True)
    files = download_adapter.remote("bagley-v10-modal")
    for rel, content in files.items():
        dst = out_local / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
        print(f"  {rel} ({len(content)/1024:.0f} KB)")
    print(f"[local] adapter ready: {out_local}")


@app.local_entrypoint()
def pull_eval_v10():
    """Baixa resultados de eval-v10 do Modal Volume."""
    out_local = LOCAL_ROOT / "runs" / "eval-v10"
    out_local.mkdir(parents=True, exist_ok=True)
    files = download_eval.remote("bagley-v10-modal")
    for rel, content in files.items():
        dst = out_local / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
        print(f"  {rel} ({len(content)/1024:.0f} KB)")
    print(f"[local] eval ready: {out_local}")


@app.local_entrypoint()
def pull_v9():
    """Baixa adapter já treinado do Modal Volume pra máquina local.

    Uso: modal run scripts/modal_train.py::pull_v9
    """
    print(f"[local] downloading adapter to {LOCAL_OUT}")
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)
    files = download_adapter.remote("bagley-v9-modal")
    for rel, content in files.items():
        dst = LOCAL_OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
        print(f"  {rel} ({len(content)/1024:.0f} KB)")
    print(f"[local] adapter ready: {LOCAL_OUT}")


@app.local_entrypoint()
def train_v9():
    print(f"[local] reading dataset from {LOCAL_DATASET}")
    data = LOCAL_DATASET.read_bytes()
    print(f"[local] dataset size: {len(data)/1024/1024:.2f} MB")

    print("[local] launching remote train on H100...")
    result = train_remote.remote(
        dataset_bytes=data,
        output_dir_name="bagley-v9-modal",
        epochs=3,
    )
    print(f"[local] train done: {result}")

    print(f"[local] downloading adapter to {LOCAL_OUT}")
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)
    files = download_adapter.remote("bagley-v9-modal")
    for rel, content in files.items():
        dst = LOCAL_OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
        print(f"  {rel} ({len(content)/1024:.0f} KB)")
    print(f"[local] adapter ready: {LOCAL_OUT}")
