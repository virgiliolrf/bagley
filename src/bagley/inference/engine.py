"""Inference engine: local (transformers + PeftModel) ou Ollama HTTP."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import httpx


@dataclass
class Reply:
    text: str                     # texto completo do assistant (inclui tool_calls inline)


# ===========================================================================
# LocalEngine — carrega base + LoRA via transformers/peft
# ===========================================================================

class LocalEngine:
    def __init__(self, base: str, adapter: str, quant_4bit: bool = True) -> None:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.tokenizer = AutoTokenizer.from_pretrained(adapter)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        kwargs: dict = {"device_map": "auto", "torch_dtype": torch.bfloat16}
        if quant_4bit:
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
        model = AutoModelForCausalLM.from_pretrained(base, **kwargs)
        self.model = PeftModel.from_pretrained(model, adapter)
        self.model.eval()

        # Stop ids: EOS + <|im_end|>
        self._stop_ids = [self.tokenizer.eos_token_id]
        im_end = self.tokenizer.convert_tokens_to_ids("<|im_end|>")
        if im_end != self.tokenizer.unk_token_id and im_end is not None:
            self._stop_ids.append(im_end)

    def generate(self, messages: list[dict], *,
                 max_new_tokens: int = 512, temperature: float = 0.7,
                 top_p: float = 0.9, repetition_penalty: float = 1.1) -> Reply:
        import torch
        input_ids = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True,
            return_tensors="pt", return_dict=False,
        ).to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                input_ids, max_new_tokens=max_new_tokens, do_sample=True,
                temperature=temperature, top_p=top_p,
                repetition_penalty=repetition_penalty,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self._stop_ids,
            )
        text = self.tokenizer.decode(
            out[0][input_ids.shape[1]:], skip_special_tokens=True
        ).strip()
        # Remove trailing <|im_end|> se vazou por `skip_special_tokens` inconsistente
        text = text.replace("<|im_end|>", "").strip()
        return Reply(text=text)


# ===========================================================================
# OllamaEngine — fallback / produção rápida
# ===========================================================================

import os as _os


def _default_ollama_host() -> str:
    return _os.getenv("OLLAMA_HOST", "http://localhost:11434")


@dataclass
class OllamaEngine:
    model: str = "bagley"
    host: str = field(default_factory=_default_ollama_host)
    timeout: float = 180.0

    def generate(self, messages: list[dict], **kwargs) -> Reply:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.host}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
        text = data.get("message", {}).get("content", "").strip()
        return Reply(text=text)


def stub_response(user: str) -> Reply:
    lower = user.lower()
    if "scan" in lower or "nmap" in lower:
        return Reply(text="Let me have a go.\n<tool_call>{\"name\":\"shell\",\"arguments\":{\"cmd\":\"nmap -sC -sV 10.10.10.10\"}}</tool_call>")
    return Reply(text="Stub mode — connect a real engine to get somewhere.")
