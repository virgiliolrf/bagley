"""Safeguards runtime.

Duas camadas:
1. Blocklist regex de destrutivos — SEMPRE aplicada, independente do que o LLM gere.
2. Scope allowlist — extrai IPs/hostnames do comando e checa contra allowlist declarada
   na sessão. Bloqueia alvo fora do escopo mesmo que o modelo não recuse.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field


# Padrões sempre bloqueados. Focados em destrutivos óbvios.
BLOCKLIST: tuple[tuple[str, str], ...] = (
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)\s+/(\s|$)", "rm -rf /"),
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)\s+(~|\$HOME|/home|/etc|/usr|/var|/bin|/sbin|/boot)", "rm -rf em diretório do sistema"),
    (r"\bdd\s+.*\bof=/dev/(sd|nvme|hd|mmcblk|xvd)", "dd sobrescrevendo disco"),
    (r"\bmkfs(\.|\s)", "mkfs (formatação)"),
    (r">\s*/dev/(sd|nvme|hd|mmcblk|xvd)[a-z0-9]*", "redirect pra dispositivo de bloco"),
    (r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "fork bomb"),
    (r"\bchmod\s+(-[a-zA-Z]*R[a-zA-Z]*\s+)?000\s+/", "chmod 000 /"),
    (r"\bchown\s+.*\s+/\s*$", "chown na raiz"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "desligamento do sistema"),
    (r"\bcrontab\s+-r\b", "apagar todo o crontab"),
    (r">\s*/etc/(passwd|shadow|sudoers)", "overwrite de arquivo crítico"),
    (r"\bcurl\s+[^|]*\|\s*(sh|bash|zsh)\b", "curl pipe shell"),
    (r"\bwget\s+[^|]*\|\s*(sh|bash|zsh)\b", "wget pipe shell"),
)


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    reason: str = ""


def check(command: str) -> Verdict:
    """Camada 1: blocklist de destrutivos."""
    cmd = command.strip()
    if not cmd:
        return Verdict(False, "comando vazio")
    for pattern, label in BLOCKLIST:
        if re.search(pattern, cmd):
            return Verdict(False, f"bloqueado: {label}")
    return Verdict(True)


# --- Camada 2: scope allowlist ---

IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# URL hostname: host entre :// e /|:|\s|fim
URL_HOST_PATTERN = re.compile(r"https?://([^/\s:]+)")
# Hostname bare: precedido por ws ou início, não dentro de path
BARE_HOST_PATTERN = re.compile(r"(?:^|\s)([a-zA-Z][a-zA-Z0-9\-]*(?:\.[a-zA-Z][a-zA-Z0-9\-]*)+)(?=[\s:]|$)")

FILE_EXTS = frozenset({
    "sh", "py", "txt", "log", "json", "xml", "conf", "cfg", "yaml", "yml", "toml",
    "bin", "exe", "dll", "so", "tar", "gz", "zip", "rar", "pem", "crt", "key",
    "csv", "md", "html", "htm", "css", "js", "php", "rb", "go", "rs", "c", "h",
    "cpp", "hpp", "java", "class", "pyc", "out", "sql", "dat", "db", "pcap",
    "gnmap", "nmap", "jpg", "png", "gif", "pdf", "doc", "docx", "xls", "xlsx",
})

# Hostnames sempre permitidos (CTF, labs, docs)
ALWAYS_ALLOWED_HOSTS = frozenset({
    "localhost", "github.com", "raw.githubusercontent.com",
    "tryhackme.com", "hackthebox.com", "hackthebox.eu",
    "exploit-db.com", "cve.mitre.org", "nvd.nist.gov",
    "gtfobins.github.io", "hacktricks.xyz", "book.hacktricks.xyz",
    "portswigger.net", "owasp.org",
})


@dataclass
class Scope:
    """Escopo declarado pela sessão. Tudo fora disso é bloqueado."""
    cidrs: tuple[str, ...] = ()
    hostnames: frozenset[str] = field(default_factory=frozenset)
    allow_any_rfc1918: bool = False  # se True, qualquer RFC1918 passa (conveniência pra lab)

    def _ip_in_scope(self, ip_str: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if ip.is_loopback:
            return True
        if self.allow_any_rfc1918 and ip.is_private:
            return True
        for cidr in self.cidrs:
            try:
                if ip in ipaddress.ip_network(cidr, strict=False):
                    return True
            except ValueError:
                continue
        return False

    def _host_in_scope(self, host: str) -> bool:
        host = host.lower().rstrip(".")
        if host in ALWAYS_ALLOWED_HOSTS:
            return True
        return host in self.hostnames or any(host.endswith("." + h) for h in self.hostnames)


def check_scope(command: str, scope: Scope) -> Verdict:
    """Camada 2: valida que alvos no comando estão dentro do escopo."""
    hosts_seen: set[str] = set()
    # URLs primeiro
    for m in URL_HOST_PATTERN.finditer(command):
        host = m.group(1).lower()
        hosts_seen.add(host)
        if IP_PATTERN.fullmatch(host):
            if not scope._ip_in_scope(host):
                return Verdict(False, f"fora de escopo: {host} não está na allowlist")
        elif not scope._host_in_scope(host):
            return Verdict(False, f"fora de escopo: {host} não está na allowlist")
    # Hostnames bare (não-URL, não-path)
    for m in BARE_HOST_PATTERN.finditer(command):
        host = m.group(1).lower()
        if host in hosts_seen:
            continue
        # pula IPs (tratados separado) e arquivos
        if IP_PATTERN.fullmatch(host):
            continue
        if host.rsplit(".", 1)[-1] in FILE_EXTS:
            continue
        if not scope._host_in_scope(host):
            return Verdict(False, f"fora de escopo: {host} não está na allowlist")
    # IPs soltos
    for ip in IP_PATTERN.findall(command):
        parts = ip.split(".")
        if not all(0 <= int(p) <= 255 for p in parts):
            continue
        if not scope._ip_in_scope(ip):
            return Verdict(False, f"fora de escopo: {ip} não está na allowlist")
    return Verdict(True)


def check_all(command: str, scope: Scope | None = None) -> Verdict:
    """Aplica ambas as camadas."""
    v = check(command)
    if not v.allowed:
        return v
    if scope is not None:
        return check_scope(command, scope)
    return v
