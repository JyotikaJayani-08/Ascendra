"""
Ascendra — Gemini AI Provider.

Free tier: 15 RPM, 1M tokens/day.
"""

import logging

from google import genai
from google.genai import types

from app.config import settings
from app.providers.ai.base import AIProvider, AIResponse

logger = logging.getLogger("ascendra.providers.ai.gemini")


class GeminiProvider(AIProvider):

    def __init__(self):
        self._client = None

    def _get_client(self):
        if not self._client:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Generate text using Gemini."""
        client = self._get_client()

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system_prompt:
            config.system_instruction = system_prompt

        try:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt,
                config=config,
            )

            return AIResponse(
                content=response.text or "",
                model="gemini-flash-latest",
                total_tokens=response.usage_metadata.total_token_count if response.usage_metadata else 0,
                prompt_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                completion_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            )
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            from fastapi import HTTPException
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                raise HTTPException(status_code=429, detail="AI Provider Rate Limit Reached. Please wait a minute and try again.")
            raise HTTPException(status_code=500, detail=f"AI Provider Error: {e}")

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> AIResponse:
        """Generate structured JSON output using Gemini."""
        structured_system = (system_prompt or "") + (
            "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no code fences, no explanation."
        )
        return await self.generate(
            prompt=prompt,
            system_prompt=structured_system,
            temperature=temperature,
        )


# Singleton
gemini_provider = GeminiProvider()
