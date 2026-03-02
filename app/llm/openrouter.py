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


def stream(messages: list, tools: list) -> Generator[StreamChunk, None, None]:
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
