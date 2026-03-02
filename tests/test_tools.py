# tests/test_tools.py
import json
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
    def test_calls_kokoro_api(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Need config loaded so tts.execute can call config.get
        from app import config
        import importlib
        importlib.reload(config)
        config.load()

        from app.tools.tts import execute
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"RIFF....fake_wav_data"
        with patch("requests.post", return_value=mock_response) as mock_post:
            result = execute({
                "text": "Hello world",
                "language": "en",
                "filename": "test.wav"
            })
        assert mock_post.called
        call_kwargs = mock_post.call_args
        # Voice should be af_heart for English
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json") or call_kwargs[0][1]
        assert payload.get("voice") == "af_heart"

    def test_french_uses_correct_voice(self):
        from app.tools.tts import VOICE_MAP
        assert VOICE_MAP["fr"] == "ff_siwis"

    def test_spanish_uses_correct_voice(self):
        from app.tools.tts import VOICE_MAP
        assert VOICE_MAP["es"] == "ef_dora"

    def test_unknown_language_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from app import config
        import importlib
        importlib.reload(config)
        config.load()
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

    def test_dispatch_unknown_tool(self):
        from app.tools import dispatch
        result = dispatch("nonexistent_tool", {})
        assert result["error"] is not None
