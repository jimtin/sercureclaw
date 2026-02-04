"""Main entry point for SecureClaw."""

import asyncio

from secureclaw.config import get_settings
from secureclaw.discord.bot import SecureClawBot
from secureclaw.logging import get_logger, setup_logging
from secureclaw.memory.qdrant import QdrantMemory


async def main() -> None:
    """Main application entry point."""
    setup_logging()
    log = get_logger("secureclaw.main")

    settings = get_settings()
    log.info(
        "starting_secureclaw",
        environment=settings.environment,
        qdrant_url=settings.qdrant_url,
    )

    # Initialize memory system
    memory = QdrantMemory()
    await memory.initialize()

    # Initialize and run the Discord bot
    bot = SecureClawBot(memory=memory)

    try:
        await bot.start(settings.discord_token.get_secret_value())
    except KeyboardInterrupt:
        log.info("shutdown_requested")
    finally:
        await bot.close()
        log.info("secureclaw_stopped")


def run() -> None:
    """Run the application."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
