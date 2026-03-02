# app/config.py
import json
from pathlib import Path

_CONFIG_FILE = Path("config.json")
_DEFAULTS = {
    "provider": "ollama",
    "ollama": {
        "host": "localhost",
        "port": 11434,
        "model": "ministral-3:14b-instruct-2512-q8_0"
    },
    "openrouter": {
        "model": "qwen/qwen3-235b-a22b-2507",
        "api_key": ""
    },
    "tools": {
        "read_file": True,
        "write_txt_file": True,
        "tts_generate_audio": False,
        "default_read_filename": "note.txt"
    },
    "tts": {
        "host": "localhost",
        "port": 8880
    }
}

_config: dict = {}


def load() -> dict:
    global _config
    if not _CONFIG_FILE.exists():
        _config = _deep_copy(_DEFAULTS)
        _save()
    else:
        with open(_CONFIG_FILE) as f:
            _config = json.load(f)
        # Merge any missing keys from defaults
        _merge_defaults(_config, _DEFAULTS)
        _save()
    return _config


def get(key: str, default=None):
    """Get a config value using dot notation. e.g. 'ollama.model'"""
    parts = key.split(".")
    val = _config
    for part in parts:
        if not isinstance(val, dict) or part not in val:
            return default
        val = val[part]
    return val


def set(key: str, value):
    """Set a config value using dot notation and persist."""
    parts = key.split(".")
    d = _config
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value
    _save()


def _save():
    with open(_CONFIG_FILE, "w") as f:
        json.dump(_config, f, indent=2)


def _deep_copy(d: dict) -> dict:
    return json.loads(json.dumps(d))


def _merge_defaults(target: dict, defaults: dict):
    for key, val in defaults.items():
        if key not in target:
            target[key] = _deep_copy(val) if isinstance(val, dict) else val
        elif isinstance(val, dict) and isinstance(target[key], dict):
            _merge_defaults(target[key], val)
