"""Discord front end: `/ask` slash command, or @mention the bot with a question.

Reply to one of the bot's answers (keeping the reply's mention on) to follow up in the same conversation.
"""

import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

from codbot.chat import Chat

log = logging.getLogger("codbot")
DISCORD_LIMIT = 2000


def chunks(text: str, size: int = DISCORD_LIMIT) -> list[str]:
    """Split text into Discord-sized messages, preferring line breaks."""
    out = []
    while len(text) > size:
        cut = text.rfind("\n", 0, size)
        cut = cut if cut > 0 else size
        out.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return out + [text] if text else out


class Codbot(discord.Client):
    def __init__(self, guild_id: int | None) -> None:
        # Default intents suffice: bots receive the content of messages that mention them.
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.guild = discord.Object(id=guild_id) if guild_id else None
        self.chat = Chat()

    def conversation_for(self, message_id: int) -> str | None:
        return self.chat.history.find(f"discord:{message_id}")

    def remember(self, conversation_id: str, messages: list[discord.Message]) -> None:
        """Link Discord messages to a conversation, so replying to any of them continues it."""
        for message in messages:
            self.chat.history.link(f"discord:{message.id}", conversation_id)

    async def setup_hook(self) -> None:
        if self.guild:
            # Guild sync is instant; global sync can take a while to propagate.
            self.tree.copy_global_to(guild=self.guild)
            await self.tree.sync(guild=self.guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("Logged in as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or self.user not in message.mentions:
            return
        question = message.content.replace(self.user.mention, "").replace(f"<@!{self.user.id}>", "").strip()
        if not question:
            await message.reply("Ask me something about the knowledge base!")
            return
        # A reply to a message from an earlier exchange continues that conversation; anything else starts a new one.
        reference = message.reference
        conversation_id = self.conversation_for(reference.message_id) if reference and reference.message_id else None
        async with message.channel.typing():
            conversation_id, answer = await self.chat.send(question, conversation_id)
        sent = [await message.reply(part, mention_author=False) for part in chunks(answer)]
        self.remember(conversation_id, [message, *sent])


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    bot = Codbot(int(guild_id) if guild_id else None)

    @bot.tree.command(description="Ask a question about the knowledge base")
    @app_commands.describe(question="What do you want to know?")
    async def ask(interaction: discord.Interaction, question: str) -> None:
        await interaction.response.defer(thinking=True)
        conversation_id, answer = await bot.chat.send(question)
        parts = chunks(f"> {question}\n\n{answer}")
        bot.remember(conversation_id, [await interaction.followup.send(part, wait=True) for part in parts])

    @bot.tree.command(description="Reload the knowledge base from disk")
    async def reload(interaction: discord.Interaction) -> None:
        bot.chat.answerer.reload()
        await interaction.response.send_message("Knowledge base reloaded.", ephemeral=True)

    bot.run(os.environ["DISCORD_TOKEN"], log_handler=None)


if __name__ == "__main__":
    main()
