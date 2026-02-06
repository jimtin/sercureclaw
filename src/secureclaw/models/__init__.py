"""Model registry and tier-based selection for LLM providers."""

from secureclaw.models.discovery import DiscoveryError, ModelDiscovery
from secureclaw.models.pricing import CostResult, get_cost, has_pricing
from secureclaw.models.registry import ModelRegistry
from secureclaw.models.tiers import ModelInfo, Tier, infer_tier

__all__ = [
    "CostResult",
    "DiscoveryError",
    "ModelDiscovery",
    "ModelInfo",
    "ModelRegistry",
    "Tier",
    "get_cost",
    "has_pricing",
    "infer_tier",
]
