# app/tools/read_file.py
from pathlib import Path

FILES_DIR = Path("files")


def _ensure_dir():
    FILES_DIR.mkdir(exist_ok=True)


def get_schema() -> dict:
    from app import config
    default = config.get("tools.default_read_filename", "note.txt")
    return {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                f"Read a file from the ./files/ directory and return its contents. "
                f"Default file: {default}. "
                f"If the user says 'read the file', 'read the note', or does not specify a filename, "
                f"call this tool with no arguments to read the default file ({default})."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": (
                            f"Filename inside ./files/ to read. "
                            f"Omit to use the default ({default})."
                        )
                    }
                },
                "required": []
            }
        }
    }


def execute(args: dict) -> dict:
    from app import config
    _ensure_dir()
    default = config.get("tools.default_read_filename", "note.txt")
    filename = args.get("filename", default)
    # Strip any path separators — files always live in ./files/
    filename = Path(filename).name
    path = FILES_DIR / filename
    if not path.exists():
        return {"result": "", "error": f"File not found: files/{filename}"}
    try:
        content = path.read_text(encoding="utf-8")
        return {"result": content, "error": None}
    except Exception as e:
        return {"result": "", "error": str(e)}
