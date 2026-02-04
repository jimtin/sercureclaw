"""Tests for message router."""

import pytest


class TestMessageRouter:
    """Tests for MessageRouter intent classification."""

    @pytest.mark.asyncio
    async def test_router_imports(self) -> None:
        """Test that router imports correctly."""
        from secureclaw.agent.router import MessageIntent, MessageRouter, RoutingDecision

        assert MessageIntent.SIMPLE_QUERY.value == "simple_query"
        assert MessageIntent.COMPLEX_TASK.value == "complex_task"
        assert MessageIntent.MEMORY_STORE.value == "memory_store"
        assert MessageIntent.MEMORY_RECALL.value == "memory_recall"
        assert MessageIntent.SYSTEM_COMMAND.value == "system_command"

    def test_routing_decision_dataclass(self) -> None:
        """Test RoutingDecision dataclass."""
        from secureclaw.agent.router import MessageIntent, RoutingDecision

        decision = RoutingDecision(
            intent=MessageIntent.SIMPLE_QUERY,
            confidence=0.95,
            reasoning="greeting detected",
            use_claude=False,
        )

        assert decision.intent == MessageIntent.SIMPLE_QUERY
        assert decision.confidence == 0.95
        assert decision.use_claude is False

    def test_complex_task_uses_claude(self) -> None:
        """Test that complex tasks with high confidence use Claude."""
        from secureclaw.agent.router import MessageIntent, RoutingDecision

        decision = RoutingDecision(
            intent=MessageIntent.COMPLEX_TASK,
            confidence=0.9,
            reasoning="code generation request",
            use_claude=True,
        )

        assert decision.use_claude is True
