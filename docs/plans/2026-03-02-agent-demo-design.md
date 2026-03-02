# Agent Demo — Design Document
**Date:** 2026-03-02
**Author:** Josh Müller · joshmuller.ca

## Purpose

A GTK4 + libadwaita desktop app that demonstrates the concept of an AI agent — "an LLM using tools in a loop" — for a live presentation. The app lets an audience watch an LLM stream tokens, call local tools, and loop until the task is complete.

---

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| UI | GTK4 + libadwaita (Python) | Native Arch/GNOME look, no browser required |
| Async/streaming | Python threads + `GLib.idle_add` | Standard GTK streaming pattern, no exotic deps |
| LLM HTTP | `requests` (streaming) | Simple, universal |
| Audio playback | `subprocess aplay` | Available on all Linux distros |
| Config | `config.json` in working dir | Simple, portable |

---

## UI Layout

Two-panel layout using `Adw.OverlaySplitView`:

- **Wide mode**: Chat on left, sidebar (tools + model + status + branding) on right
- **Narrow mode**: Chat fills full width, sidebar slides in as overlay via hamburger button

### Header Bar
- App title: "What is an Agent?"
- Left: sidebar toggle (hamburger, narrow mode only)
- Right: Clear context button + Settings gear

### Chat Panel (left / full-width in narrow)
- Scrollable message list with distinct user/assistant bubbles
- Assistant bubble streams tokens in real-time
- Tool calls shown as inline status chips: `[Using tool: read_file]`
- Tool results shown as collapsible inline cards
- TTS tool results include a ▶ Play button

### Sidebar (right / overlay in narrow)
- **Tools** section: three toggle rows (read_file, write_txt_file, tts_generate_audio)
  - Toggling any tool clears the conversation context (required — tool schemas change)
- **Model** section: Ollama / OpenRouter radio + dropdown for model name
- **Status** indicator: Ready / Thinking / Running tool
- **Branding**: "Made by Josh Müller · joshmuller.ca"

### Input Row (pinned to bottom)
- Text entry + Send button
- Disabled during LLM generation

---

## Tools

### `read_file`
```json
{
  "name": "read_file",
  "description": "Read a file from the current working directory",
  "parameters": {
    "filename": { "type": "string", "description": "Filename to read (default: note.txt)" }
  }
}
```

### `write_txt_file`
```json
{
  "name": "write_txt_file",
  "description": "Write text content to a file in the current working directory",
  "parameters": {
    "filename": { "type": "string" },
    "content": { "type": "string" }
  }
}
```

### `tts_generate_audio`
```json
{
  "name": "tts_generate_audio",
  "description": "Convert text to speech using Kokoro TTS and save to a file",
  "parameters": {
    "text": { "type": "string" },
    "language": { "type": "string", "enum": ["en", "fr", "es", "pt", "it", "hi"] },
    "filename": { "type": "string", "description": "Output filename (e.g. output.wav)" }
  }
}
```

#### Default Female Voices per Language
| Language | Code | Voice |
|----------|------|-------|
| English | `en` | `af_heart` |
| French | `fr` | `ff_siwis` |
| Spanish | `es` | `ef_dora` |
| Portuguese | `pt` | `pf_dora` |
| Italian | `it` | `if_sara` |
| Hindi | `hi` | `hf_alpha` |

Kokoro API endpoint: `POST http://{host}:{port}/v1/audio/speech`
Response: audio bytes saved to `{filename}` in working dir, then played via `aplay`.

---

## Agentic Loop

```
User sends message
  → Append to messages[]
  → POST to Ollama/OpenRouter with enabled tool schemas
  → Stream response tokens to chat bubble
  → If response contains tool_calls:
      → Show "[Using tool: X]" chip in chat
      → Execute tool locally
      → Append tool result as role:tool message
      → Loop (re-POST)
  → Else: done, re-enable input
```

---

## LLM Providers

### Ollama
- API: `POST http://{host}:{port}/api/chat`
- Format: Ollama native JSON with tool_calls support
- Default model: `gemma3:27b`
- Default host: `localhost:11434`

### OpenRouter
- API: `POST https://openrouter.ai/api/v1/chat/completions`
- Format: OpenAI-compatible with streaming
- Default model: `qwen/qwen3-235b-a22b-2507`
- API key: read from `$OPENROUTER_API_KEY` env var (overridable in settings)

---

## Settings Window (`AdwPreferencesWindow`)

| Group | Setting | Default |
|-------|---------|---------|
| LLM | Active provider | Ollama |
| Ollama | Host | `localhost` |
| Ollama | Port | `11434` |
| Ollama | Model | `gemma3:27b` |
| OpenRouter | Model | `qwen/qwen3-235b-a22b-2507` |
| OpenRouter | API Key | `$OPENROUTER_API_KEY` env var |
| Tools | Default read filename | `note.txt` |
| TTS | Kokoro host | `localhost` |
| TTS | Kokoro port | `8880` |
| TTS | Setup link | https://github.com/remsky/Kokoro-FastAPI |

Config persisted to `config.json` in the working directory.

---

## File Structure

```
what-is-an-agent/
├── main.py                  # Entry point
├── app/
│   ├── __init__.py
│   ├── window.py            # Main AdwApplicationWindow
│   ├── chat_panel.py        # Chat message list + streaming
│   ├── sidebar.py           # Tools toggles + model selector
│   ├── settings_window.py   # AdwPreferencesWindow
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── ollama.py        # Ollama streaming client
│   │   └── openrouter.py    # OpenRouter streaming client
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── read_file.py
│   │   ├── write_txt_file.py
│   │   └── tts.py
│   └── config.py            # Config load/save
├── config.json.example      # Template config for new users
├── requirements.txt
└── README.md
```

---

## Setup for New Users

```bash
# 1. Install Python GTK4 deps (Arch Linux)
sudo pacman -S python-gobject gtk4 libadwaita

# 2. Install Python deps
pip install -r requirements.txt

# 3. Configure
cp config.json.example config.json
# Edit config.json with your Ollama/OpenRouter settings

# 4. Run
python main.py
```

`requirements.txt` will only contain `requests` (for HTTP streaming) — GTK/GLib are system packages.

---

## Branding

- Window subtitle or sidebar footer: "Made by Josh Müller · joshmuller.ca"
- Clean libadwaita default theme (respects system dark/light mode)
