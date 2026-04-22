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
        # Phase 3: #findings-section was replaced by SeverityBars aggregate bars.
        from bagley.tui.widgets.rings import SeverityBars
        bars = app.query_one(SeverityBars)
        h_text = str(hosts.render())
        p_text = str(ports.render())
        b_text = bars._render_text()
        assert "10.10.14.23" in h_text
        assert "22" in p_text and "ssh" in p_text
        # one HIGH finding was added — expect non-zero bar
        assert "HIGH" in b_text
        # HIGH row should show "1" at the end (count)
        high_line = next(l for l in b_text.splitlines() if l.startswith("HIGH"))
        assert "1" in high_line
