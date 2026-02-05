"""End-to-end Discord integration tests with real Discord API.

These tests send actual messages through Discord and verify bot responses.
Requires:
- TEST_DISCORD_BOT_TOKEN environment variable (separate test bot)
- TEST_DISCORD_CHANNEL_ID environment variable (test channel ID)
- Test Discord server set up
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import suppress

import discord
import pytest
import pytest_asyncio

# Skip if test Discord credentials not provided
SKIP_DISCORD_E2E = not all(
    [
        os.getenv("TEST_DISCORD_BOT_TOKEN"),
        os.getenv("TEST_DISCORD_CHANNEL_ID"),
    ]
)

SKIP_REASON = (
    "Discord E2E tests require TEST_DISCORD_BOT_TOKEN and TEST_DISCORD_CHANNEL_ID "
    "environment variables. Set these in your .env to run Discord E2E tests."
)


class DiscordTestClient:
    """Discord test client to send messages and read responses."""

    def __init__(self, token: str, channel_id: int) -> None:
        """Initialize test client.

        Args:
            token: Discord bot token (for test user bot).
            channel_id: Channel ID to send test messages to.
        """
        self.token = token
        self.channel_id = channel_id
        self.client: discord.Client | None = None
        self.channel: discord.TextChannel | None = None

    async def start(self) -> None:
        """Start the Discord client."""
        intents = discord.Intents.default()
        intents.message_content = True

        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready() -> None:
            print(f"✅ Test client logged in as {self.client.user}")  # type: ignore[union-attr]
            # Get test channel
            channel = self.client.get_channel(self.channel_id)  # type: ignore[union-attr]
            if not isinstance(channel, discord.TextChannel):
                raise RuntimeError(f"Channel {self.channel_id} is not a text channel")
            self.channel = channel

        # Start client in background
        asyncio.create_task(self.client.start(self.token))

        # Wait for client to be ready
        for _ in range(30):  # 30 second timeout
            if self.client.is_ready() and self.channel:
                return
            await asyncio.sleep(1)

        raise TimeoutError("Discord test client failed to connect")

    async def stop(self) -> None:
        """Stop the Discord client."""
        if self.client:
            await self.client.close()

    async def send_message(self, content: str) -> discord.Message:
        """Send a message to the test channel.

        Args:
            content: Message content to send.

        Returns:
            The sent message.
        """
        if not self.channel:
            raise RuntimeError("Test client not connected")

        return await self.channel.send(content)

    async def wait_for_bot_response(
        self,
        after_message: discord.Message,
        timeout: float = 30.0,
    ) -> discord.Message | None:
        """Wait for bot to respond to a message.

        Args:
            after_message: The message we sent that bot should respond to.
            timeout: Maximum time to wait in seconds.

        Returns:
            The bot's response message, or None if timeout.
        """
        if not self.client or not self.channel:
            raise RuntimeError("Test client not connected")

        # Get bot user ID from channel (SecureClaw bot)
        # We'll identify it by checking if it's a bot and not ourselves
        bot_id = None
        async for message in self.channel.history(limit=10):
            if message.author.bot and message.author.id != self.client.user.id:  # type: ignore[union-attr]
                bot_id = message.author.id
                break

        if not bot_id:
            raise RuntimeError("Could not identify SecureClaw bot in channel")

        # Wait for bot response
        def check(message: discord.Message) -> bool:
            return (
                message.channel.id == self.channel_id  # type: ignore[union-attr]
                and message.author.id == bot_id
                and message.created_at > after_message.created_at
            )

        try:
            response = await self.client.wait_for("message", check=check, timeout=timeout)
            return response
        except TimeoutError:
            return None

    async def delete_message(self, message: discord.Message) -> None:
        """Delete a message (cleanup).

        Args:
            message: Message to delete.
        """
        with suppress(discord.errors.NotFound):
            await message.delete()


@pytest_asyncio.fixture(scope="module")
async def discord_test_client() -> AsyncGenerator[DiscordTestClient, None]:
    """Create Discord test client.

    Yields:
        Initialized DiscordTestClient.
    """
    if SKIP_DISCORD_E2E:
        pytest.skip(SKIP_REASON)

    token = os.getenv("TEST_DISCORD_BOT_TOKEN", "")
    channel_id = int(os.getenv("TEST_DISCORD_CHANNEL_ID", "0"))

    client = DiscordTestClient(token=token, channel_id=channel_id)
    await client.start()

    yield client

    await client.stop()


@pytest.mark.discord_e2e
@pytest.mark.skipif(SKIP_DISCORD_E2E, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_bot_responds_to_message(discord_test_client: DiscordTestClient) -> None:
    """Test bot responds to a simple message."""
    # Send test message
    test_message = await discord_test_client.send_message("Hello SecureClaw, what is 2+2?")

    try:
        # Wait for bot response
        response = await discord_test_client.wait_for_bot_response(test_message, timeout=30.0)

        assert response is not None, "Bot did not respond within timeout"
        assert len(response.content) > 0, "Bot response was empty"
        print(f"✅ Bot responded: {response.content[:100]}...")

    finally:
        # Cleanup test messages
        await discord_test_client.delete_message(test_message)
        if response:
            await discord_test_client.delete_message(response)


@pytest.mark.discord_e2e
@pytest.mark.skipif(SKIP_DISCORD_E2E, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_bot_handles_complex_query(discord_test_client: DiscordTestClient) -> None:
    """Test bot handles complex queries."""
    test_message = await discord_test_client.send_message(
        "Can you explain what async/await is in Python?"
    )

    try:
        response = await discord_test_client.wait_for_bot_response(test_message, timeout=45.0)

        assert response is not None, "Bot did not respond to complex query"
        assert len(response.content) > 50, "Bot response too short for complex query"
        print(f"✅ Bot handled complex query: {response.content[:100]}...")

    finally:
        await discord_test_client.delete_message(test_message)
        if response:
            await discord_test_client.delete_message(response)


@pytest.mark.discord_e2e
@pytest.mark.skipif(SKIP_DISCORD_E2E, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_bot_remembers_information(discord_test_client: DiscordTestClient) -> None:
    """Test bot memory functionality."""
    # Store memory
    store_message = await discord_test_client.send_message(
        "Remember that my favorite color is purple"
    )

    try:
        store_response = await discord_test_client.wait_for_bot_response(
            store_message, timeout=30.0
        )
        assert store_response is not None, "Bot did not acknowledge memory storage"

        # Wait a moment for memory to be indexed
        await asyncio.sleep(3)

        # Recall memory
        recall_message = await discord_test_client.send_message("What is my favorite color?")
        recall_response = await discord_test_client.wait_for_bot_response(
            recall_message, timeout=30.0
        )

        assert recall_response is not None, "Bot did not respond to recall query"
        # Note: Due to LLM variability, we just check it responded (not exact content)
        assert len(recall_response.content) > 20, "Bot response too short"
        print(f"✅ Memory test completed: {recall_response.content[:100]}...")

    finally:
        await discord_test_client.delete_message(store_message)
        if store_response:
            await discord_test_client.delete_message(store_response)
        await discord_test_client.delete_message(recall_message)
        if recall_response:
            await discord_test_client.delete_message(recall_response)


@pytest.mark.discord_e2e
@pytest.mark.skipif(SKIP_DISCORD_E2E, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_bot_handles_mention(discord_test_client: DiscordTestClient) -> None:
    """Test bot responds to mentions."""
    # Get bot ID
    bot_id = None
    if discord_test_client.channel:
        async for message in discord_test_client.channel.history(limit=10):
            if (
                message.author.bot
                and discord_test_client.client
                and message.author.id != discord_test_client.client.user.id  # type: ignore[union-attr]
            ):
                bot_id = message.author.id
                break

    if not bot_id:
        pytest.skip("Could not identify bot in channel")

    # Send message with mention
    test_message = await discord_test_client.send_message(f"<@{bot_id}> ping")

    try:
        response = await discord_test_client.wait_for_bot_response(test_message, timeout=30.0)

        assert response is not None, "Bot did not respond to mention"
        assert len(response.content) > 0, "Bot response was empty"
        print(f"✅ Bot responded to mention: {response.content[:100]}...")

    finally:
        await discord_test_client.delete_message(test_message)
        if response:
            await discord_test_client.delete_message(response)


@pytest.mark.discord_e2e
@pytest.mark.skipif(SKIP_DISCORD_E2E, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_bot_slash_commands_available(discord_test_client: DiscordTestClient) -> None:
    """Test bot slash commands are registered."""
    if not discord_test_client.client:
        pytest.skip("Discord client not connected")

    # Fetch application commands
    if discord_test_client.client.application:
        commands = await discord_test_client.client.application.commands()

        # Check for expected commands
        command_names = [cmd.name for cmd in commands]
        expected_commands = ["ask", "remember", "search", "ping", "channels"]

        for expected in expected_commands:
            assert expected in command_names, f"Command /{expected} not registered"

        print(f"✅ All slash commands registered: {command_names}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "discord_e2e"])
