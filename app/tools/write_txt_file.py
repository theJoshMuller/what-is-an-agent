# app/tools/write_txt_file.py
from pathlib import Path

FILES_DIR = Path("files")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_txt_file",
        "description": "Write text content to a file inside the ./files/ directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename to write inside ./files/ (e.g. haiku.txt)"
                },
                "content": {
                    "type": "string",
                    "description": "The text content to write"
                }
            },
            "required": ["filename", "content"]
        }
    }
}


def execute(args: dict) -> dict:
    FILES_DIR.mkdir(exist_ok=True)
    filename = Path(args.get("filename", "output.txt")).name  # strip any path prefix
    content = args.get("content", "")
    path = FILES_DIR / filename
    try:
        path.write_text(content, encoding="utf-8")
        return {
            "result": f"Successfully wrote {len(content)} characters to files/{filename}",
            "error": None
        }
    except Exception as e:
        return {"result": "", "error": str(e)}
