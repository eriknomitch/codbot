"""Answer questions about the knowledge base via OpenRouter."""

import os

from openai import AsyncOpenAI

from codbot.kb import load_documents

# An OpenRouter model's canonical_slug, as listed by https://openrouter.ai/api/v1/models.
DEFAULT_MODEL = "anthropic/claude-opus-5.5-20260921"

INSTRUCTIONS = """You answer questions using the knowledge base below.
Base your answers on the documents. If they don't cover the question, say so plainly rather than guessing.
When useful, cite the document path(s) you relied on. If the knowledge base marks a fact as unofficial, reported,
or fast-changing (like meta or tier lists), pass that caveat on. Keep answers concise: they are often shown in Discord."""


class Answerer:
    def __init__(self) -> None:
        # OpenRouter speaks the OpenAI Chat Completions API.
        self.client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPEN_ROUTER_API_KEY"])
        self.model = os.environ.get("OPEN_ROUTER_MODEL") or DEFAULT_MODEL
        self.reload()

    def reload(self) -> None:
        """Re-read the knowledge base from disk."""
        self.system = {
            "role": "system",
            "content": [
                {"type": "text", "text": INSTRUCTIONS},
                # Large, stable block: cache it so repeat questions are cheap and fast. Anthropic models need this
                # breakpoint; OpenRouter maps it for other providers that cache explicitly, and others cache automatically.
                {
                    "type": "text",
                    "text": f"<knowledge_base>\n{load_documents()}\n</knowledge_base>",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
        }

    async def ask(self, question: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=16000,
            messages=[self.system, {"role": "user", "content": question}],
            # OpenRouter-only field: think at medium effort, and leave the reasoning out of the response.
            extra_body={"reasoning": {"effort": "medium", "exclude": True}},
        )

        choice = response.choices[0]
        if choice.finish_reason == "content_filter" or choice.message.refusal:
            return "Sorry, I can't help with that one."
        return (choice.message.content or "").strip()
