"""Discord bot implementation."""

import discord
from discord import app_commands

from secureclaw.agent.core import Agent
from secureclaw.discord.security import (
    RateLimiter,
    UserAllowlist,
    detect_prompt_injection,
)
from secureclaw.logging import get_logger
from secureclaw.memory.qdrant import QdrantMemory

log = get_logger("secureclaw.discord.bot")


class SecureClawBot(discord.Client):
    """SecureClaw Discord bot."""

    def __init__(self, memory: QdrantMemory) -> None:
        """Initialize the bot.

        Args:
            memory: The memory system.
        """
        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True

        super().__init__(intents=intents)

        self._memory = memory
        self._agent: Agent | None = None
        self._tree = app_commands.CommandTree(self)
        self._rate_limiter = RateLimiter()
        self._allowlist = UserAllowlist()

        self._setup_commands()

    def _setup_commands(self) -> None:
        """Set up slash commands."""

        @self._tree.command(name="ask", description="Ask SecureClaw a question")
        async def ask_command(interaction: discord.Interaction, question: str) -> None:
            await self._handle_ask(interaction, question)

        @self._tree.command(name="remember", description="Ask SecureClaw to remember something")
        async def remember_command(interaction: discord.Interaction, content: str) -> None:
            await self._handle_remember(interaction, content)

        @self._tree.command(name="search", description="Search your memories")
        async def search_command(interaction: discord.Interaction, query: str) -> None:
            await self._handle_search(interaction, query)

        @self._tree.command(name="ping", description="Check if SecureClaw is online")
        async def ping_command(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(
                f"🦀 Pong! Latency: {round(self.latency * 1000)}ms",
                ephemeral=True,
            )

    async def setup_hook(self) -> None:
        """Called when the bot is ready to set up."""
        # Initialize agent after bot is ready
        self._agent = Agent(memory=self._memory)

        # Sync commands
        await self._tree.sync()
        log.info("commands_synced")

    async def on_ready(self) -> None:
        """Called when the bot is fully ready."""
        log.info(
            "bot_ready",
            user=str(self.user),
            guilds=len(self.guilds),
        )

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages."""
        # Ignore own messages
        if message.author == self.user:
            return

        # Ignore messages from bots
        if message.author.bot:
            return

        # Only respond to DMs or mentions
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.user in message.mentions if self.user else False

        if not (is_dm or is_mention):
            return

        # Check allowlist
        if not self._allowlist.is_allowed(message.author.id):
            log.warning("user_not_allowed", user_id=message.author.id)
            await message.reply(
                "Sorry, you're not authorized to use this bot.",
                mention_author=False,
            )
            return

        # Check rate limit
        allowed, warning = self._rate_limiter.check(message.author.id)
        if not allowed:
            if warning:
                await message.reply(warning, mention_author=False)
            return

        # Check for prompt injection
        if detect_prompt_injection(message.content):
            await message.reply(
                "I noticed some unusual patterns in your message. "
                "Could you rephrase your question?",
                mention_author=False,
            )
            return

        # Generate response
        async with message.channel.typing():
            content = message.content
            # Remove bot mention from content
            if is_mention and self.user:
                content = content.replace(f"<@{self.user.id}>", "").strip()

            if not content:
                await message.reply(
                    "How can I help you?",
                    mention_author=False,
                )
                return

            if self._agent is None:
                await message.reply(
                    "I'm still starting up. Please try again in a moment.",
                    mention_author=False,
                )
                return

            response = await self._agent.generate_response(
                user_id=message.author.id,
                channel_id=message.channel.id,
                message=content,
            )

            # Send response, splitting if too long
            await self._send_long_message(message.channel, response)

    async def _handle_ask(
        self,
        interaction: discord.Interaction,
        question: str,
    ) -> None:
        """Handle /ask command."""
        # Check allowlist
        if not self._allowlist.is_allowed(interaction.user.id):
            await interaction.response.send_message(
                "Sorry, you're not authorized to use this bot.",
                ephemeral=True,
            )
            return

        # Check rate limit
        allowed, warning = self._rate_limiter.check(interaction.user.id)
        if not allowed:
            await interaction.response.send_message(
                warning or "Rate limited. Please wait.",
                ephemeral=True,
            )
            return

        # Check for prompt injection
        if detect_prompt_injection(question):
            await interaction.response.send_message(
                "I noticed some unusual patterns in your question. "
                "Could you rephrase it?",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        if self._agent is None:
            await interaction.followup.send(
                "I'm still starting up. Please try again in a moment."
            )
            return

        response = await self._agent.generate_response(
            user_id=interaction.user.id,
            channel_id=interaction.channel_id or 0,
            message=question,
        )

        # Send response
        await interaction.followup.send(response)

    async def _handle_remember(
        self,
        interaction: discord.Interaction,
        content: str,
    ) -> None:
        """Handle /remember command."""
        if not self._allowlist.is_allowed(interaction.user.id):
            await interaction.response.send_message(
                "Sorry, you're not authorized to use this bot.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        if self._agent is None:
            await interaction.followup.send(
                "I'm still starting up. Please try again in a moment."
            )
            return

        confirmation = await self._agent.store_memory_from_request(content)
        await interaction.followup.send(confirmation)

    async def _handle_search(
        self,
        interaction: discord.Interaction,
        query: str,
    ) -> None:
        """Handle /search command."""
        if not self._allowlist.is_allowed(interaction.user.id):
            await interaction.response.send_message(
                "Sorry, you're not authorized to use this bot.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Search memories
        memories = await self._memory.search_memories(query=query, limit=5)

        if not memories:
            await interaction.followup.send("No matching memories found.")
            return

        # Format results
        lines = ["**Search Results:**\n"]
        for i, mem in enumerate(memories, 1):
            score_pct = int(mem["score"] * 100)
            lines.append(f"{i}. [{score_pct}%] {mem['content'][:200]}")

        await interaction.followup.send("\n".join(lines))

    async def _send_long_message(
        self,
        channel: discord.abc.Messageable,
        content: str,
        max_length: int = 2000,
    ) -> None:
        """Send a message, splitting if it exceeds Discord's limit.

        Args:
            channel: The channel to send to.
            content: The message content.
            max_length: Maximum message length.
        """
        if len(content) <= max_length:
            await channel.send(content)
            return

        # Split on paragraph boundaries if possible
        parts = []
        current = ""

        for line in content.split("\n"):
            if len(current) + len(line) + 1 <= max_length:
                current += line + "\n"
            else:
                if current:
                    parts.append(current.strip())
                current = line + "\n"

        if current:
            parts.append(current.strip())

        for part in parts:
            if part:
                await channel.send(part)
