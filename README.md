# SecureClaw

A secure, simplified personal AI assistant. Discord-based with vector memory.

## Quick Start

```bash
git clone https://github.com/youruser/secureclaw.git
cd secureclaw
cp .env.example .env  # Edit with your API keys
docker compose up -d
```

## Requirements

- Docker Desktop
- Discord bot token ([create one here](https://discord.com/developers/applications))
- Gemini API key ([get free tier](https://aistudio.google.com/app/apikey))
- Optional: Anthropic API key for Claude

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key  # optional
```

## Development

```bash
# Run in development mode with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Run tests
docker compose exec secureclaw pytest
```

## Architecture

- **Discord Bot**: Main interface (discord.py)
- **Qdrant**: Vector database for semantic memory
- **Gemini Embeddings**: High-quality text embeddings
- **Sandbox**: Isolated tool execution with seccomp

## License

MIT
