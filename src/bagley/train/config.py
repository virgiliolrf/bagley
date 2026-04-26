"""Hiperparâmetros QLoRA. Calibrado pra RTX 5070 (12GB VRAM) + Foundation-Sec-8B."""

from dataclasses import dataclass, field


@dataclass
class BagleyTrainConfig:
    base_model_id: str = "./models/foundation-sec-8b"
    output_dir: str = "./runs/bagley-v0"
    dataset_path: str = "./data/dataset.jsonl"

    # 4-bit quant
    load_in_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_use_double_quant: bool = True

    # LoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: tuple[str, ...] = (
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    )

    # Training — conservador pra 12GB VRAM. Ajustar depois do primeiro dry-run.
    max_seq_len: int = 1024
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 16
    learning_rate: float = 2e-4
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.03
    num_train_epochs: int = 3
    weight_decay: float = 0.0
    logging_steps: int = 5
    save_steps: int = 100
    save_total_limit: int = 2
    gradient_checkpointing: bool = True
    optim: str = "paged_adamw_8bit"
    bf16: bool = True
    seed: int = 42

    # Anti-forgetting: mix genérico
    generic_mix_ratio: float = 0.2

    # Dry-run: limita steps pra validar pipeline
    max_steps: int | None = None  # None = treino completo; setar pra dry-run


DEFAULT = BagleyTrainConfig()
