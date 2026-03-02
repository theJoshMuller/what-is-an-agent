# app/tools/read_file.py
from pathlib import Path


def get_schema() -> dict:
    from app import config
    default = config.get("tools.default_read_filename", "note.txt")
    return {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": f"Read a file from the current working directory and return its contents. Default file: {default}",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": f"The filename to read (default: {default})"
                    }
                },
                "required": []
            }
        }
    }

# Also expose as SCHEMA for backwards compat
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
                    "description": "The filename to read"
                }
            },
            "required": []
        }
    }
}


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
