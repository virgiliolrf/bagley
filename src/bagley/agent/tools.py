"""Wrappers leves para ferramentas Kali. Apenas monta comando — execução passa pelo executor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tool:
    name: str
    binary: str
    build: callable  # type: ignore[type-arg]


def nmap_cmd(target: str, *, fast: bool = False, scripts: bool = True) -> str:
    flags = "-sS -T4 -F" if fast else "-sC -sV"
    return f"nmap {flags} {target}".strip() if scripts else f"nmap {flags.replace('-sC ', '')} {target}".strip()


def gobuster_dir(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt") -> str:
    return f"gobuster dir -u {url} -w {wordlist}"


def hydra_ssh(user: str, target: str, wordlist: str = "/usr/share/wordlists/rockyou.txt") -> str:
    return f"hydra -l {user} -P {wordlist} ssh://{target}"


def nikto_scan(url: str) -> str:
    return f"nikto -h {url}"


def ffuf_fuzz(url_with_fuzz: str, wordlist: str = "/usr/share/wordlists/SecLists/Discovery/Web-Content/common.txt") -> str:
    return f"ffuf -u '{url_with_fuzz}' -w {wordlist} -mc 200,302"


TOOLS: dict[str, Tool] = {
    "nmap": Tool("nmap", "nmap", nmap_cmd),
    "gobuster": Tool("gobuster", "gobuster", gobuster_dir),
    "hydra": Tool("hydra", "hydra", hydra_ssh),
    "nikto": Tool("nikto", "nikto", nikto_scan),
    "ffuf": Tool("ffuf", "ffuf", ffuf_fuzz),
}
