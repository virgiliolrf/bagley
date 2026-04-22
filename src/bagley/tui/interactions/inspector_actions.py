"""Inspector actions — contextual action list produced per ClassifyResult.

Each InspectorAction carries:
  - label: short human-readable button text
  - command: shell command template or TUI action string
  - is_tui_action: if True, `command` is dispatched via app.action_* not executed in shell

A caller (InspectorPane) renders these as clickable items. Commands with
`{value}` are interpolated with ClassifyResult.value before use.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bagley.tui.interactions.selection import ClassifyResult, SelectionType


@dataclass
class InspectorAction:
    label: str
    command: str
    is_tui_action: bool = False


def actions_for(result: ClassifyResult) -> list[InspectorAction]:
    """Return contextual actions for *result*."""
    value = result.value
    t = result.type

    if t == SelectionType.IPV4:
        return [
            InspectorAction("nmap -sV", f"nmap -sV {value}"),
            InspectorAction("nmap full", f"nmap -sC -sV -p- --min-rate=1000 {value}"),
            InspectorAction("Open tab", f"new_tab:{value}", is_tui_action=True),
            InspectorAction("Set as target", f"set_target:{value}", is_tui_action=True),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to memory", f"memory_note:{value}", is_tui_action=True),
        ]

    if t == SelectionType.CVE:
        return [
            InspectorAction("searchsploit", f"searchsploit {value}"),
            InspectorAction("Exploit-DB lookup", f"exploit-db:{value}", is_tui_action=True),
            InspectorAction("MSF module search", f"msfconsole -q -x 'search {value}; exit'"),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to memory", f"memory_note:{value}", is_tui_action=True),
        ]

    if t == SelectionType.MD5:
        return [
            InspectorAction("hashcat (rockyou)", f"hashcat -a 0 -m 0 {value} rockyou.txt"),
            InspectorAction("john crack", f"echo '{value}' | john --format=raw-md5 --stdin"),
            InspectorAction("Identify type", f"hash-id:{value}", is_tui_action=True),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to creds", f"memory_cred:{value}", is_tui_action=True),
        ]

    if t == SelectionType.SHA256:
        return [
            InspectorAction("hashcat (rockyou)", f"hashcat -a 0 -m 1400 {value} rockyou.txt"),
            InspectorAction("Identify type", f"hash-id:{value}", is_tui_action=True),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to creds", f"memory_cred:{value}", is_tui_action=True),
        ]

    if t == SelectionType.URL:
        return [
            InspectorAction("ffuf dir-bust", f"ffuf -u {value}/FUZZ -w common.txt"),
            InspectorAction("gobuster", f"gobuster dir -u {value} -w common.txt"),
            InspectorAction("nikto scan", f"nikto -h {value}"),
            InspectorAction("curl -I", f"curl -sI {value}"),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to memory", f"memory_note:{value}", is_tui_action=True),
        ]

    if t == SelectionType.PORT:
        port_num = value.split("/")[0]
        return [
            InspectorAction("Banner grab", f"nc -zv {{target}} {port_num}"),
            InspectorAction("nmap service", f"nmap -sV -p {port_num} {{target}}"),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
        ]

    if t == SelectionType.PATH:
        return [
            InspectorAction("GTFOBins lookup", f"gtfobins:{value}", is_tui_action=True),
            InspectorAction("Check SUID", f"find {value} -perm -4000 2>/dev/null"),
            InspectorAction("ls -la", f"ls -la {value}"),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
        ]

    # UNKNOWN — fallback
    return [
        InspectorAction("Send to chat", f"chat:{result.raw}", is_tui_action=True),
        InspectorAction("Search (model)", f"explain:{result.raw}", is_tui_action=True),
    ]
