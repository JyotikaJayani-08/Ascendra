"""
Ascendra — AI Provider ABC.

Every AI provider (Gemini, OpenAI, Claude) implements this interface.
Business logic never talks to providers directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResponse:
    """Standardized response from any AI provider."""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AIProvider(ABC):
    """Abstract base for all AI providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Generate text from a prompt."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> AIResponse:
        """Generate structured (JSON) output."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier."""
        ...
