"""Minimal nmap -sV text output parser."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Port:
    number: int
    protocol: str        # "tcp" | "udp"
    state: str           # "open" | "closed" | "filtered"
    service: str
    version: str = ""


@dataclass
class Host:
    ip: str
    ports: list[Port] = field(default_factory=list)

    def open_ports(self) -> list[Port]:
        return [p for p in self.ports if p.state == "open"]


_HOST_RE = re.compile(r"Nmap scan report for ([\d\.]+)")
_PORT_RE = re.compile(
    r"^(\d+)/(tcp|udp)\s+(open|closed|filtered)\s+(\S+)(?:\s+(.+))?$"
)


def parse_nmap_output(text: str, open_only: bool = False) -> list[Host]:
    """Parse nmap -sV plain-text output into a list of Host objects."""
    hosts: list[Host] = []
    current: Optional[Host] = None

    for line in text.splitlines():
        line = line.strip()
        m = _HOST_RE.match(line)
        if m:
            current = Host(ip=m.group(1))
            hosts.append(current)
            continue

        if current is not None:
            pm = _PORT_RE.match(line)
            if pm:
                number = int(pm.group(1))
                protocol = pm.group(2)
                state = pm.group(3)
                service = pm.group(4)
                version = (pm.group(5) or "").strip()
                if open_only and state != "open":
                    continue
                current.ports.append(
                    Port(number=number, protocol=protocol, state=state,
                         service=service, version=version)
                )

    return hosts
