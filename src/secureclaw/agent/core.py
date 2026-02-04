"""Agent core - LLM interaction and response generation with routing."""

import anthropic

from secureclaw.agent.prompts import SYSTEM_PROMPT
from secureclaw.agent.router import MessageIntent, MessageRouter, RoutingDecision
from secureclaw.config import get_settings
from secureclaw.logging import get_logger
from secureclaw.memory.qdrant import QdrantMemory

log = get_logger("secureclaw.agent.core")


class Agent:
    """Core agent that handles LLM interactions with intelligent routing."""

    def __init__(self, memory: QdrantMemory) -> None:
        """Initialize the agent.

        Args:
            memory: The memory system for context retrieval.
        """
        settings = get_settings()
        self._memory = memory
        self._router = MessageRouter()

        # Initialize Anthropic client for complex tasks
        if settings.anthropic_api_key:
            self._claude_client = anthropic.AsyncAnthropic(
                api_key=settings.anthropic_api_key.get_secret_value()
            )
            self._claude_model = "claude-sonnet-4-20250514"
            self._has_claude = True
            log.info("agent_initialized", providers=["gemini_flash", "claude"])
        else:
            self._claude_client = None
            self._has_claude = False
            log.info("agent_initialized", providers=["gemini_flash"])

    async def generate_response(
        self,
        user_id: int,
        channel_id: int,
        message: str,
    ) -> str:
        """Generate a response to a user message with intelligent routing.

        Args:
            user_id: Discord user ID.
            channel_id: Discord channel ID.
            message: The user's message.

        Returns:
            The generated response.
        """
        # Step 1: Classify the message intent
        routing = await self._router.classify(message)
        log.info(
            "message_routed",
            intent=routing.intent.value,
            use_claude=routing.use_claude,
            confidence=routing.confidence,
        )

        # Step 2: Handle based on intent
        match routing.intent:
            case MessageIntent.MEMORY_STORE:
                response = await self._handle_memory_store(message)
            case MessageIntent.MEMORY_RECALL:
                response = await self._handle_memory_recall(user_id, message)
            case MessageIntent.SYSTEM_COMMAND:
                response = await self._handle_system_command(message)
            case MessageIntent.SIMPLE_QUERY:
                response = await self._handle_simple_query(message)
            case MessageIntent.COMPLEX_TASK:
                response = await self._handle_complex_task(
                    user_id, channel_id, message, routing
                )
            case _:
                response = await self._handle_complex_task(
                    user_id, channel_id, message, routing
                )

        # Step 3: Store the exchange in memory
        await self._memory.store_message(
            user_id=user_id,
            channel_id=channel_id,
            role="user",
            content=message,
            metadata={"intent": routing.intent.value},
        )
        await self._memory.store_message(
            user_id=user_id,
            channel_id=channel_id,
            role="assistant",
            content=response,
        )

        return response

    async def _handle_simple_query(self, message: str) -> str:
        """Handle simple queries with Gemini Flash (cheap/fast).

        Args:
            message: The user's simple query.

        Returns:
            Generated response.
        """
        log.debug("handling_simple_query")
        return await self._router.generate_simple_response(message)

    async def _handle_complex_task(
        self,
        user_id: int,
        channel_id: int,
        message: str,
        routing: RoutingDecision,
    ) -> str:
        """Handle complex tasks with Claude (capable) or Flash (fallback).

        Args:
            user_id: Discord user ID.
            channel_id: Discord channel ID.
            message: The user's message.
            routing: The routing decision.

        Returns:
            Generated response.
        """
        # If Claude is available and this warrants it, use Claude
        if routing.use_claude and self._has_claude:
            return await self._generate_claude_response(user_id, channel_id, message)

        # Otherwise use Gemini Flash
        log.debug("using_flash_for_complex", reason="no_claude_or_low_complexity")
        return await self._router.generate_simple_response(message)

    async def _generate_claude_response(
        self,
        user_id: int,
        channel_id: int,
        message: str,
    ) -> str:
        """Generate a response using Claude for complex tasks.

        Args:
            user_id: Discord user ID.
            channel_id: Discord channel ID.
            message: The user's message.

        Returns:
            Generated response.
        """
        if not self._claude_client:
            return await self._router.generate_simple_response(message)

        # Get recent conversation context
        recent_messages = await self._memory.get_recent_context(
            user_id=user_id,
            channel_id=channel_id,
            limit=20,
        )

        # Search for relevant memories
        relevant_memories = await self._memory.search_memories(
            query=message,
            limit=5,
        )

        # Build context
        context_parts = []

        if relevant_memories:
            memory_text = "\n".join(
                f"- {m['content']}" for m in relevant_memories if m["score"] > 0.7
            )
            if memory_text:
                context_parts.append(f"## Relevant Memories\n{memory_text}")

        # Build message history for Claude
        messages = []
        for msg in recent_messages[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        messages.append({
            "role": "user",
            "content": message,
        })

        # Build system prompt with context
        system = SYSTEM_PROMPT
        if context_parts:
            system = f"{SYSTEM_PROMPT}\n\n" + "\n\n".join(context_parts)

        try:
            response = await self._claude_client.messages.create(
                model=self._claude_model,
                max_tokens=2048,
                system=system,
                messages=messages,
            )

            log.debug(
                "claude_response_generated",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            return response.content[0].text

        except anthropic.APIError as e:
            log.error("claude_api_error", error=str(e))
            # Fallback to Flash
            return await self._router.generate_simple_response(message)

    async def _handle_memory_store(self, message: str) -> str:
        """Handle memory storage requests.

        Args:
            message: The message containing what to remember.

        Returns:
            Confirmation message.
        """
        # Extract what to remember (simple approach - store the whole thing)
        # Could use Flash to extract the key info
        log.debug("handling_memory_store")

        # Use Flash to extract the memory content
        extraction_prompt = f"""The user wants to remember something. Extract just the key information to store.

User message: {message}

Respond with ONLY the fact/preference to remember, nothing else."""

        extracted = await self._router.generate_simple_response(extraction_prompt)

        await self._memory.store_memory(
            content=extracted.strip(),
            memory_type="user_request",
        )

        return f"Got it! I'll remember: {extracted.strip()}"

    async def _handle_memory_recall(self, user_id: int, query: str) -> str:
        """Handle memory recall requests.

        Args:
            user_id: Discord user ID.
            query: The recall query.

        Returns:
            Retrieved memories or response.
        """
        log.debug("handling_memory_recall")

        # Search memories
        memories = await self._memory.search_memories(query=query, limit=5)
        conversations = await self._memory.search_conversations(
            query=query, user_id=user_id, limit=5
        )

        if not memories and not conversations:
            return "I don't have any memories related to that. Would you like to tell me about it?"

        # Format and summarize using Flash
        context_parts = []

        if memories:
            mem_text = "\n".join(
                f"- {m['content']}" for m in memories if m["score"] > 0.5
            )
            if mem_text:
                context_parts.append(f"Stored memories:\n{mem_text}")

        if conversations:
            conv_text = "\n".join(
                f"- [{c['role']}]: {c['content'][:100]}..."
                for c in conversations
                if c["score"] > 0.5
            )
            if conv_text:
                context_parts.append(f"Past conversations:\n{conv_text}")

        if not context_parts:
            return "I found some vague matches, but nothing strongly related. Could you be more specific?"

        summary_prompt = f"""The user is asking: {query}

Here's what I found in my memory:
{chr(10).join(context_parts)}

Summarize what I know about this in a helpful, conversational way."""

        return await self._router.generate_simple_response(summary_prompt)

    async def _handle_system_command(self, message: str) -> str:
        """Handle system commands and help requests.

        Args:
            message: The system command.

        Returns:
            Help or command response.
        """
        log.debug("handling_system_command")

        lower_msg = message.lower().strip()

        if "help" in lower_msg or "what can you do" in lower_msg:
            return """Hi! I'm SecureClaw, your personal AI assistant. Here's what I can do:

**Chat & Questions**
- Ask me anything - simple questions use fast responses, complex tasks get deeper analysis

**Memory**
- Say "remember that..." to store information
- Ask "what do you know about..." to recall memories

**Commands**
- `/ask` - Ask me a question
- `/remember` - Store a memory
- `/search` - Search your memories
- `/ping` - Check if I'm online

I route messages intelligently - simple queries are fast and free, complex tasks use more capable models."""

        return "I'm not sure what you're asking. Try saying 'help' to see what I can do!"

    async def store_memory_from_request(
        self,
        content: str,
        memory_type: str = "general",
    ) -> str:
        """Store a memory based on explicit user request.

        Args:
            content: The memory content to store.
            memory_type: Type of memory.

        Returns:
            Confirmation message.
        """
        await self._memory.store_memory(
            content=content,
            memory_type=memory_type,
        )
        return f"I've stored that in my memory: {content}"
