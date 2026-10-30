"""Answer questions about the knowledge base with Claude."""

import os

import anthropic

from codbot.kb import load_documents

MODEL = os.environ.get("CODBOT_MODEL", "claude-opus-5-5")

INSTRUCTIONS = """You answer questions using the knowledge base below.
Base your answers on the documents. If they don't cover the question, say so plainly rather than guessing.
When useful, cite the document path(s) you relied on. If the knowledge base marks a fact as unofficial, reported,
or fast-changing (like meta or tier lists), pass that caveat on. Keep answers concise: they are often shown in Discord."""


class Answerer:
    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic()
        self.reload()

    def reload(self) -> None:
        """Re-read the knowledge base from disk."""
        self.system = [
            {"type": "text", "text": INSTRUCTIONS},
            # Large, stable block: cache it so repeat questions are cheap and fast.
            {
                "type": "text",
                "text": f"<knowledge_base>\n{load_documents()}\n</knowledge_base>",
                "cache_control": {"type": "ephemeral"},
            },
        ]

    async def ask(self, question: str) -> str:
        async with self.client.beta.messages.stream(
            model=MODEL,
            max_tokens=16000,
            system=self.system,
            messages=[{"role": "user", "content": question}],
            output_config={"effort": "medium"},
            # On a safety decline, the API retries on a fallback model automatically.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            response = await stream.get_final_message()

        if response.stop_reason == "refusal":
            return "Sorry, I can't help with that one."
        return "".join(b.text for b in response.content if b.type == "text").strip()
