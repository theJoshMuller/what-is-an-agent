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


def stream(messages: list, tools: list) -> Generator[StreamChunk, None, None]:
    host = config.get("ollama.host", "localhost")
    port = config.get("ollama.port", 11434)
    model = config.get("ollama.model", "ministral-3:14b-instruct-2512-q8_0")
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
    except requests.exceptions.ConnectionError:
        yield StreamChunk(error=f"Cannot connect to Ollama at {host}:{port}. Is Ollama running?")
    except requests.exceptions.HTTPError as e:
        body = e.response.text[:300] if e.response else ""
        yield StreamChunk(error=f"Ollama API error: {e.response.status_code} — {body}")
    except Exception as e:
        yield StreamChunk(error=str(e))
