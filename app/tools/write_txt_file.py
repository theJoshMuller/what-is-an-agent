# app/tools/write_txt_file.py
from pathlib import Path

SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_txt_file",
        "description": "Write text content to a file in the current working directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to write (e.g. output.txt)"
                },
                "content": {
                    "type": "string",
                    "description": "The text content to write to the file"
                }
            },
            "required": ["filename", "content"]
        }
    }
}


def execute(args: dict) -> dict:
    filename = args.get("filename", "output.txt")
    content = args.get("content", "")
    path = Path(filename)
    try:
        path.write_text(content, encoding="utf-8")
        return {"result": f"Successfully wrote {len(content)} characters to {filename}", "error": None}
    except Exception as e:
        return {"result": "", "error": str(e)}
