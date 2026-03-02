# tests/test_ollama_message_format.py
"""Integration tests for Ollama message format correctness.

Reproduces the 400 errors that occur after multi-tool-call sequences
in the agentic loop. These tests send the exact message history format
that window.py builds to verify Ollama accepts it.

Requires a running Ollama instance at the configured host.
"""
import pytest
import requests


def setup_module(_):
    from app import config
    config.load()


def _chat(messages, tools=None):
    """POST to Ollama /api/chat, return (status_code, body_text)."""
    from app import config
    host = config.get("ollama.host", "localhost")
    port = config.get("ollama.port", 11434)
    model = config.get("ollama.model", "mistral-small3.2:latest")
    payload = {"model": model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    resp = requests.post(f"http://{host}:{port}/api/chat", json=payload, timeout=60)
    return resp.status_code, resp.text


READ_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file and return its contents.",
        "parameters": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": [],
        },
    },
}

WRITE_TOOL = {
    "type": "function",
    "function": {
        "name": "write_txt_file",
        "description": "Write text content to a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["filename", "content"],
        },
    },
}

TTS_TOOL = {
    "type": "function",
    "function": {
        "name": "tts_generate_audio",
        "description": "Convert text to speech.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "language": {"type": "string", "enum": ["en", "fr", "es", "pt", "it", "hi"]},
                "filename": {"type": "string"},
            },
            "required": ["text", "language", "filename"],
        },
    },
}


class TestOllamaToolCallHistory:
    """Verify the exact message formats built by window.py don't cause 400 errors."""

    def test_single_tool_call_history_accepted(self):
        """Single tool call + result → 200."""
        messages = [
            {"role": "user", "content": "Read note.txt"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_read1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": {"filename": "note.txt"},
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_read1",
                "content": "Josh loves his wife",
            },
        ]
        status, body = _chat(messages, tools=[READ_TOOL])
        assert status == 200, f"Expected 200, got {status}: {body[:300]}"

    def test_multi_tool_call_history_accepted(self):
        """Read + 3 writes history → 200 (the failing scenario in production)."""
        messages = [
            {
                "role": "user",
                "content": "Read note.txt and write Spanish, Italian, Portuguese translations",
            },
            # Turn 1: read
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_read1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": {},
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_read1", "content": "Josh loves his wife"},
            # Turn 2: 3 writes
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_write_es",
                        "type": "function",
                        "function": {
                            "name": "write_txt_file",
                            "arguments": {"filename": "es.txt", "content": "Josh ama a su esposa"},
                        },
                    },
                    {
                        "id": "call_write_it",
                        "type": "function",
                        "function": {
                            "name": "write_txt_file",
                            "arguments": {"filename": "it.txt", "content": "Josh ama sua moglie"},
                        },
                    },
                    {
                        "id": "call_write_pt",
                        "type": "function",
                        "function": {
                            "name": "write_txt_file",
                            "arguments": {"filename": "pt.txt", "content": "Josh ama sua esposa"},
                        },
                    },
                ],
            },
            {"role": "tool", "tool_call_id": "call_write_es", "content": "Wrote 21 chars to files/es.txt"},
            {"role": "tool", "tool_call_id": "call_write_it", "content": "Wrote 22 chars to files/it.txt"},
            {"role": "tool", "tool_call_id": "call_write_pt", "content": "Wrote 22 chars to files/pt.txt"},
        ]
        status, body = _chat(messages, tools=[READ_TOOL, WRITE_TOOL])
        assert status == 200, f"Expected 200, got {status}: {body[:300]}"

    def test_tts_tool_call_history_accepted(self):
        """TTS tool call + result → 200."""
        messages = [
            {"role": "user", "content": "Say hello in English"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_tts1",
                        "type": "function",
                        "function": {
                            "name": "tts_generate_audio",
                            "arguments": {"text": "Hello", "language": "en", "filename": "hello.wav"},
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_tts1",
                "content": "Audio saved to files/hello.wav (12000 bytes). Voice: af_heart.",
            },
        ]
        status, body = _chat(messages, tools=[TTS_TOOL])
        assert status == 200, f"Expected 200, got {status}: {body[:300]}"
