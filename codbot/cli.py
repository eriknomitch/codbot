"""Ask the knowledge base from the terminal: `codbot "your question"`."""

import asyncio
import sys

from dotenv import load_dotenv

from codbot.answer import Answerer


def main() -> None:
    load_dotenv()
    if len(sys.argv) < 2:
        sys.exit('usage: codbot "your question"')
    print(asyncio.run(Answerer().ask(" ".join(sys.argv[1:]))))


if __name__ == "__main__":
    main()
