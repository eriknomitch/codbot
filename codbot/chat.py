"""Back-and-forth conversations: answer each question in light of the earlier ones, and save both sides."""

from codbot.answer import Answerer
from codbot.history import History


class Chat:
    def __init__(self, answerer: Answerer | None = None, history: History | None = None) -> None:
        self.answerer = answerer or Answerer()
        self.history = history or History()

    async def send(self, question: str, conversation_id: str | None = None) -> tuple[str, str]:
        """Answer a question, continuing conversation_id or starting a new conversation.

        Returns (conversation_id, answer). Raises KeyError if conversation_id doesn't exist.
        """
        if conversation_id is not None and not self.history.exists(conversation_id):
            raise KeyError(conversation_id)
        earlier = self.history.messages(conversation_id) if conversation_id else []
        answer = await self.answerer.ask(question, earlier)
        # Save only once the model has answered, so a failed call leaves no half-finished exchange behind.
        if conversation_id is None:
            conversation_id = self.history.create(title=question)
        self.history.add(conversation_id, "user", question)
        self.history.add(conversation_id, "assistant", answer)
        return conversation_id, answer
