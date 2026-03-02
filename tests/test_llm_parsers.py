# tests/test_llm_parsers.py
import json
import pytest
from unittest.mock import MagicMock, patch


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

    def test_invalid_json_returns_error_chunk(self):
        from app.llm.ollama import _parse_chunk
        chunk = _parse_chunk("not json")
        assert chunk.error is not None


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

    def test_non_data_line_returns_none(self):
        from app.llm.openrouter import _parse_sse_line
        assert _parse_sse_line("event: message") is None


class TestStreamChunk:
    def test_default_chunk(self):
        from app.llm.base import StreamChunk
        chunk = StreamChunk()
        assert chunk.text == ""
        assert chunk.tool_calls == []
        assert chunk.done is False
        assert chunk.error is None
        assert chunk.thinking == ""

    def test_tool_call_dataclass(self):
        from app.llm.base import ToolCall
        tc = ToolCall(id="abc", name="read_file", arguments={"filename": "note.txt"})
        assert tc.name == "read_file"
        assert tc.arguments == {"filename": "note.txt"}


class TestOllamaThinkingParser:
    def test_thinking_token_parsed(self):
        from app.llm.ollama import _parse_chunk
        raw = json.dumps({
            "message": {"role": "assistant", "content": "", "thinking": "I need to write"},
            "done": False
        })
        chunk = _parse_chunk(raw)
        assert chunk.thinking == "I need to write"
        assert chunk.text == ""

    def test_chunk_without_thinking_has_empty_string(self):
        from app.llm.ollama import _parse_chunk
        raw = json.dumps({"message": {"content": "Hi"}, "done": False})
        chunk = _parse_chunk(raw)
        assert chunk.thinking == ""

    def test_thinking_and_tool_calls_in_final_chunk(self):
        from app.llm.ollama import _parse_chunk
        raw = json.dumps({
            "message": {
                "role": "assistant",
                "content": "",
                "thinking": "I should call the tool",
                "tool_calls": [{"id": "call_1", "function": {"name": "write_txt_file", "arguments": {"filename": "f.txt", "content": "hi"}}}]
            },
            "done": True
        })
        chunk = _parse_chunk(raw)
        assert chunk.thinking == "I should call the tool"
        assert len(chunk.tool_calls) == 1
        assert chunk.done is True
