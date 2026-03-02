# Agent Demo — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a GTK4 + libadwaita desktop app that demonstrates an AI agent (LLM + tools in a loop) for a live presentation.

**Architecture:** Single Python process. GTK4 UI with `Adw.OverlaySplitView` for responsive layout. LLM streaming via background threads with `GLib.idle_add` to update the UI safely. Agentic tool-call loop runs until no more tool calls are returned.

**Tech Stack:** Python 3, GTK4, libadwaita (system packages), `requests` (PyPI), Ollama API, OpenRouter API, Kokoro-FastAPI TTS

---

## Context & Constraints

- **Target platform:** Arch Linux + GNOME (libadwaita 1.4+, GTK 4.x)
- **System deps:** `python-gobject`, `gtk4`, `libadwaita` — installed via pacman
- **PyPI deps:** `requests` only
- **No browser required.** This is a native `.py` entry point.
- **Config:** `config.json` in working dir (auto-created on first run from defaults)
- **Tool calling:** Ollama and OpenRouter both support OpenAI-style `tools` + `tool_calls`
- **TDD applies to:** config, tools, LLM response parsers. NOT to GTK widgets (no headless GTK test infra).

---

## File Structure (target)

```
what-is-an-agent/
├── main.py
├── app/
│   ├── __init__.py
│   ├── window.py            # AdwApplicationWindow + agentic loop
│   ├── chat_panel.py        # Scrollable chat message list
│   ├── sidebar.py           # Tools toggles + model selector + branding
│   ├── settings_window.py   # AdwPreferencesWindow
│   ├── config.py            # Load/save config.json
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py          # Shared types: Message, ToolCall, StreamChunk
│   │   ├── ollama.py        # Ollama /api/chat streaming client
│   │   └── openrouter.py    # OpenRouter /v1/chat/completions SSE client
│   └── tools/
│       ├── __init__.py      # Tool registry + dispatch
│       ├── read_file.py
│       ├── write_txt_file.py
│       └── tts.py
├── tests/
│   ├── test_config.py
│   ├── test_tools.py
│   └── test_llm_parsers.py
├── config.json.example
├── requirements.txt
└── README.md
```

---

## Task 1: Project Scaffolding

**No tests for this task — just file/directory setup.**

**Files:**
- Create: `requirements.txt`
- Create: `config.json.example`
- Create: `app/__init__.py`, `app/llm/__init__.py`, `app/tools/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p app/llm app/tools tests docs/plans
touch app/__init__.py app/llm/__init__.py app/tools/__init__.py tests/__init__.py
```

**Step 2: Write requirements.txt**

```
requests>=2.31.0
```

**Step 3: Write config.json.example**

```json
{
  "provider": "ollama",
  "ollama": {
    "host": "localhost",
    "port": 11434,
    "model": "gemma3:27b"
  },
  "openrouter": {
    "model": "qwen/qwen3-235b-a22b-2507",
    "api_key": ""
  },
  "tools": {
    "read_file": true,
    "write_txt_file": true,
    "tts_generate_audio": false,
    "default_read_filename": "note.txt"
  },
  "tts": {
    "host": "localhost",
    "port": 8880
  }
}
```

**Step 4: Install Python dep**

```bash
pip install requests
```

**Step 5: Verify GTK4 + libadwaita are available**

```bash
python -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1'); from gi.repository import Gtk, Adw; print('GTK OK')"
```

Expected: `GTK OK`

If missing: `sudo pacman -S python-gobject gtk4 libadwaita`

**Step 6: Commit**

```bash
git init
git add requirements.txt config.json.example app/ tests/
git commit -m "chore: initial project scaffold"
```

---

## Task 2: Config System

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

### What config.py does

Loads `config.json` from the current working directory. If the file doesn't exist, creates it from defaults. Provides `get()` and `set()` functions. Saves on every `set()`.

**Step 1: Write the failing tests**

```python
# tests/test_config.py
import json
import os
import pytest
from pathlib import Path
import tempfile


def test_load_creates_default_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import config
    # Force reload
    import importlib
    importlib.reload(config)
    cfg = config.load()
    assert cfg["provider"] == "ollama"
    assert cfg["ollama"]["model"] == "gemma3:27b"
    assert (tmp_path / "config.json").exists()


def test_get_nested_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import config
    import importlib
    importlib.reload(config)
    config.load()
    assert config.get("ollama.model") == "gemma3:27b"
    assert config.get("provider") == "ollama"


def test_set_and_persist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import config
    import importlib
    importlib.reload(config)
    config.load()
    config.set("ollama.model", "llama3.2")
    # Reload from disk
    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved["ollama"]["model"] == "llama3.2"


def test_get_missing_key_returns_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app import config
    import importlib
    importlib.reload(config)
    config.load()
    assert config.get("nonexistent.key", "fallback") == "fallback"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`

**Step 3: Implement app/config.py**

```python
# app/config.py
import json
from pathlib import Path

_CONFIG_FILE = Path("config.json")
_DEFAULTS = {
    "provider": "ollama",
    "ollama": {
        "host": "localhost",
        "port": 11434,
        "model": "gemma3:27b"
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
```

**Step 4: Run tests**

```bash
pytest tests/test_config.py -v
```

Expected: 4 PASSED

**Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: config load/save with dot-notation get/set"
```

---

## Task 3: Tool Implementations

**Files:**
- Create: `app/tools/read_file.py`
- Create: `app/tools/write_txt_file.py`
- Create: `app/tools/tts.py`
- Create: `app/tools/__init__.py` (tool registry)
- Test: `tests/test_tools.py`

### Tool contract

Each tool is a function with signature:
```python
def execute(args: dict) -> dict:
    # returns {"result": str, "error": str | None}
```

**Step 1: Write failing tests**

```python
# tests/test_tools.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestReadFile:
    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "note.txt"
        f.write_text("Hello world")
        from app.tools.read_file import execute
        result = execute({"filename": str(f)})
        assert result["error"] is None
        assert result["result"] == "Hello world"

    def test_missing_file_returns_error(self, tmp_path):
        from app.tools.read_file import execute
        result = execute({"filename": str(tmp_path / "missing.txt")})
        assert result["error"] is not None
        assert "not found" in result["error"].lower()


class TestWriteTxtFile:
    def test_writes_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from app.tools.write_txt_file import execute
        result = execute({"filename": "output.txt", "content": "Test content"})
        assert result["error"] is None
        assert (tmp_path / "output.txt").read_text() == "Test content"

    def test_returns_confirmation(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from app.tools.write_txt_file import execute
        result = execute({"filename": "out.txt", "content": "hi"})
        assert "out.txt" in result["result"]


class TestTts:
    def test_calls_kokoro_api(self):
        from app.tools.tts import execute
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"RIFF....fake_wav_data"
        with patch("requests.post", return_value=mock_response) as mock_post:
            with patch("builtins.open", MagicMock()):
                result = execute({
                    "text": "Hello world",
                    "language": "en",
                    "filename": "test.wav"
                })
        assert mock_post.called
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json", call_args.args[1] if len(call_args.args) > 1 else {})
        assert payload.get("voice") == "af_heart"

    def test_french_uses_correct_voice(self):
        from app.tools.tts import VOICE_MAP
        assert VOICE_MAP["fr"] == "ff_siwis"

    def test_unknown_language_returns_error(self):
        from app.tools.tts import execute
        result = execute({"text": "Hi", "language": "xx", "filename": "out.wav"})
        assert result["error"] is not None


class TestToolRegistry:
    def test_get_enabled_tools_schemas(self):
        from app.tools import get_tool_schemas
        schemas = get_tool_schemas(["read_file", "write_txt_file"])
        names = [s["function"]["name"] for s in schemas]
        assert "read_file" in names
        assert "write_txt_file" in names
        assert "tts_generate_audio" not in names

    def test_dispatch_read_file(self, tmp_path):
        f = tmp_path / "note.txt"
        f.write_text("demo")
        from app.tools import dispatch
        result = dispatch("read_file", {"filename": str(f)})
        assert result["result"] == "demo"
```

**Step 2: Run tests to see them fail**

```bash
pytest tests/test_tools.py -v
```

Expected: All FAIL with import errors.

**Step 3: Implement app/tools/read_file.py**

```python
# app/tools/read_file.py
from pathlib import Path


SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file from the current working directory and return its contents.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to read (e.g. note.txt)"
                }
            },
            "required": ["filename"]
        }
    }
}


def execute(args: dict) -> dict:
    filename = args.get("filename", "note.txt")
    path = Path(filename)
    if not path.exists():
        return {"result": "", "error": f"File not found: {filename}"}
    try:
        content = path.read_text(encoding="utf-8")
        return {"result": content, "error": None}
    except Exception as e:
        return {"result": "", "error": str(e)}
```

**Step 4: Implement app/tools/write_txt_file.py**

```python
# app/tools/write_txt_file.py
from pathlib import Path


SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_txt_file",
        "description": "Write text content to a file in the current working directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to write (e.g. output.txt)"
                },
                "content": {
                    "type": "string",
                    "description": "The text content to write to the file"
                }
            },
            "required": ["filename", "content"]
        }
    }
}


def execute(args: dict) -> dict:
    filename = args.get("filename", "output.txt")
    content = args.get("content", "")
    path = Path(filename)
    try:
        path.write_text(content, encoding="utf-8")
        return {"result": f"Successfully wrote {len(content)} characters to {filename}", "error": None}
    except Exception as e:
        return {"result": "", "error": str(e)}
```

**Step 5: Implement app/tools/tts.py**

```python
# app/tools/tts.py
import subprocess
from pathlib import Path
import requests
from app import config

VOICE_MAP = {
    "en": "af_heart",
    "fr": "ff_siwis",
    "es": "ef_dora",
    "pt": "pf_dora",
    "it": "if_sara",
    "hi": "hf_alpha",
}

LANGUAGE_LABELS = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "it": "Italian",
    "hi": "Hindi",
}

SCHEMA = {
    "type": "function",
    "function": {
        "name": "tts_generate_audio",
        "description": (
            "Convert text to speech using Kokoro TTS and save the audio to a file. "
            "Supported languages: en (English), fr (French), es (Spanish), "
            "pt (Portuguese), it (Italian), hi (Hindi)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to synthesize"
                },
                "language": {
                    "type": "string",
                    "enum": list(VOICE_MAP.keys()),
                    "description": "Language code: en, fr, es, pt, it, hi"
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename (e.g. greeting.wav)"
                }
            },
            "required": ["text", "language", "filename"]
        }
    }
}


def execute(args: dict) -> dict:
    text = args.get("text", "")
    language = args.get("language", "en")
    filename = args.get("filename", "output.wav")

    if language not in VOICE_MAP:
        return {
            "result": "",
            "error": f"Unsupported language '{language}'. Supported: {', '.join(VOICE_MAP.keys())}"
        }

    voice = VOICE_MAP[language]
    host = config.get("tts.host", "localhost")
    port = config.get("tts.port", 8880)
    url = f"http://{host}:{port}/v1/audio/speech"

    try:
        response = requests.post(url, json={
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": "wav",
        }, timeout=30)

        if response.status_code != 200:
            return {"result": "", "error": f"TTS API error {response.status_code}: {response.text[:200]}"}

        path = Path(filename)
        with open(path, "wb") as f:
            f.write(response.content)

        return {
            "result": f"Audio saved to {filename} ({len(response.content)} bytes). Voice: {voice}.",
            "error": None,
            "audio_file": str(path.absolute()),
        }
    except requests.exceptions.ConnectionError:
        return {
            "result": "",
            "error": f"Cannot connect to Kokoro TTS at {host}:{port}. See https://github.com/remsky/Kokoro-FastAPI to set up TTS."
        }
    except Exception as e:
        return {"result": "", "error": str(e)}


def play_audio(filepath: str):
    """Play audio file using aplay (non-blocking)."""
    subprocess.Popen(["aplay", filepath],
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
```

**Step 6: Implement app/tools/__init__.py (tool registry)**

```python
# app/tools/__init__.py
from app.tools import read_file, write_txt_file, tts

_TOOL_MAP = {
    "read_file": read_file,
    "write_txt_file": write_txt_file,
    "tts_generate_audio": tts,
}


def get_tool_schemas(enabled_tools: list[str]) -> list[dict]:
    """Return OpenAI-format tool schemas for the enabled tools."""
    schemas = []
    for name in enabled_tools:
        if name in _TOOL_MAP:
            schemas.append(_TOOL_MAP[name].SCHEMA)
    return schemas


def dispatch(tool_name: str, args: dict) -> dict:
    """Execute a tool by name with the given args."""
    if tool_name not in _TOOL_MAP:
        return {"result": "", "error": f"Unknown tool: {tool_name}"}
    return _TOOL_MAP[tool_name].execute(args)
```

**Step 7: Run tests**

```bash
pytest tests/test_tools.py -v
```

Expected: All PASSED (TTS test uses mocks so no real Kokoro needed)

**Step 8: Commit**

```bash
git add app/tools/ tests/test_tools.py
git commit -m "feat: tool implementations (read_file, write_txt_file, tts_generate_audio)"
```

---

## Task 4: LLM Clients

**Files:**
- Create: `app/llm/base.py`
- Create: `app/llm/ollama.py`
- Create: `app/llm/openrouter.py`
- Test: `tests/test_llm_parsers.py`

### Unified streaming protocol

Both clients must yield `StreamChunk` objects so the UI layer doesn't care which backend is active.

**Step 1: Write app/llm/base.py**

```python
# app/llm/base.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict  # Already parsed from JSON


@dataclass
class StreamChunk:
    """Yielded by streaming LLM clients."""
    text: str = ""               # Token text (may be empty if tool call)
    tool_calls: list[ToolCall] = field(default_factory=list)  # Non-empty on tool call
    done: bool = False           # True on final chunk
    error: Optional[str] = None  # Set if an error occurred


Message = dict  # {"role": "user"|"assistant"|"tool", "content": str, "tool_calls": [...]}
```

**Step 2: Write failing tests**

```python
# tests/test_llm_parsers.py
import json
import pytest
from unittest.mock import MagicMock, patch
from app.llm.base import StreamChunk, ToolCall


class TestOllamaParser:
    def test_text_chunk_parsed(self):
        from app.llm.ollama import _parse_chunk
        raw = json.dumps({
            "message": {"role": "assistant", "content": "Hello", "tool_calls": None},
            "done": False
        })
        chunk = _parse_chunk(raw)
        assert chunk.text == "Hello"
        assert chunk.done is False
        assert chunk.tool_calls == []

    def test_tool_call_chunk_parsed(self):
        from app.llm.ollama import _parse_chunk
        raw = json.dumps({
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "read_file",
                        "arguments": {"filename": "note.txt"}
                    }
                }]
            },
            "done": False
        })
        chunk = _parse_chunk(raw)
        assert len(chunk.tool_calls) == 1
        assert chunk.tool_calls[0].name == "read_file"
        assert chunk.tool_calls[0].arguments == {"filename": "note.txt"}

    def test_done_chunk(self):
        from app.llm.ollama import _parse_chunk
        raw = json.dumps({"message": {"content": ""}, "done": True})
        chunk = _parse_chunk(raw)
        assert chunk.done is True


class TestOpenRouterParser:
    def test_text_delta_parsed(self):
        from app.llm.openrouter import _parse_sse_line
        line = 'data: ' + json.dumps({
            "choices": [{"delta": {"content": "Hi"}, "finish_reason": None}]
        })
        chunk = _parse_sse_line(line)
        assert chunk is not None
        assert chunk.text == "Hi"

    def test_done_signal(self):
        from app.llm.openrouter import _parse_sse_line
        chunk = _parse_sse_line("data: [DONE]")
        assert chunk is not None
        assert chunk.done is True

    def test_empty_line_returns_none(self):
        from app.llm.openrouter import _parse_sse_line
        assert _parse_sse_line("") is None
        assert _parse_sse_line(":") is None
```

**Step 3: Run to confirm failures**

```bash
pytest tests/test_llm_parsers.py -v
```

Expected: All FAIL with import errors.

**Step 4: Implement app/llm/ollama.py**

```python
# app/llm/ollama.py
import json
import requests
from typing import Generator
from app.llm.base import StreamChunk, ToolCall, Message
from app import config


def _parse_chunk(raw: str) -> StreamChunk:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return StreamChunk(error=f"JSON parse error: {raw[:100]}")

    done = data.get("done", False)
    msg = data.get("message", {})
    content = msg.get("content", "") or ""
    raw_tool_calls = msg.get("tool_calls") or []

    tool_calls = []
    for tc in raw_tool_calls:
        fn = tc.get("function", {})
        name = fn.get("name", "")
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        tool_calls.append(ToolCall(id=name, name=name, arguments=args))

    return StreamChunk(text=content, tool_calls=tool_calls, done=done)


def stream(messages: list[Message], tools: list[dict]) -> Generator[StreamChunk, None, None]:
    host = config.get("ollama.host", "localhost")
    port = config.get("ollama.port", 11434)
    model = config.get("ollama.model", "gemma3:27b")
    url = f"http://{host}:{port}/api/chat"

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools

    try:
        resp = requests.post(url, json=payload, stream=True, timeout=60)
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                chunk = _parse_chunk(line.decode("utf-8"))
                yield chunk
                if chunk.done or chunk.error:
                    break
    except requests.exceptions.ConnectionError as e:
        yield StreamChunk(error=f"Cannot connect to Ollama at {host}:{port}. Is Ollama running?")
    except Exception as e:
        yield StreamChunk(error=str(e))
```

**Step 5: Implement app/llm/openrouter.py**

```python
# app/llm/openrouter.py
import json
import os
import requests
from typing import Generator, Optional
from app.llm.base import StreamChunk, ToolCall, Message
from app import config


def _parse_sse_line(line: str) -> Optional[StreamChunk]:
    if not line or line.startswith(":"):
        return None
    if line == "data: [DONE]":
        return StreamChunk(done=True)
    if not line.startswith("data: "):
        return None

    try:
        data = json.loads(line[6:])
    except json.JSONDecodeError:
        return None

    choices = data.get("choices", [])
    if not choices:
        return None

    choice = choices[0]
    finish_reason = choice.get("finish_reason")
    delta = choice.get("delta", {})
    content = delta.get("content") or ""

    # Parse streaming tool calls (accumulated across chunks)
    raw_tool_calls = delta.get("tool_calls") or []
    tool_calls = []
    for tc in raw_tool_calls:
        fn = tc.get("function", {})
        name = fn.get("name", "")
        args_str = fn.get("arguments", "{}")
        try:
            args = json.loads(args_str) if args_str else {}
        except Exception:
            args = {}
        if name:
            tool_calls.append(ToolCall(id=tc.get("id", name), name=name, arguments=args))

    done = finish_reason in ("stop", "tool_calls")
    return StreamChunk(text=content, tool_calls=tool_calls, done=done)


def stream(messages: list[Message], tools: list[dict]) -> Generator[StreamChunk, None, None]:
    api_key = config.get("openrouter.api_key", "") or os.environ.get("OPENROUTER_API_KEY", "")
    model = config.get("openrouter.model", "qwen/qwen3-235b-a22b-2507")

    if not api_key:
        yield StreamChunk(error="No OpenRouter API key. Set OPENROUTER_API_KEY env var or configure in Settings.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://joshmuller.ca",
        "X-Title": "What is an Agent? Demo",
    }

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools

    # OpenRouter tool calls accumulate across SSE chunks — we buffer them
    accumulated_tool_calls: dict[int, dict] = {}

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        )
        resp.raise_for_status()

        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            chunk = _parse_sse_line(decoded)
            if chunk is None:
                continue
            yield chunk
            if chunk.done or chunk.error:
                break

    except requests.exceptions.ConnectionError as e:
        yield StreamChunk(error=f"Cannot connect to OpenRouter: {e}")
    except requests.exceptions.HTTPError as e:
        yield StreamChunk(error=f"OpenRouter API error: {e.response.status_code} {e.response.text[:200]}")
    except Exception as e:
        yield StreamChunk(error=str(e))
```

**Step 6: Run tests**

```bash
pytest tests/test_llm_parsers.py -v
```

Expected: All PASSED

**Step 7: Commit**

```bash
git add app/llm/ tests/test_llm_parsers.py
git commit -m "feat: Ollama and OpenRouter streaming LLM clients"
```

---

## Task 5: Main Window Skeleton

**Files:**
- Create: `main.py`
- Create: `app/window.py`

No unit tests for GTK widgets. Verify by running the app.

**Step 1: Write main.py**

```python
# main.py
import sys
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw
from app import config
from app.window import AgentDemoWindow


class AgentDemoApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="ca.joshmuller.agent-demo")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        config.load()
        win = AgentDemoWindow(application=app)
        win.present()


def main():
    app = AgentDemoApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
```

**Step 2: Write app/window.py (skeleton)**

```python
# app/window.py
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
import threading

from app import config
from app.chat_panel import ChatPanel
from app.sidebar import Sidebar
from app.settings_window import SettingsWindow
from app import tools
from app.llm import base as llm_base


class AgentDemoWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("What is an Agent?")
        self.set_default_size(1000, 700)
        self.messages: list[dict] = []  # Conversation context

        self._build_ui()

    def _build_ui(self):
        # Root: ToolbarView for header + content
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # Sidebar toggle (for narrow mode)
        self._sidebar_toggle = Gtk.ToggleButton(icon_name="sidebar-show-symbolic")
        self._sidebar_toggle.set_tooltip_text("Show/Hide Tools")
        header.pack_start(self._sidebar_toggle)

        # Clear button
        clear_btn = Gtk.Button(icon_name="edit-clear-all-symbolic")
        clear_btn.set_tooltip_text("Clear conversation")
        clear_btn.connect("clicked", self._on_clear)
        header.pack_end(clear_btn)

        # Settings button
        settings_btn = Gtk.Button(icon_name="preferences-system-symbolic")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.connect("clicked", self._on_settings)
        header.pack_end(settings_btn)

        # Split view (responsive sidebar)
        self._split_view = Adw.OverlaySplitView()
        self._split_view.set_sidebar_position(Gtk.PackType.END)
        self._split_view.set_max_sidebar_width(300)
        self._split_view.set_min_sidebar_width(220)
        # Collapse sidebar when window is narrow
        self._split_view.set_collapsed(False)
        toolbar_view.set_content(self._split_view)

        # Bind toggle to split view
        self._sidebar_toggle.bind_property(
            "active", self._split_view, "show-sidebar",
            GLib.BindingFlags.BIDIRECTIONAL | GLib.BindingFlags.SYNC_CREATE
        )

        # Chat panel (main content)
        self._chat = ChatPanel()
        self._split_view.set_content(self._chat)

        # Sidebar
        self._sidebar = Sidebar(on_tool_toggled=self._on_tool_toggled)
        self._split_view.set_sidebar(self._sidebar)

        # Input row
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_box.set_margin_start(12)
        input_box.set_margin_end(12)
        input_box.set_margin_top(8)
        input_box.set_margin_bottom(12)

        self._entry = Gtk.Entry()
        self._entry.set_hexpand(True)
        self._entry.set_placeholder_text("Type a message...")
        self._entry.connect("activate", self._on_send)
        input_box.append(self._entry)

        self._send_btn = Gtk.Button(label="Send")
        self._send_btn.add_css_class("suggested-action")
        self._send_btn.connect("clicked", self._on_send)
        input_box.append(self._send_btn)

        toolbar_view.add_bottom_bar(input_box)

    def _on_clear(self, *_):
        self.messages = []
        self._chat.clear()

    def _on_settings(self, *_):
        win = SettingsWindow(transient_for=self)
        win.present()

    def _on_tool_toggled(self, tool_name: str, enabled: bool):
        """Toggling a tool clears context (tool schemas change)."""
        self._on_clear()

    def _on_send(self, *_):
        text = self._entry.get_text().strip()
        if not text:
            return
        self._entry.set_text("")
        self._set_input_sensitive(False)

        # Add user message to context and UI
        self.messages.append({"role": "user", "content": text})
        self._chat.add_user_message(text)

        # Start agentic loop in background thread
        thread = threading.Thread(target=self._agent_loop, daemon=True)
        thread.start()

    def _set_input_sensitive(self, sensitive: bool):
        self._entry.set_sensitive(sensitive)
        self._send_btn.set_sensitive(sensitive)

    def _agent_loop(self):
        """Runs in background thread. Uses GLib.idle_add to update UI."""
        from app.llm import ollama, openrouter
        from app import tools as tool_registry

        provider = config.get("provider", "ollama")
        llm_stream = ollama.stream if provider == "ollama" else openrouter.stream

        enabled_tools = [
            name for name in ["read_file", "write_txt_file", "tts_generate_audio"]
            if config.get(f"tools.{name}", False)
        ]
        tool_schemas = tool_registry.get_tool_schemas(enabled_tools)

        while True:
            # Create a new assistant bubble
            bubble_id = self._chat.start_assistant_message()
            full_text = ""
            pending_tool_calls = []

            for chunk in llm_stream(self.messages, tool_schemas):
                if chunk.error:
                    GLib.idle_add(self._chat.append_text, bubble_id, f"\n\n⚠ {chunk.error}")
                    break
                if chunk.text:
                    full_text += chunk.text
                    GLib.idle_add(self._chat.append_text, bubble_id, chunk.text)
                if chunk.tool_calls:
                    pending_tool_calls.extend(chunk.tool_calls)
                if chunk.done:
                    break

            # Append assistant message to context
            if full_text or pending_tool_calls:
                assistant_msg = {"role": "assistant", "content": full_text}
                if pending_tool_calls:
                    assistant_msg["tool_calls"] = [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.name, "arguments": tc.arguments}}
                        for tc in pending_tool_calls
                    ]
                self.messages.append(assistant_msg)

            # Execute tool calls
            if not pending_tool_calls:
                break  # No more tool calls — done

            for tc in pending_tool_calls:
                GLib.idle_add(self._chat.add_tool_indicator, tc.name)
                GLib.idle_add(self._sidebar.set_status, f"Running: {tc.name}")

                result = tool_registry.dispatch(tc.name, tc.arguments)

                # Append tool result to context
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": result["result"] if not result["error"] else f"Error: {result['error']}"
                })

                # Show result in UI
                audio_file = result.get("audio_file")
                GLib.idle_add(self._chat.add_tool_result, tc.name, result, audio_file)

        GLib.idle_add(self._sidebar.set_status, "Ready")
        GLib.idle_add(self._set_input_sensitive, True)
```

**Step 3: Run the app (smoke test)**

```bash
python main.py
```

Expected: Window opens. Header bar with toggle, clear, settings buttons. Empty chat area. Input row at bottom. Sidebar visible.

**Step 4: Commit**

```bash
git add main.py app/window.py
git commit -m "feat: main window skeleton with responsive split view"
```

---

## Task 6: Chat Panel Widget

**Files:**
- Create: `app/chat_panel.py`

**Step 1: Implement app/chat_panel.py**

```python
# app/chat_panel.py
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango
import subprocess
from pathlib import Path


class MessageBubble(Gtk.Box):
    """A single message bubble (user or assistant)."""

    def __init__(self, role: str, text: str = ""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        is_user = role == "user"

        # Label
        self._label = Gtk.Label()
        self._label.set_wrap(True)
        self._label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._label.set_xalign(0)
        self._label.set_selectable(True)
        self._label.set_text(text)

        # Bubble box
        bubble = Gtk.Box()
        bubble.set_margin_start(0 if is_user else 40)
        bubble.set_margin_end(40 if is_user else 0)
        bubble.set_halign(Gtk.Align.END if is_user else Gtk.Align.START)
        bubble.append(self._label)
        bubble.add_css_class("card")
        bubble.set_margin_top(2)
        bubble.set_margin_bottom(2)

        # Style
        if is_user:
            bubble.add_css_class("user-bubble")
        else:
            bubble.add_css_class("assistant-bubble")

        self._label.set_margin_start(12)
        self._label.set_margin_end(12)
        self._label.set_margin_top(8)
        self._label.set_margin_bottom(8)

        self.append(bubble)
        self._bubble = bubble

    def append_text(self, text: str):
        current = self._label.get_text()
        self._label.set_text(current + text)

    def add_play_button(self, audio_file: str):
        btn = Gtk.Button(label="▶ Play Audio")
        btn.set_halign(Gtk.Align.START)
        btn.set_margin_start(12)
        btn.connect("clicked", lambda *_: _play_audio(audio_file))
        self._bubble.parent.append(btn)


class ToolChip(Gtk.Box):
    """Shows a tool call indicator inline in the chat."""

    def __init__(self, tool_name: str):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.set_margin_start(52)
        self.set_margin_top(2)
        self.set_margin_bottom(2)

        icon = Gtk.Image.new_from_icon_name("system-run-symbolic")
        label = Gtk.Label(label=f"Using tool: {tool_name}")
        label.add_css_class("caption")
        label.add_css_class("dim-label")

        self.append(icon)
        self.append(label)


class ToolResultCard(Gtk.Box):
    """Shows the result of a tool call."""

    def __init__(self, tool_name: str, result: dict, audio_file: str | None = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_margin_start(52)
        self.set_margin_end(12)
        self.set_margin_top(2)
        self.set_margin_bottom(6)

        expander = Gtk.Expander()
        has_error = bool(result.get("error"))
        label_text = f"{'✗' if has_error else '✓'} {tool_name} result"
        expander.set_label(label_text)

        content_text = result.get("error") or result.get("result", "")
        content_label = Gtk.Label(label=content_text[:500])  # Truncate long results
        content_label.set_wrap(True)
        content_label.set_xalign(0)
        content_label.add_css_class("monospace")
        content_label.add_css_class("caption")
        content_label.set_margin_start(12)
        content_label.set_margin_top(4)
        expander.set_child(content_label)

        self.append(expander)

        if audio_file and Path(audio_file).exists():
            play_btn = Gtk.Button(label="▶ Play Audio")
            play_btn.set_halign(Gtk.Align.START)
            play_btn.add_css_class("pill")
            play_btn.connect("clicked", lambda *_: _play_audio(audio_file))
            self.append(play_btn)


def _play_audio(filepath: str):
    subprocess.Popen(["aplay", filepath],
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)


class ChatPanel(Gtk.Box):
    """Scrollable chat message list."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._bubbles: dict[int, MessageBubble] = {}
        self._next_id = 0

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scroll)

        self._list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._list_box.set_valign(Gtk.Align.END)
        self._list_box.set_vexpand(True)
        scroll.set_child(self._list_box)

        self._scroll = scroll

    def add_user_message(self, text: str):
        bubble = MessageBubble("user", text)
        self._list_box.append(bubble)
        self._scroll_to_bottom()

    def start_assistant_message(self) -> int:
        """Create an empty assistant bubble and return its ID for streaming."""
        bubble_id = self._next_id
        self._next_id += 1
        bubble = MessageBubble("assistant", "")
        self._bubbles[bubble_id] = bubble
        self._list_box.append(bubble)
        self._scroll_to_bottom()
        return bubble_id

    def append_text(self, bubble_id: int, text: str):
        """Append text to an existing assistant bubble (for streaming)."""
        if bubble_id in self._bubbles:
            self._bubbles[bubble_id].append_text(text)
            self._scroll_to_bottom()

    def add_tool_indicator(self, tool_name: str):
        chip = ToolChip(tool_name)
        self._list_box.append(chip)
        self._scroll_to_bottom()

    def add_tool_result(self, tool_name: str, result: dict, audio_file: str | None = None):
        card = ToolResultCard(tool_name, result, audio_file)
        self._list_box.append(card)
        self._scroll_to_bottom()

    def clear(self):
        self._bubbles = {}
        child = self._list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._list_box.remove(child)
            child = next_child

    def _scroll_to_bottom(self):
        adj = self._scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
```

**Step 2: Run the app**

```bash
python main.py
```

Expected: Chat panel is visible. Type a message and hit Enter — a user bubble appears.

**Step 3: Commit**

```bash
git add app/chat_panel.py
git commit -m "feat: chat panel with streaming bubbles and tool result cards"
```

---

## Task 7: Sidebar Widget

**Files:**
- Create: `app/sidebar.py`

**Step 1: Implement app/sidebar.py**

```python
# app/sidebar.py
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from app import config


TOOL_INFO = {
    "read_file": ("document-open-symbolic", "read_file", "Read a file from the working directory"),
    "write_txt_file": ("document-save-symbolic", "write_txt_file", "Write a text file to the working directory"),
    "tts_generate_audio": ("audio-speakers-symbolic", "tts_generate_audio", "Generate speech audio via Kokoro TTS"),
}


class Sidebar(Gtk.Box):
    def __init__(self, on_tool_toggled=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._on_tool_toggled = on_tool_toggled
        self._tool_switches: dict[str, Gtk.Switch] = {}
        self._status_label = None
        self._build()

    def _build(self):
        self.set_width_request(220)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scroll)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroll.set_child(content)

        # Tools section
        tools_group = Adw.PreferencesGroup()
        tools_group.set_title("Tools")
        tools_group.set_margin_start(12)
        tools_group.set_margin_end(12)
        tools_group.set_margin_top(16)
        content.append(tools_group)

        for tool_name, (icon, key, description) in TOOL_INFO.items():
            row = Adw.SwitchRow()
            row.set_title(tool_name)
            row.set_subtitle(description)
            row.set_icon_name(icon)
            active = config.get(f"tools.{key}", False)
            row.set_active(active)
            row.connect("notify::active", self._on_switch_changed, key)
            self._tool_switches[key] = row
            tools_group.add(row)

        # Model section
        model_group = Adw.PreferencesGroup()
        model_group.set_title("Model")
        model_group.set_margin_start(12)
        model_group.set_margin_end(12)
        model_group.set_margin_top(16)
        content.append(model_group)

        # Provider toggle
        self._provider_row = Adw.ActionRow()
        self._provider_row.set_title("Provider")

        provider_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        ollama_btn = Gtk.ToggleButton(label="Ollama")
        openrouter_btn = Gtk.ToggleButton(label="OpenRouter")
        ollama_btn.set_group(None)
        openrouter_btn.set_group(ollama_btn)

        current_provider = config.get("provider", "ollama")
        ollama_btn.set_active(current_provider == "ollama")
        openrouter_btn.set_active(current_provider == "openrouter")

        ollama_btn.connect("toggled", self._on_provider_changed, "ollama")
        openrouter_btn.connect("toggled", self._on_provider_changed, "openrouter")

        provider_box.append(ollama_btn)
        provider_box.append(openrouter_btn)
        self._provider_row.add_suffix(provider_box)
        model_group.add(self._provider_row)

        # Model name display
        self._model_row = Adw.ActionRow()
        self._model_row.set_title("Model")
        self._update_model_label()
        model_group.add(self._model_row)

        # Status section
        status_group = Adw.PreferencesGroup()
        status_group.set_title("Status")
        status_group.set_margin_start(12)
        status_group.set_margin_end(12)
        status_group.set_margin_top(16)
        content.append(status_group)

        status_row = Adw.ActionRow()
        status_row.set_title("State")
        self._status_label = Gtk.Label(label="Ready")
        self._status_label.add_css_class("success")
        status_row.add_suffix(self._status_label)
        status_group.add(status_row)

        # Branding
        branding_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        branding_box.set_margin_top(24)
        branding_box.set_margin_bottom(12)
        branding_box.set_margin_start(12)
        branding_box.set_margin_end(12)
        branding_box.set_valign(Gtk.Align.END)
        branding_box.set_vexpand(True)

        made_by = Gtk.Label(label="Made by Josh Müller")
        made_by.add_css_class("caption")
        made_by.add_css_class("dim-label")

        website = Gtk.LinkButton(uri="https://joshmuller.ca", label="joshmuller.ca")
        website.add_css_class("caption")

        branding_box.append(made_by)
        branding_box.append(website)
        content.append(branding_box)

    def _on_switch_changed(self, row, _param, tool_name: str):
        active = row.get_active()
        config.set(f"tools.{tool_name}", active)
        if self._on_tool_toggled:
            self._on_tool_toggled(tool_name, active)

    def _on_provider_changed(self, btn, provider: str):
        if btn.get_active():
            config.set("provider", provider)
            self._update_model_label()

    def _update_model_label(self):
        provider = config.get("provider", "ollama")
        if provider == "ollama":
            model = config.get("ollama.model", "gemma3:27b")
        else:
            model = config.get("openrouter.model", "qwen/qwen3-235b-a22b-2507")
        # Truncate long model names for display
        display = model if len(model) < 24 else f"...{model[-21:]}"
        if hasattr(self, "_model_row") and self._model_row:
            self._model_row.set_subtitle(display)

    def set_status(self, text: str):
        if self._status_label:
            self._status_label.set_text(text)
            self._status_label.remove_css_class("success")
            self._status_label.remove_css_class("warning")
            if text == "Ready":
                self._status_label.add_css_class("success")
            else:
                self._status_label.add_css_class("warning")
```

**Step 2: Run the app**

```bash
python main.py
```

Expected: Sidebar shows Tools section with 3 toggle rows, Model section with provider toggle, Status "Ready", and branding at bottom.

**Step 3: Commit**

```bash
git add app/sidebar.py
git commit -m "feat: sidebar with tool toggles, model selector, status, branding"
```

---

## Task 8: Settings Window

**Files:**
- Create: `app/settings_window.py`

**Step 1: Implement app/settings_window.py**

```python
# app/settings_window.py
import os
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from app import config


class SettingsWindow(Adw.PreferencesDialog):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Settings")
        self._build()

    def _build(self):
        # ── LLM Page ──────────────────────────────────────────────
        llm_page = Adw.PreferencesPage()
        llm_page.set_title("LLM")
        llm_page.set_icon_name("brain-augmented-symbolic")
        self.add(llm_page)

        # Ollama group
        ollama_group = Adw.PreferencesGroup()
        ollama_group.set_title("Ollama")
        ollama_group.set_description("Local LLM server (default: localhost)")
        llm_page.add(ollama_group)

        ollama_host = Adw.EntryRow()
        ollama_host.set_title("Host")
        ollama_host.set_text(str(config.get("ollama.host", "localhost")))
        ollama_host.connect("changed", lambda r: config.set("ollama.host", r.get_text()))
        ollama_group.add(ollama_host)

        ollama_port = Adw.EntryRow()
        ollama_port.set_title("Port")
        ollama_port.set_text(str(config.get("ollama.port", 11434)))
        ollama_port.connect("changed", lambda r: config.set("ollama.port", int(r.get_text() or 11434)))
        ollama_group.add(ollama_port)

        ollama_model = Adw.EntryRow()
        ollama_model.set_title("Model")
        ollama_model.set_text(str(config.get("ollama.model", "gemma3:27b")))
        ollama_model.connect("changed", lambda r: config.set("ollama.model", r.get_text()))
        ollama_group.add(ollama_model)

        # OpenRouter group
        or_group = Adw.PreferencesGroup()
        or_group.set_title("OpenRouter")
        or_group.set_description("Cloud LLM via OpenRouter API")
        llm_page.add(or_group)

        or_model = Adw.EntryRow()
        or_model.set_title("Model")
        or_model.set_text(str(config.get("openrouter.model", "qwen/qwen3-235b-a22b-2507")))
        or_model.connect("changed", lambda r: config.set("openrouter.model", r.get_text()))
        or_group.add(or_model)

        or_key = Adw.PasswordEntryRow()
        or_key.set_title("API Key")
        stored_key = config.get("openrouter.api_key", "")
        env_key = os.environ.get("OPENROUTER_API_KEY", "")
        or_key.set_text(stored_key or "")
        if not stored_key and env_key:
            or_key.set_subtitle("Using $OPENROUTER_API_KEY from environment")
        or_key.connect("changed", lambda r: config.set("openrouter.api_key", r.get_text()))
        or_group.add(or_key)

        # ── Tools Page ────────────────────────────────────────────
        tools_page = Adw.PreferencesPage()
        tools_page.set_title("Tools")
        tools_page.set_icon_name("applications-engineering-symbolic")
        self.add(tools_page)

        files_group = Adw.PreferencesGroup()
        files_group.set_title("File Tools")
        tools_page.add(files_group)

        read_filename = Adw.EntryRow()
        read_filename.set_title("Default read filename")
        read_filename.set_text(config.get("tools.default_read_filename", "note.txt"))
        read_filename.connect("changed", lambda r: config.set("tools.default_read_filename", r.get_text()))
        files_group.add(read_filename)

        # ── TTS Page ──────────────────────────────────────────────
        tts_page = Adw.PreferencesPage()
        tts_page.set_title("TTS")
        tts_page.set_icon_name("audio-speakers-symbolic")
        self.add(tts_page)

        kokoro_group = Adw.PreferencesGroup()
        kokoro_group.set_title("Kokoro TTS")
        kokoro_group.set_description(
            "Self-hosted text-to-speech. See setup instructions:"
        )
        tts_page.add(kokoro_group)

        # Link to Kokoro-FastAPI setup
        setup_row = Adw.ActionRow()
        setup_row.set_title("Setup Guide")
        setup_row.set_subtitle("github.com/remsky/Kokoro-FastAPI")
        setup_row.set_activatable(True)
        link_btn = Gtk.LinkButton(uri="https://github.com/remsky/Kokoro-FastAPI", label="Open")
        link_btn.set_valign(Gtk.Align.CENTER)
        setup_row.add_suffix(link_btn)
        kokoro_group.add(setup_row)

        tts_host = Adw.EntryRow()
        tts_host.set_title("Host")
        tts_host.set_text(str(config.get("tts.host", "localhost")))
        tts_host.connect("changed", lambda r: config.set("tts.host", r.get_text()))
        kokoro_group.add(tts_host)

        tts_port = Adw.EntryRow()
        tts_port.set_title("Port")
        tts_port.set_text(str(config.get("tts.port", 8880)))
        tts_port.connect("changed", lambda r: config.set("tts.port", int(r.get_text() or 8880)))
        kokoro_group.add(tts_port)
```

**Step 2: Run the app, click the Settings gear**

```bash
python main.py
```

Expected: Settings dialog opens with 3 tabs (LLM, Tools, TTS). Fields are pre-filled from config.json.

**Step 3: Commit**

```bash
git add app/settings_window.py
git commit -m "feat: settings window with LLM, Tools, TTS configuration"
```

---

## Task 9: CSS Styling

**Files:**
- Create: `app/style.css`
- Modify: `main.py` (load CSS)

**Step 1: Write app/style.css**

```css
/* app/style.css */

/* User message bubble */
.user-bubble {
  background-color: @accent_bg_color;
  color: @accent_fg_color;
  border-radius: 18px 18px 4px 18px;
  padding: 2px 4px;
}

/* Assistant message bubble */
.assistant-bubble {
  background-color: @card_bg_color;
  border-radius: 18px 18px 18px 4px;
  padding: 2px 4px;
}

/* Input row background */
.input-bar {
  background-color: @headerbar_bg_color;
  border-top: 1px solid @borders;
}
```

**Step 2: Load CSS in main.py**

In `AgentDemoApp.on_activate`, before `win.present()`, add:

```python
# Load CSS
css_provider = Gtk.CssProvider()
css_file = Path(__file__).parent / "app" / "style.css"
if css_file.exists():
    css_provider.load_from_path(str(css_file))
Gtk.StyleContext.add_provider_for_display(
    win.get_display(),
    css_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
)
```

Also add `from pathlib import Path` to imports.

**Step 3: Run and verify**

```bash
python main.py
```

Expected: User bubbles are blue (accent color). Assistant bubbles are card-colored. Input bar has a subtle top border.

**Step 4: Commit**

```bash
git add app/style.css main.py
git commit -m "feat: custom CSS for chat bubbles"
```

---

## Task 10: Wire Up Default Read Filename

The `read_file` tool should use the configured default filename when none is specified in the tool call. The tool schema's description should mention the default.

**Modify: `app/tools/read_file.py`**

In `execute()`, change:
```python
filename = args.get("filename", "note.txt")
```
to:
```python
from app import config
default = config.get("tools.default_read_filename", "note.txt")
filename = args.get("filename", default)
```

Also update the SCHEMA description to be dynamic — but since SCHEMA is module-level, compute it at call time instead. Replace the static `SCHEMA` dict with a function:

```python
# app/tools/read_file.py (revised)
from pathlib import Path


def get_schema() -> dict:
    from app import config
    default = config.get("tools.default_read_filename", "note.txt")
    return {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": f"Read a file from the current working directory. Default file: {default}",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": f"The filename to read (default: {default})"
                    }
                },
                "required": []  # Not required — use default if omitted
            }
        }
    }

SCHEMA = property(get_schema)  # Will be accessed via get_schema() instead


def execute(args: dict) -> dict:
    from app import config
    default = config.get("tools.default_read_filename", "note.txt")
    filename = args.get("filename", default)
    path = Path(filename)
    if not path.exists():
        return {"result": "", "error": f"File not found: {filename}"}
    try:
        content = path.read_text(encoding="utf-8")
        return {"result": content, "error": None}
    except Exception as e:
        return {"result": "", "error": str(e)}
```

**Update `app/tools/__init__.py`** to call `get_schema()` instead of accessing `.SCHEMA`:

```python
# In get_tool_schemas():
from app.tools import read_file, write_txt_file, tts

_SCHEMA_MAP = {
    "read_file": read_file.get_schema,
    "write_txt_file": lambda: write_txt_file.SCHEMA,
    "tts_generate_audio": lambda: tts.SCHEMA,
}

def get_tool_schemas(enabled_tools: list[str]) -> list[dict]:
    return [_SCHEMA_MAP[name]() for name in enabled_tools if name in _SCHEMA_MAP]
```

**Run tests to ensure nothing broke:**

```bash
pytest tests/ -v
```

Expected: All tests still pass (update test expectations if needed for `get_schema` vs `SCHEMA`).

**Commit:**

```bash
git add app/tools/
git commit -m "feat: read_file uses configured default filename from settings"
```

---

## Task 11: README + config.json.example

**Files:**
- Create: `README.md`

**Step 1: Write README.md**

```markdown
# What is an Agent?

A live demonstration app showing Anthropic's paradigm: **"Agents are LLMs using tools in a loop."**

Built with GTK4 + libadwaita for a native Linux desktop experience. Watch an LLM stream tokens, call local tools (file read/write, text-to-speech), and loop until the task is complete.

Made by [Josh Müller](https://joshmuller.ca)

---

## Features

- **Streaming chat** with Ollama (local) or OpenRouter (cloud)
- **Agentic tool loop** — LLM calls tools and keeps going until done
- **Tools:** `read_file`, `write_txt_file`, `tts_generate_audio`
- **Responsive layout** — works narrow or fullscreen
- **Live tool toggles** with visual feedback

## Requirements

### System packages (Arch Linux)

```bash
sudo pacman -S python-gobject gtk4 libadwaita
```

For other distros:
- **Ubuntu/Debian:** `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1`
- **Fedora:** `sudo dnf install python3-gobject gtk4 libadwaita`

### Python packages

```bash
pip install requests
```

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/joshmuller/what-is-an-agent
cd what-is-an-agent
```

### 2. Configure

```bash
cp config.json.example config.json
```

Edit `config.json`:
- Set your **Ollama host** if not running locally
- Add your **OpenRouter API key** (or set `OPENROUTER_API_KEY` env var)
- Set your **Kokoro TTS host** if using TTS

### 3. Run

```bash
python main.py
```

## LLM Providers

### Ollama (local)
Install Ollama from [ollama.ai](https://ollama.ai), then pull a model:
```bash
ollama pull gemma3:27b
```

### OpenRouter (cloud)
Get a free API key at [openrouter.ai](https://openrouter.ai). Set it in Settings or:
```bash
export OPENROUTER_API_KEY=your_key_here
python main.py
```

## TTS Setup (optional)

The `tts_generate_audio` tool requires a running [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) instance.

```bash
docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi:latest
```

Then set the host/port in Settings.

## Supported TTS Languages

| Language | Code |
|----------|------|
| English | `en` |
| French | `fr` |
| Spanish | `es` |
| Portuguese | `pt` |
| Italian | `it` |
| Hindi | `hi` |
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions"
```

---

## Task 12: End-to-End Smoke Test

**This is a manual checklist — run through before the presentation.**

1. `python main.py` — window opens
2. Type "Hello!" → streaming response appears
3. Enable `read_file` tool → context clears → type "Read note.txt and summarize it" → agent calls tool, shows result
4. Enable `write_txt_file` → type "Write a haiku to haiku.txt" → agent creates file → verify `cat haiku.txt`
5. Enable `tts_generate_audio` → type "Say 'Bonjour tout le monde' in French, save to bonjour.wav" → audio file created → ▶ Play button works
6. Switch provider to OpenRouter → verify streaming still works
7. Open Settings → change Ollama model → close → verify model row updates in sidebar
8. Resize window narrow → sidebar collapses to overlay → hamburger button appears
9. Clear button → chat clears

**All passing? Final commit:**

```bash
git add -A
git commit -m "chore: final cleanup and smoke test complete"
```

---

## Execution Notes

- GTK must be tested visually — there's no headless test mode without `Xvfb`
- Config tests use `monkeypatch.chdir(tmp_path)` to isolate filesystem
- Tool tests mock HTTP calls — no real Ollama/OpenRouter/Kokoro needed for tests
- Run `pytest tests/ -v` after every task to catch regressions
