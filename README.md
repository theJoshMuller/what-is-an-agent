# What is an Agent?

> A live demonstration showing Anthropic's paradigm: **"Agents are LLMs using tools in a loop."**

Watch an LLM stream tokens, call local tools (file read/write, text-to-speech), and loop until the task is complete — all in a native Linux desktop app.

**Made by [Josh Müller](https://joshmuller.ca)**

---

## Features

- **Streaming chat** — tokens appear in real-time as the LLM generates them
- **Agentic tool loop** — the LLM can call tools and keep going until the task is done
- **Three tools:**
  - `read_file` — read a file from the working directory
  - `write_txt_file` — write a text file to the working directory
  - `tts_generate_audio` — convert text to speech (requires Kokoro TTS)
- **Two LLM providers** — Ollama (local) or OpenRouter (cloud), switchable in the sidebar
- **Responsive layout** — works in a narrow window or fullscreen
- **Native Linux UI** — GTK4 + libadwaita (respects your system dark/light theme)

---

## Requirements

### System packages

**Arch Linux:**
```bash
sudo pacman -S python-gobject gtk4 libadwaita
```

**Ubuntu / Debian:**
```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

**Fedora:**
```bash
sudo dnf install python3-gobject gtk4 libadwaita
```

> ⚠️ Do **not** install `PyGObject` via pip on Arch Linux — always use pacman.

### Python packages

```bash
pip install requests
```

---

## Setup

### 1. Clone

```bash
git clone https://github.com/theJoshMuller/what-is-an-agent
cd what-is-an-agent
```

### 2. Install system deps (see above)

### 3. Install Python deps

```bash
pip install requests
```

### 4. Configure

```bash
cp config.json.example config.json
```

Edit `config.json` to set your Ollama host, OpenRouter API key, and/or Kokoro TTS host.

### 5. Run

```bash
python main.py
```

---

## LLM Providers

### Ollama (local, default)

Install [Ollama](https://ollama.ai), then pull the default model:

```bash
ollama pull gemma3:27b
```

If Ollama is running on a different machine, update `ollama.host` in Settings or `config.json`.

### OpenRouter (cloud)

Get a free API key at [openrouter.ai](https://openrouter.ai).

Either set it in the app's Settings window, or:

```bash
export OPENROUTER_API_KEY=your_key_here
python main.py
```

The app reads `$OPENROUTER_API_KEY` from the environment automatically.

---

## TTS (optional)

The `tts_generate_audio` tool requires a running [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) instance.

**Quick start with Docker:**

```bash
docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi:latest
```

Then enable TTS in the sidebar and set the host in Settings if it's not on localhost.

**Supported languages:**

| Language | Code |
|----------|------|
| English | `en` |
| French | `fr` |
| Spanish | `es` |
| Portuguese | `pt` |
| Italian | `it` |
| Hindi | `hi` |

---

## Usage

1. **Type a message** and press Enter or click Send
2. **Enable tools** using the toggles in the right sidebar
3. **Switch models** using the Ollama / OpenRouter toggle in the sidebar
4. **Open Settings** (gear icon) to configure hosts, models, and API keys
5. **Clear context** with the trash icon in the header

---

## Project Structure

```
what-is-an-agent/
├── main.py                  # Entry point
├── app/
│   ├── window.py            # Main window + agentic loop
│   ├── chat_panel.py        # Streaming chat UI
│   ├── sidebar.py           # Tools toggles + model selector
│   ├── settings_window.py   # Settings dialog
│   ├── config.py            # Config load/save
│   ├── style.css            # Chat bubble styles
│   ├── llm/
│   │   ├── ollama.py        # Ollama streaming client
│   │   └── openrouter.py    # OpenRouter streaming client
│   └── tools/
│       ├── read_file.py
│       ├── write_txt_file.py
│       └── tts.py
├── config.json.example      # Template — copy to config.json
└── requirements.txt
```

---

*Made with ♥ by [Josh Müller](https://joshmuller.ca)*
