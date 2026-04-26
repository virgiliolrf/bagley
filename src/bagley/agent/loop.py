"""ReAct loop do Bagley.

Fluxo:
    user → model.generate → se tool_call → confirmar → executar → devolver como tool message → model.generate → ...
    até o model responder sem tool_call (resposta final).

Segurança:
- check_all (blocklist destrutivos + scope se declarado) ANTES de execução
- confirmação user-in-the-loop opcional
- audit log de tudo
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from bagley.agent.executor import Execution, confirm as default_confirm, execute, execute_with_stream
from bagley.agent.parser import ToolCall, extract, strip_tool_calls
from bagley.agent.safeguards import Scope


@dataclass
class LoopStep:
    kind: str            # "assistant" | "tool" | "final" | "blocked"
    content: str
    tool_call: ToolCall | None = None
    execution: Execution | None = None


@dataclass
class ReActLoop:
    engine: object                     # LocalEngine | OllamaEngine (duck-typed)
    scope: Scope | None = None
    auto_approve: bool = False         # se True, não pede [Y/n]
    max_steps: int = 8
    confirm_fn: Callable[[str], bool] = None  # type: ignore[assignment]
    history: list[dict] = field(default_factory=list)
    commentator: object = None         # StreamCommentator opcional
    stream: bool = False               # True = usa PTY tap (commentator fala em real-time)
    disable_safeguard: bool = False    # True = bypass blocklist destrutivos (operator takes responsibility)

    def __post_init__(self):
        if self.confirm_fn is None:
            self.confirm_fn = (lambda cmd: True) if self.auto_approve else default_confirm

    def run(self, user_msg: str, system: str) -> list[LoopStep]:
        if not self.history:
            self.history.append({"role": "system", "content": system})
        self.history.append({"role": "user", "content": user_msg})

        steps: list[LoopStep] = []
        for _ in range(self.max_steps):
            reply = self.engine.generate(self.history)
            self.history.append({"role": "assistant", "content": reply.text})

            calls = extract(reply.text)
            prose = strip_tool_calls(reply.text)

            if not calls:
                steps.append(LoopStep(kind="final", content=prose or reply.text))
                return steps

            if prose:
                steps.append(LoopStep(kind="assistant", content=prose))

            # Executa primeiro tool_call; resto é ignorado (uma ferramenta por step)
            call = calls[0]
            if call.name != "shell":
                steps.append(LoopStep(kind="blocked", content=f"tool '{call.name}' não suportado",
                                      tool_call=call))
                self.history.append({
                    "role": "tool",
                    "content": f"[error] tool '{call.name}' not supported; only 'shell' is wired up",
                })
                continue

            cmd = call.arguments.get("cmd", "")
            if self.stream and self.commentator is not None:
                on_line = lambda ln, _cmd=cmd: self.commentator.on_line(ln, context=_cmd)
                exec_result = execute_with_stream(
                    cmd, scope=self.scope, confirm_fn=self.confirm_fn, on_line=on_line,
                    disable_safeguard=self.disable_safeguard,
                )
            else:
                exec_result = execute(
                    cmd, scope=self.scope, confirm_fn=self.confirm_fn,
                    disable_safeguard=self.disable_safeguard,
                )
            output = self._format_output(exec_result)
            steps.append(LoopStep(kind="tool", content=output, tool_call=call,
                                  execution=exec_result))
            self.history.append({"role": "tool", "content": output})

            if exec_result.blocked:
                # modelo pode continuar com explicação, ou podemos parar. Deixamos continuar.
                pass

        # Passou do max_steps sem terminar
        steps.append(LoopStep(kind="final",
                              content="[loop reached max_steps — stopping]"))
        return steps

    def _format_output(self, ex: Execution) -> str:
        if ex.blocked:
            return f"[blocked] {ex.reason}"
        parts = []
        if ex.stdout:
            parts.append(ex.stdout.strip())
        if ex.stderr:
            parts.append(f"[stderr]\n{ex.stderr.strip()}")
        if ex.returncode != 0 and not ex.stdout and not ex.stderr:
            parts.append(f"[exit={ex.returncode}, no output]")
        text = "\n".join(parts).strip()
        # Limita output pra não estourar context window
        if len(text) > 4000:
            text = text[:2000] + "\n... [truncated] ...\n" + text[-1500:]
        return text or "[no output]"
