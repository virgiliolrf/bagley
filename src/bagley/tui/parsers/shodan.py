"""Minimal Shodan JSON → list[Host] parser."""

from __future__ import annotations

import json
from typing import Any

from bagley.tui.parsers.nmap import Host, Port


def parse_shodan_json(text: str) -> list[Host]:
    """Parse Shodan host JSON (single host or list) into Host objects.

    Handles both a bare Shodan host object and a list of them.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    hosts: list[Host] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ip = item.get("ip_str") or item.get("ip")
        if not ip:
            continue
        ports: list[Port] = []
        for port_entry in item.get("ports", []):
            if isinstance(port_entry, int):
                ports.append(Port(number=port_entry, protocol="tcp", state="open",
                                  service="", version=""))
        # Also parse the richer 'data' array if present
        for svc in item.get("data", []):
            if isinstance(svc, dict):
                num = svc.get("port")
                if num:
                    ports.append(Port(
                        number=int(num),
                        protocol=svc.get("transport", "tcp"),
                        state="open",
                        service=svc.get("_shodan", {}).get("module", ""),
                        version=svc.get("product", ""),
                    ))
        hosts.append(Host(ip=str(ip), ports=ports))
    return hosts
