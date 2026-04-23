"""Tests for engine_registry - local adapter discovery and Ollama enumeration.

Ollama HTTP calls are mocked with `responses` library (no real network).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import responses as resp

from bagley.tui.services.engine_registry import (
    EngineEntry,
    EngineKind,
    list_engines,
)


# ---------------------------------------------------------------------------
# Local adapter discovery
# ---------------------------------------------------------------------------

def test_discovers_local_adapters(tmp_path: Path):
    # Simulate a runs/ directory with adapter dirs containing adapter_config.json
    for name in ("bagley-v9", "bagley-v10-modal"):
        d = tmp_path / name
        d.mkdir()
        (d / "adapter_config.json").write_text("{}")

    engines = list_engines(runs_dir=tmp_path, ollama_host=None)
    local_labels = [e.label for e in engines if e.kind == EngineKind.LOCAL]
    assert "bagley-v9" in local_labels
    assert "bagley-v10-modal" in local_labels


def test_ignores_non_adapter_dirs(tmp_path: Path):
    (tmp_path / "eval-v9").mkdir()          # no adapter_config.json
    (tmp_path / "bagley-v9").mkdir()
    (tmp_path / "bagley-v9" / "adapter_config.json").write_text("{}")

    engines = list_engines(runs_dir=tmp_path, ollama_host=None)
    local_labels = [e.label for e in engines if e.kind == EngineKind.LOCAL]
    assert "eval-v9" not in local_labels
    assert "bagley-v9" in local_labels


def test_stub_engine_always_present(tmp_path: Path):
    engines = list_engines(runs_dir=tmp_path, ollama_host=None)
    stubs = [e for e in engines if e.kind == EngineKind.STUB]
    assert len(stubs) == 1
    assert stubs[0].label == "stub"


# ---------------------------------------------------------------------------
# Ollama discovery (mocked HTTP)
# ---------------------------------------------------------------------------

OLLAMA_TAGS_RESPONSE = {
    "models": [
        {"name": "bagley:latest", "size": 5000000000},
        {"name": "llama3.1:8b", "size": 4000000000},
    ]
}


@resp.activate
def test_discovers_ollama_models(tmp_path: Path):
    resp.add(
        resp.GET,
        "http://localhost:11434/api/tags",
        json=OLLAMA_TAGS_RESPONSE,
        status=200,
    )
    engines = list_engines(runs_dir=tmp_path, ollama_host="http://localhost:11434")
    ollama_labels = [e.label for e in engines if e.kind == EngineKind.OLLAMA]
    assert "bagley:latest" in ollama_labels
    assert "llama3.1:8b" in ollama_labels


@resp.activate
def test_ollama_unavailable_is_skipped(tmp_path: Path):
    resp.add(
        resp.GET,
        "http://localhost:11434/api/tags",
        body=ConnectionError("refused"),
    )
    # Should not raise - just return no Ollama entries.
    engines = list_engines(runs_dir=tmp_path, ollama_host="http://localhost:11434")
    ollama = [e for e in engines if e.kind == EngineKind.OLLAMA]
    assert ollama == []


@resp.activate
def test_ollama_bad_status_is_skipped(tmp_path: Path):
    resp.add(
        resp.GET,
        "http://localhost:11434/api/tags",
        status=500,
    )
    engines = list_engines(runs_dir=tmp_path, ollama_host="http://localhost:11434")
    ollama = [e for e in engines if e.kind == EngineKind.OLLAMA]
    assert ollama == []


# ---------------------------------------------------------------------------
# EngineEntry fields
# ---------------------------------------------------------------------------

def test_engine_entry_has_required_fields(tmp_path: Path):
    (tmp_path / "bagley-v9").mkdir()
    (tmp_path / "bagley-v9" / "adapter_config.json").write_text("{}")
    engines = list_engines(runs_dir=tmp_path, ollama_host=None)
    local = [e for e in engines if e.kind == EngineKind.LOCAL][0]
    assert hasattr(local, "label")
    assert hasattr(local, "kind")
    assert hasattr(local, "path")   # Path or None
