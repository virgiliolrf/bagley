import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_hosts_panel_renders_store_content(tmp_path, monkeypatch):
    monkeypatch.setenv("BAGLEY_MEMORY_DB", str(tmp_path / "mem.db"))
    from bagley.memory.store import MemoryStore, Finding
    store = MemoryStore(str(tmp_path / "mem.db"))
    store.upsert_host("10.10.14.23", state="up")
    store.add_port("10.10.14.23", 22, "tcp", "ssh", "OpenSSH 8.9")
    store.add_finding(Finding(
        host="10.10.14.23",
        severity="HIGH",
        category="web",
        summary="weak SSH kex",
        cve="CVE-2023-X",
    ))
    store.close()

    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        hosts = app.query_one("#hosts-section")
        ports = app.query_one("#ports-section")
        findings = app.query_one("#findings-section")
        h_text = str(hosts.render())
        p_text = str(ports.render())
        f_text = str(findings.render())
        assert "10.10.14.23" in h_text
        assert "22" in p_text and "ssh" in p_text
        assert "CVE-2023-X" in f_text or "weak SSH kex" in f_text
