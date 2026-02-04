"""Message router using Gemini Flash for intent classification."""

from dataclasses import dataclass
from enum import Enum

from google import genai

from secureclaw.config import get_settings
from secureclaw.logging import get_logger

log = get_logger("secureclaw.agent.router")

# Fast, cheap model for routing decisions
ROUTER_MODEL = "gemini-2.0-flash"


class MessageIntent(Enum):
    """Classified intent types for routing."""

    SIMPLE_QUERY = "simple_query"  # Quick factual questions, greetings
    COMPLEX_TASK = "complex_task"  # Code generation, analysis, creative tasks
    MEMORY_STORE = "memory_store"  # User wants to remember something
    MEMORY_RECALL = "memory_recall"  # User asking about past conversations
    SYSTEM_COMMAND = "system_command"  # Bot commands, settings


@dataclass
class RoutingDecision:
    """Result of routing classification."""

    intent: MessageIntent
    confidence: float
    reasoning: str
    use_claude: bool  # Whether to use Claude (expensive) or Flash (cheap)


ROUTER_PROMPT = """You are a message router. Classify the user's message into one of these intents:

1. SIMPLE_QUERY - Greetings, quick factual questions, simple requests
   Examples: "Hi", "What's 2+2?", "What day is it?", "Thanks!"
   
2. COMPLEX_TASK - Code generation, detailed analysis, creative writing, multi-step tasks
   Examples: "Write a Python script to...", "Explain how transformers work in detail", "Help me debug this code..."
   
3. MEMORY_STORE - User explicitly wants you to remember something
   Examples: "Remember that I prefer dark mode", "My birthday is March 15", "Note that..."
   
4. MEMORY_RECALL - User asking about past conversations or stored information
   Examples: "What did we talk about yesterday?", "What do you know about me?", "What are my preferences?"
   
5. SYSTEM_COMMAND - Bot commands, settings, help requests
   Examples: "Help", "What can you do?", "List commands", "Settings"

Respond with ONLY a JSON object:
{"intent": "INTENT_NAME", "confidence": 0.0-1.0, "reasoning": "brief reason"}
"""


class MessageRouter:
    """Routes messages to appropriate handlers using Gemini Flash."""

    def __init__(self) -> None:
        """Initialize the router with Gemini Flash."""
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self._model = ROUTER_MODEL
        log.info("message_router_initialized", model=self._model)

    async def classify(self, message: str) -> RoutingDecision:
        """Classify a message and determine routing.

        Args:
            message: The user's message to classify.

        Returns:
            RoutingDecision with intent and routing info.
        """
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=f"{ROUTER_PROMPT}\n\nUser message: {message}",
                config={
                    "temperature": 0.1,  # Low temperature for consistent classification
                    "max_output_tokens": 150,
                },
            )

            # Parse the response
            import json
            result_text = response.text.strip()
            
            # Handle potential markdown code blocks
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            result = json.loads(result_text)

            intent = MessageIntent(result["intent"].lower())
            confidence = float(result.get("confidence", 0.8))
            reasoning = result.get("reasoning", "")

            # Determine if we need Claude (expensive) or can use Flash (cheap)
            use_claude = intent == MessageIntent.COMPLEX_TASK and confidence > 0.7

            decision = RoutingDecision(
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                use_claude=use_claude,
            )

            log.debug(
                "message_classified",
                intent=intent.value,
                confidence=confidence,
                use_claude=use_claude,
            )

            return decision

        except Exception as e:
            log.warning("classification_failed", error=str(e), message=message[:50])
            # Default to complex task with Claude on classification failure
            return RoutingDecision(
                intent=MessageIntent.COMPLEX_TASK,
                confidence=0.5,
                reasoning="Classification failed, defaulting to complex task",
                use_claude=True,
            )

    async def generate_simple_response(self, message: str) -> str:
        """Generate a response for simple queries using Gemini Flash.

        Args:
            message: The user's simple query.

        Returns:
            Generated response.
        """
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=message,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 500,
                },
            )
            return response.text
        except Exception as e:
            log.error("flash_generation_failed", error=str(e))
            return "I'm having trouble processing that. Could you try again?"
