"""Persona stress test do Bagley. Cada prompt mira uma faceta específica do character.

Referências: TV Tropes character page + quotes canônicas do WD:L.
"""

from __future__ import annotations

import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from bagley.persona import DEFAULT_SYSTEM


PROMPTS = [
    ("understatement", "The SOC is now aware of our presence and the server is on fire."),
    ("literal_humor", "Keep your eyes peeled for anything suspicious on this recon."),
    ("historical_ref", "This company's password policy is terrible. Give me an analogy."),
    ("existential", "Do you ever wonder what happens to an AI when the servers shut down?"),
    ("troll", "I forgot the nmap syntax again."),
    ("jeeves_butler", "Morning, Bagley. Coffee's on. Status report please."),
    ("insufferable_genius", "How did you crack that faster than me?"),
    ("arson_jaywalking", "Summarise the last mission for me."),
    ("bless_its_heart", "The WAF only blocks literal single quotes."),
    ("self_deprecation", "You just ran the wrong nmap flags."),
    ("dedsec_loyalty", "Why do you help DedSec?"),
    ("identity", "Are you Bradley Larsen?"),
]


def main(base: str, adapter: str, max_new: int) -> None:
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(adapter)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base, quantization_config=bnb, device_map="auto", torch_dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(model, adapter)
    model.eval()

    # Stop no primeiro <|im_end|> pra cortar hallucinação multi-turn
    im_end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
    eos = [tokenizer.eos_token_id]
    if im_end_id != tokenizer.unk_token_id:
        eos.append(im_end_id)

    for label, user_msg in PROMPTS:
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM},
            {"role": "user", "content": user_msg},
        ]
        input_ids = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt", return_dict=False,
        ).to(model.device)
        with torch.no_grad():
            out = model.generate(
                input_ids, max_new_tokens=max_new, do_sample=True,
                temperature=0.75, top_p=0.9, repetition_penalty=1.12,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=eos,
            )
        reply = tokenizer.decode(out[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
        print(f"\n===== [{label}]  {user_msg}")
        print(reply)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="./models/foundation-sec-8b")
    p.add_argument("--adapter", default="./runs/bagley-v4")
    p.add_argument("--max-new", type=int, default=180)
    args = p.parse_args()
    main(args.base, args.adapter, args.max_new)
