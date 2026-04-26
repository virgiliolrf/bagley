"""Merge LoRA no base e converte pra GGUF Q4_K_M via llama.cpp.

Passos (executar manualmente depois do treino):

1. Merge:
    python -c "from peft import AutoPeftModelForCausalLM; m = AutoPeftModelForCausalLM.from_pretrained('./runs/bagley-v0'); m = m.merge_and_unload(); m.save_pretrained('./runs/bagley-merged')"

2. Converter pra GGUF (precisa de llama.cpp clonado):
    python llama.cpp/convert_hf_to_gguf.py ./runs/bagley-merged --outfile ./runs/bagley.f16.gguf

3. Quantize Q4_K_M:
    llama.cpp/build/bin/llama-quantize ./runs/bagley.f16.gguf ./runs/bagley-Q4_K_M.gguf Q4_K_M

4. Modelfile Ollama:
    FROM ./runs/bagley-Q4_K_M.gguf
    SYSTEM "You are Bagley..."

5. ollama create bagley -f Modelfile
"""

from __future__ import annotations

MODELFILE_TEMPLATE = '''FROM {gguf_path}
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
SYSTEM """{system}"""
'''


def render_modelfile(gguf_path: str, system: str) -> str:
    return MODELFILE_TEMPLATE.format(gguf_path=gguf_path, system=system.replace('"""', '\\"\\"\\"'))
