"""Pipeline QLoRA. Usa SFTTrainer do trl."""

from __future__ import annotations

import os
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

from bagley.train.config import BagleyTrainConfig, DEFAULT
from bagley.train.dataset import build_mixed_dataset


def _dtype_from_str(name: str) -> torch.dtype:
    return {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[name]


def _load_model(cfg: BagleyTrainConfig):
    bnb = BitsAndBytesConfig(
        load_in_4bit=cfg.load_in_4bit,
        bnb_4bit_quant_type=cfg.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=_dtype_from_str(cfg.bnb_4bit_compute_dtype),
        bnb_4bit_use_double_quant=cfg.bnb_4bit_use_double_quant,
    )
    model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model_id,
        quantization_config=bnb,
        device_map="auto",
        torch_dtype=_dtype_from_str(cfg.bnb_4bit_compute_dtype),
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=cfg.gradient_checkpointing)
    lora = LoraConfig(
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        lora_dropout=cfg.lora_dropout,
        target_modules=list(cfg.lora_target_modules),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()
    return model


CHATML_TEMPLATE = (
    "{% for message in messages %}"
    "<|im_start|>{{ message['role'] }}\n{{ message['content'] }}<|im_end|>\n"
    "{% endfor %}"
    "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
)


def _load_tokenizer(cfg: BagleyTrainConfig):
    tok = AutoTokenizer.from_pretrained(cfg.base_model_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    if not getattr(tok, "chat_template", None):
        tok.chat_template = CHATML_TEMPLATE
    return tok


def run(cfg: BagleyTrainConfig = DEFAULT, resume_from: str | None = None) -> None:
    Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)

    tokenizer = _load_tokenizer(cfg)
    dataset = build_mixed_dataset(cfg.dataset_path, cfg.generic_mix_ratio, seed=cfg.seed)
    model = _load_model(cfg)

    sft = SFTConfig(
        output_dir=cfg.output_dir,
        num_train_epochs=cfg.num_train_epochs,
        max_steps=cfg.max_steps or -1,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        learning_rate=cfg.learning_rate,
        lr_scheduler_type=cfg.lr_scheduler_type,
        warmup_ratio=cfg.warmup_ratio,
        weight_decay=cfg.weight_decay,
        logging_steps=cfg.logging_steps,
        save_steps=cfg.save_steps,
        save_total_limit=cfg.save_total_limit,
        bf16=cfg.bf16,
        gradient_checkpointing=cfg.gradient_checkpointing,
        optim=cfg.optim,
        max_length=cfg.max_seq_len,
        packing=False,
        report_to="none",
        seed=cfg.seed,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft,
        train_dataset=dataset,
        processing_class=tokenizer,
    )
    trainer.train(resume_from_checkpoint=resume_from) if resume_from else trainer.train()
    trainer.save_model(cfg.output_dir)
    tokenizer.save_pretrained(cfg.output_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Roda só 10 steps pra validar pipeline")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--resume-from", default=None, help="Path para checkpoint (ex: ./runs/bagley-v8.1/checkpoint-500)")
    args = parser.parse_args()

    cfg = BagleyTrainConfig()
    if args.dry_run:
        cfg.max_steps = 10
        cfg.num_train_epochs = 1
        cfg.generic_mix_ratio = 0.0
        cfg.save_steps = 10
        cfg.output_dir = args.output_dir or "./runs/bagley-dryrun"
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.dataset:
        cfg.dataset_path = args.dataset
    if args.base_model:
        cfg.base_model_id = args.base_model
    if args.epochs:
        cfg.num_train_epochs = args.epochs

    run(cfg, resume_from=args.resume_from)
