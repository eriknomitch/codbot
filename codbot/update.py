"""Refresh knowledge base files from the web: `codbot-update [path ...]`.

Each file is sent to the model along with the whole knowledge base; the model searches the web for anything new or
changed and returns the full updated file, which is written back in place. Review the result with `git diff`.
"""

import asyncio
import datetime
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from codbot.answer import Answerer
from codbot.kb import knowledge_dir

# Updating a whole file can take several searches.
MAX_SEARCHES = 10
UNCHANGED = "NO_CHANGES"

PROMPT = """Today is {today}. Update the knowledge base file `{path}` (shown below) with current information from the web.

- Search for anything in it that is out of date, and for important new facts that belong in it.
- Keep its structure, headings, tone, and links. Change only what the web shows has changed or is missing.
- Prefer official sources. Link the source for every fact you add or change, and update any "updated"/"checked" dates.
- Mark unofficial or fast-changing facts as such, the way the rest of the knowledge base does.
- Don't remove facts just because you couldn't find them online.

If nothing needs changing, reply with only {unchanged}. Otherwise reply with the complete updated file inside
<updated_file></updated_file> tags, and nothing else.

<current_file path="{path}">
{content}
</current_file>"""


async def update_file(answerer: Answerer, rel: str) -> bool:
    """Update one file in place. Returns whether it changed."""
    path = knowledge_dir() / rel
    content = path.read_text(encoding="utf-8")
    prompt = PROMPT.format(today=datetime.date.today().isoformat(), path=rel, content=content, unchanged=UNCHANGED)
    # Reuse the cached system prompt so the knowledge base gives context on what the other files already cover.
    reply = await answerer.complete([answerer.system, {"role": "user", "content": prompt}], max_searches=MAX_SEARCHES)

    match = re.search(r"<updated_file>\s*(.*?)\s*</updated_file>", reply, re.DOTALL)
    if not match:
        if UNCHANGED not in reply:
            print(f"{rel}: unexpected reply, left unchanged:\n{reply}", file=sys.stderr)
        return False
    updated = match.group(1).strip() + "\n"
    if updated == content:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


async def run(paths: list[str]) -> None:
    root = knowledge_dir()
    # Paths can be given relative to the current directory (knowledge/glossary.md) or to the knowledge base (glossary.md).
    files = [Path(p) if Path(p).exists() else root / p for p in paths] if paths else sorted(root.rglob("*.md"))
    rels = [p.resolve().relative_to(root.resolve()).as_posix() for p in files]
    answerer = Answerer()
    for rel in rels:
        print(f"{rel}: {'updated' if await update_file(answerer, rel) else 'no changes'}")


def main() -> None:
    load_dotenv()
    asyncio.run(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
