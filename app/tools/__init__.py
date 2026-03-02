# app/tools/__init__.py
from app.tools import read_file, write_txt_file, tts

_SCHEMA_MAP = {
    "read_file": read_file.get_schema,
    "write_txt_file": lambda: write_txt_file.SCHEMA,
    "tts_generate_audio": lambda: tts.SCHEMA,
}

_TOOL_MAP = {
    "read_file": read_file,
    "write_txt_file": write_txt_file,
    "tts_generate_audio": tts,
}


def get_tool_schemas(enabled_tools: list[str]) -> list[dict]:
    """Return OpenAI-format tool schemas for the enabled tools."""
    return [_SCHEMA_MAP[name]() for name in enabled_tools if name in _SCHEMA_MAP]


def dispatch(tool_name: str, args: dict) -> dict:
    """Execute a tool by name with the given args."""
    if tool_name not in _TOOL_MAP:
        return {"result": "", "error": f"Unknown tool: {tool_name}"}
    return _TOOL_MAP[tool_name].execute(args)
