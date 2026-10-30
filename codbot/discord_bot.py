"""Discord front end: `/ask` slash command, or @mention the bot with a question."""

import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

from codbot.answer import Answerer

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
        self.answerer = Answerer()

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
        async with message.channel.typing():
            answer = await self.answerer.ask(question)
        for part in chunks(answer):
            await message.reply(part, mention_author=False)


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    bot = Codbot(int(guild_id) if guild_id else None)

    @bot.tree.command(description="Ask a question about the knowledge base")
    @app_commands.describe(question="What do you want to know?")
    async def ask(interaction: discord.Interaction, question: str) -> None:
        await interaction.response.defer(thinking=True)
        answer = await bot.answerer.ask(question)
        parts = chunks(f"> {question}\n\n{answer}")
        for part in parts:
            await interaction.followup.send(part)

    @bot.tree.command(description="Reload the knowledge base from disk")
    async def reload(interaction: discord.Interaction) -> None:
        bot.answerer.reload()
        await interaction.response.send_message("Knowledge base reloaded.", ephemeral=True)

    bot.run(os.environ["DISCORD_TOKEN"], log_handler=None)


if __name__ == "__main__":
    main()
