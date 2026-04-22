import sys

import pytest


def test_run_routes_simple_flag_to_old_cli(monkeypatch):
    calls = {"simple": 0, "tui": 0}

    def fake_simple():
        calls["simple"] += 1

    class FakeApp:
        def run(self):
            calls["tui"] += 1

    from bagley.tui import app as app_mod
    monkeypatch.setattr(app_mod, "BagleyApp", lambda *a, **kw: FakeApp())
    monkeypatch.setattr("bagley.agent.cli.app", fake_simple)
    monkeypatch.setattr(sys, "argv", ["bagley", "--simple"])
    app_mod.run()
    assert calls == {"simple": 1, "tui": 0}


def test_run_routes_default_to_tui(monkeypatch):
    calls = {"simple": 0, "tui": 0}

    class FakeApp:
        def run(self):
            calls["tui"] += 1

    from bagley.tui import app as app_mod
    monkeypatch.setattr(app_mod, "BagleyApp", lambda *a, **kw: FakeApp())
    monkeypatch.setattr("bagley.agent.cli.app", lambda: calls.update(simple=calls["simple"] + 1))
    monkeypatch.setattr(sys, "argv", ["bagley"])
    app_mod.run()
    assert calls == {"simple": 0, "tui": 1}
