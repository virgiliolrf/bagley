"""HostsPanel — reads memory/store.py for hosts + ports + findings."""

from __future__ import annotations

import os

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState


def _memory_path() -> str:
    return os.getenv("BAGLEY_MEMORY_DB", ".bagley/memory.db")


class HostsPanel(Vertical):
    DEFAULT_CSS = """
    HostsPanel { width: 28; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="hosts-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        yield Static("", id="hosts-section")
        yield Static("", id="ports-section")
        yield Static("", id="findings-section")

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        from bagley.memory.store import MemoryStore
        try:
            store = MemoryStore(_memory_path())
        except Exception:
            self.query_one("#hosts-section").update("[b orange3]◆ HOSTS[/]\n[dim](memory unavailable)[/]")
            self.query_one("#ports-section").update("[b orange3]◆ PORTS[/]\n[dim]—[/]")
            self.query_one("#findings-section").update("[b orange3]◆ FINDINGS[/]\n[dim]—[/]")
            return
        try:
            hosts = store.list_hosts() if hasattr(store, "list_hosts") else []
            host_lines = ["[b orange3]◆ HOSTS[/]"]
            for h in hosts or []:
                ip = h.get("ip") if isinstance(h, dict) else h["ip"]
                state = h.get("state", "?") if isinstance(h, dict) else h["state"]
                dot = "●" if state == "up" else "○"
                host_lines.append(f"{ip} [green]{dot}[/]")
            if len(host_lines) == 1:
                host_lines.append("[dim](none)[/]")

            active = self._state.tabs[self._state.active_tab]
            target_ip = active.id if active.kind == "target" else None
            # If not on a target tab but hosts exist, show ports/findings for the first host
            if target_ip is None and hosts:
                first = hosts[0]
                target_ip = first.get("ip") if isinstance(first, dict) else first["ip"]

            ports = []
            findings = []
            if target_ip and hasattr(store, "host_detail"):
                detail = store.host_detail(target_ip) or {}
                for p in detail.get("ports", []):
                    port_v = p.get("port") if isinstance(p, dict) else p["port"]
                    proto_v = p.get("proto", "tcp") if isinstance(p, dict) else p["proto"]
                    svc = p.get("service", "?") if isinstance(p, dict) else p["service"]
                    ports.append(f"{port_v}/{proto_v} [green]{svc}[/]")
                for f in detail.get("findings", []):
                    sev = f.get("severity", "?") if isinstance(f, dict) else f["severity"]
                    summary = f.get("summary", "") if isinstance(f, dict) else f["summary"]
                    cve = f.get("cve", "") if isinstance(f, dict) else (f["cve"] or "")
                    findings.append(f"[red]▸[/] {cve or summary} [dim]({sev})[/]")

            port_lines = ["[b orange3]◆ PORTS[/]"] + (ports or ["[dim](none)[/]"])
            finding_lines = ["[b orange3]◆ FINDINGS[/]"] + (findings or ["[dim](none)[/]"])

            self.query_one("#hosts-section").update("\n".join(host_lines))
            self.query_one("#ports-section").update("\n".join(port_lines))
            self.query_one("#findings-section").update("\n".join(finding_lines))
        finally:
            try:
                store.close()
            except Exception:
                pass
