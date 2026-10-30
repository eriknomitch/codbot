"""Load the Markdown knowledge base from disk."""

import os
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def knowledge_dir() -> Path:
    return Path(os.environ.get("CODBOT_KNOWLEDGE_DIR", DEFAULT_DIR))


def load_documents(root: Path | None = None) -> str:
    """Concatenate every .md file under root into one tagged string.

    Files are sorted so the output is byte-stable, which keeps the prompt cache warm.
    """
    root = root or knowledge_dir()
    parts = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        parts.append(f'<document path="{rel}">\n{path.read_text(encoding="utf-8").strip()}\n</document>')
    if not parts:
        raise RuntimeError(f"No .md files found in {root}")
    return "\n\n".join(parts)
