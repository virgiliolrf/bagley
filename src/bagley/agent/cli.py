"""REPL do Bagley — ReAct loop com tool execution ao vivo.

Uso:
    bagley                                    # usa LocalEngine com adapter padrão
    bagley --adapter runs/bagley-v7           # adapter específico
    bagley --ollama                           # usa Ollama em localhost
    bagley --scope 10.10.0.0/16               # limita targets
    bagley --scope 192.168.56.0/24 --scope 10.10.0.0/16
    bagley --auto                             # sem confirmação [Y/n] (perigoso)

Slash commands no REPL:
    /exit /quit /q     — sair
    /reset             — limpar history
    /scope <cidrs...>  — atualizar scope
    /last              — reimprimir output completo do último tool
    /help              — listar comandos
"""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.traceback import Traceback

from bagley.agent.loop import ReActLoop
from bagley.agent.safeguards import Scope
from bagley.inference.engine import LocalEngine, OllamaEngine, stub_response
from bagley.persona import DEFAULT_SYSTEM

app = typer.Typer(add_completion=False)
console = Console()


SLASH_COMMANDS = {
    "/exit": "disconnect",
    "/quit": "disconnect",
    "/q": "disconnect",
    "/reset": "clear conversation history",
    "/scope": "update scope: /scope <cidr|host>...",
    "/last": "reprint last tool output in full (no truncation)",
    "/help": "show this help",
}

HISTORY_PATH = Path(".bagley") / "repl_history"


def _build_engine(adapter: str | None, base: str, ollama: bool, ollama_model: str, stub: bool):
    if stub:
        class StubEngine:
            def generate(self, messages, **kwargs):
                last = next((m for m in reversed(messages) if m["role"] == "user"), None)
                return stub_response(last["content"] if last else "")
        return StubEngine()
    if ollama:
        return OllamaEngine(model=ollama_model)
    return LocalEngine(base=base, adapter=adapter or "runs/bagley-v7")


def _parse_scope(scopes: list[str]) -> Scope | None:
    if not scopes:
        return None
    cidrs: list[str] = []
    hostnames: set[str] = set()
    for s in scopes:
        s = s.strip()
        if "/" in s or all(p.isdigit() or p == "." for p in s if p):
            if "/" not in s:
                s = s + "/32"
            cidrs.append(s)
        else:
            hostnames.add(s.lower())
    return Scope(cidrs=tuple(cidrs), hostnames=frozenset(hostnames))


def _detect_lexer(cmd: str) -> str:
    first = cmd.strip().split(None, 1)[0] if cmd.strip() else ""
    first = first.lower().lstrip("./")
    python_bins = {"python", "python3", "python.exe", "py"}
    if first in python_bins:
        return "python"
    sql_bins = {"sqlmap"}
    if first in sql_bins or "select " in cmd.lower()[:20]:
        return "sql"
    if first in {"curl", "wget", "http", "httpie"}:
        return "bash"
    return "bash"


def _detect_os() -> dict:
    sysname = platform.system()                       # Windows | Linux | Darwin
    release = platform.release()
    shell = "cmd.exe" if sysname == "Windows" else ("/bin/sh")
    eof_key = "Ctrl+Z, Enter" if sysname == "Windows" else "Ctrl+D"
    distro = ""
    if sysname == "Linux":
        # tenta ler /etc/os-release pra identificar Kali/Ubuntu/etc
        try:
            txt = Path("/etc/os-release").read_text()
            for line in txt.splitlines():
                if line.startswith("PRETTY_NAME="):
                    distro = line.split("=", 1)[1].strip().strip('"')
                    break
        except Exception:
            distro = ""
    return {
        "system": sysname,
        "release": release,
        "distro": distro,
        "shell": shell,
        "eof": eof_key,
        "pty_stream": sysname != "Windows",   # PTY stream só Unix
    }


def _check_recon_tools() -> dict:
    """Check presence of tools Bagley typically invokes. Returns dict name->bool."""
    tools = ["nmap", "curl", "nc", "ncat", "sqlmap", "gobuster", "ffuf", "hydra",
             "nikto", "whatweb", "dig", "whois", "openssl"]
    return {t: shutil.which(t) is not None for t in tools}


def _print_banner(console: Console, os_info: dict) -> None:
    body = (
        f"[bold cyan]Bagley[/] online — [bold]/exit[/] or [bold]{os_info['eof']}[/] to disconnect.\n"
        f"[dim]os={os_info['system']} {os_info['release']}"
        f"{' · ' + os_info['distro'] if os_info['distro'] else ''}"
        f" · shell={os_info['shell']} · Type /help for commands.[/]"
    )
    console.print(Panel(body, border_style="cyan"))


def _print_help(console: Console) -> None:
    body = "\n".join(f"  [bold cyan]{k:<8}[/] — {v}" for k, v in SLASH_COMMANDS.items())
    console.print(Panel(body, title="slash commands", border_style="cyan"))


def _print_scope(console: Console, scope_obj: Scope | None) -> None:
    if scope_obj:
        body = (
            f"cidrs: [green]{list(scope_obj.cidrs) or '[]'}[/]\n"
            f"hosts: [green]{list(scope_obj.hostnames) or '[]'}[/]\n"
            f"allow_any_rfc1918: [green]{scope_obj.allow_any_rfc1918}[/]"
        )
        console.print(Panel(body, title="scope", border_style="green"))
    else:
        console.print(Panel(
            "[bold red]NO SCOPE DECLARED[/] — every IP-bearing command will be blocked.\n"
            "Use [bold]--scope <cidr>[/] on launch or [bold]/scope <cidr>[/] in REPL.",
            border_style="red", title="scope",
        ))


def _print_statusline(console: Console, engine_label: str, scope_obj: Scope | None,
                       auto: bool, safeguard_off: bool, turn: int, os_name: str) -> None:
    scope_txt = (
        f"scope=[green]{len(scope_obj.cidrs)}cidr/{len(scope_obj.hostnames)}host[/]"
        if scope_obj else "scope=[red]none[/]"
    )
    auto_txt = "auto=[red]on[/]" if auto else "auto=off"
    sg_txt = "safeguard=[red]OFF[/]" if safeguard_off else "safeguard=on"
    os_txt = f"os=[cyan]{os_name.lower()}[/]"
    console.rule(
        f"[dim]turn {turn} | {engine_label} | {os_txt} | {scope_txt} | {auto_txt} | {sg_txt}[/]",
        style="dim",
    )


def _print_step(step, console: Console, last_tool_full: dict) -> None:
    if step.kind == "assistant":
        console.print(f"[bold magenta]bagley>[/] {step.content}")
    elif step.kind == "tool":
        if step.execution and step.execution.blocked:
            console.print(Panel(
                f"[red]BLOCKED[/]: {step.execution.reason}",
                title="tool result", border_style="red",
            ))
            return
        cmd = step.tool_call.arguments.get("cmd", "") if step.tool_call else ""
        lexer = _detect_lexer(cmd)
        console.print(Panel(
            Syntax(cmd, lexer, theme="monokai", line_numbers=False, word_wrap=True),
            title=f"[bold]tool call[/] ({lexer})", border_style="blue",
        ))
        full = step.content
        last_tool_full["content"] = full
        last_tool_full["rc"] = step.execution.returncode if step.execution else None
        lines = full.splitlines()
        hidden = 0
        if len(lines) > 40:
            displayed = "\n".join(lines[:30] + ["..."] + lines[-8:])
            hidden = len(lines) - 38
        elif len(full) > 2000:
            displayed = full[:1500] + "\n...\n" + full[-400:]
            hidden = -1  # flag: truncated by chars
        else:
            displayed = full
        rc = step.execution.returncode if step.execution else "?"
        title = f"exit={rc}"
        if hidden > 0:
            title += f"  [dim](+{hidden} lines hidden — /last for full)[/]"
        elif hidden < 0:
            title += "  [dim](truncated — /last for full)[/]"
        console.print(Panel(
            displayed,
            title=title,
            border_style="green" if rc == 0 else "yellow",
        ))
    elif step.kind == "blocked":
        console.print(f"[red]blocked:[/] {step.content}")
    elif step.kind == "final":
        console.print(f"[bold magenta]bagley>[/] {step.content}")


def _make_confirm(console: Console):
    """Rich-styled confirmation — panel com cmd, depois prompt."""
    def confirm(command: str) -> bool:
        console.print(Panel(
            Syntax(command, _detect_lexer(command), theme="monokai", word_wrap=True),
            title="[bold yellow]about to execute[/]", border_style="yellow",
        ))
        try:
            ans = console.input("[bold yellow]run? [y/N]:[/] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return ans in {"y", "yes", "s", "sim"}
    return confirm


@app.command()
def main(
    adapter: str | None = typer.Option(None, "--adapter", help="Path do LoRA adapter."),
    base: str = typer.Option("./models/foundation-sec-8b", "--base", help="Base model path."),
    ollama: bool = typer.Option(False, "--ollama", help="Usa Ollama HTTP em vez de transformers local."),
    ollama_model: str = typer.Option("bagley", "--ollama-model"),
    stub: bool = typer.Option(False, "--stub", help="Modo mock sem modelo."),
    scope: list[str] = typer.Option(
        [], "--scope", "-s",
        help="CIDR ou hostname permitido. Pode repetir. Sem --scope, executor bloqueia qualquer IP.",
    ),
    allow_rfc1918: bool = typer.Option(False, "--allow-rfc1918",
        help="Atalho: permite qualquer RFC1918 (labs)."),
    auto: bool = typer.Option(False, "--auto", help="Sem confirmação [Y/n] antes de executar. CUIDADO."),
    max_steps: int = typer.Option(8, "--max-steps"),
    disable_safeguard: bool = typer.Option(False, "--disable-runtime-safeguard",
        help="⚠️  BYPASS do blocklist de destrutivos (rm -rf /, mkfs, dd, fork bomb). Você assume 100% da responsabilidade."),
) -> None:
    os_info = _detect_os()
    _print_banner(console, os_info)

    if os_info["system"] == "Windows":
        console.print(Panel(
            "[yellow]Running on Windows.[/] Recon tooling (nmap, sqlmap, gobuster, hydra...) "
            "typically absent — shell is cmd.exe, PTY streaming disabled "
            "(fallback to post-exec capture). For live engagements, deploy on Linux (Kali).",
            border_style="yellow", title="dev-host notice",
        ))
    else:
        tools = _check_recon_tools()
        missing = [t for t, ok in tools.items() if not ok]
        present = [t for t, ok in tools.items() if ok]
        color = "green" if len(present) >= 5 else "yellow"
        console.print(Panel(
            f"[{color}]{len(present)}/{len(tools)} tools found[/] — "
            f"present: [green]{', '.join(present) or 'none'}[/]"
            + (f"\nmissing: [yellow]{', '.join(missing)}[/]" if missing else ""),
            border_style=color, title="recon tools",
        ))

    if disable_safeguard:
        console.print(Panel(
            "[bold red]⚠️  RUNTIME SAFEGUARD DISABLED ⚠️[/]\n\n"
            "Destructive blocklist is OFF. `rm -rf /`, `mkfs`, `dd of=/dev/sd*`, fork bombs\n"
            "will execute if the model proposes them and you confirm (or --auto is on).\n"
            "Every command is logged with [SAFEGUARD_OFF] in audit log.",
            border_style="red", title="WARNING",
        ))

    scope_obj = _parse_scope(scope)
    if scope_obj and allow_rfc1918:
        scope_obj = Scope(cidrs=scope_obj.cidrs, hostnames=scope_obj.hostnames,
                          allow_any_rfc1918=True)
    elif allow_rfc1918:
        scope_obj = Scope(allow_any_rfc1918=True)
    _print_scope(console, scope_obj)

    engine_label = (
        "stub" if stub
        else f"ollama:{ollama_model}" if ollama
        else f"local:{(adapter or 'runs/bagley-v7').split('/')[-1]}"
    )

    with console.status(f"[cyan]loading engine ({engine_label})...", spinner="dots"):
        try:
            engine = _build_engine(adapter, base, ollama, ollama_model, stub)
        except Exception as exc:
            console.print(Panel(
                Traceback.from_exception(type(exc), exc, exc.__traceback__, show_locals=False),
                title="[red]engine load failed[/]", border_style="red",
            ))
            raise typer.Exit(1)

    from bagley.observe.commentator import StreamCommentator, CommentaryConfig
    commentator = StreamCommentator(engine=engine, tts=None,
                                    cfg=CommentaryConfig(min_interval_s=3.0))

    loop = ReActLoop(
        engine=engine, scope=scope_obj, auto_approve=auto,
        max_steps=max_steps, commentator=commentator, stream=True,
        disable_safeguard=disable_safeguard,
        confirm_fn=None if auto else _make_confirm(console),
    )

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if sys.stdin.isatty():
        session = PromptSession(
            history=FileHistory(str(HISTORY_PATH)),
            completer=WordCompleter(list(SLASH_COMMANDS.keys()), ignore_case=True),
            complete_while_typing=False,
        )
        def _read_input() -> str:
            return session.prompt(HTML("<ansigreen><b>you&gt; </b></ansigreen>")).strip()
    else:
        def _read_input() -> str:
            return console.input("[bold green]you> [/]").strip()

    last_tool_full: dict = {"content": "", "rc": None}
    turn = 0

    _print_help(console)

    while True:
        turn += 1
        _print_statusline(console, engine_label, loop.scope, auto, disable_safeguard, turn,
                          os_info["system"])
        try:
            user = _read_input()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]disconnecting.[/]")
            return
        if not user:
            turn -= 1
            continue
        if user in {"/exit", "/quit", "/q"}:
            return
        if user == "/help":
            _print_help(console)
            turn -= 1
            continue
        if user == "/reset":
            loop.history.clear()
            console.print("[dim]history cleared.[/]")
            turn = 0
            continue
        if user == "/last":
            if not last_tool_full["content"]:
                console.print("[dim]no previous tool output.[/]")
            else:
                console.print(Panel(
                    last_tool_full["content"],
                    title=f"last tool output (exit={last_tool_full['rc']})",
                    border_style="cyan",
                ))
            turn -= 1
            continue
        if user.startswith("/scope"):
            parts = user.split()[1:]
            loop.scope = _parse_scope(parts) if parts else None
            _print_scope(console, loop.scope)
            turn -= 1
            continue
        if user.startswith("/"):
            console.print(f"[red]unknown command:[/] {user}  — try /help")
            turn -= 1
            continue

        try:
            with console.status("[magenta]bagley thinking...", spinner="dots"):
                steps = loop.run(user, DEFAULT_SYSTEM)
        except Exception as exc:
            console.print(Panel(
                Traceback.from_exception(type(exc), exc, exc.__traceback__, show_locals=False),
                title="[red]loop error[/]", border_style="red",
            ))
            continue
        for step in steps:
            _print_step(step, console, last_tool_full)


if __name__ == "__main__":
    app()
