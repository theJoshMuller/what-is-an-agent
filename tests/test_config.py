# tests/test_config.py
import json
import pytest
from pathlib import Path
import importlib


def test_load_creates_default_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import config
    importlib.reload(config)
    cfg = config.load()
    assert cfg["provider"] == "ollama"
    assert cfg["ollama"]["model"] == "ministral-3:14b-instruct-2512-q8_0"
    assert (tmp_path / "config.json").exists()


def test_get_nested_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import config
    importlib.reload(config)
    config.load()
    assert config.get("ollama.model") == "ministral-3:14b-instruct-2512-q8_0"
    assert config.get("provider") == "ollama"


def test_set_and_persist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import config
    importlib.reload(config)
    config.load()
    config.set("ollama.model", "llama3.2")
    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved["ollama"]["model"] == "llama3.2"


def test_get_missing_key_returns_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import config
    importlib.reload(config)
    config.load()
    assert config.get("nonexistent.key", "fallback") == "fallback"
