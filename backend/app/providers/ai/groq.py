"""
Ascendra — Groq AI Provider.

Fast inference using Groq cloud models (GPT-OSS-20B).
"""

import logging

import httpx
from groq import AsyncGroq

from app.config import settings
from app.providers.ai.base import AIProvider, AIResponse

logger = logging.getLogger("ascendra.providers.ai.groq")


class GroqProvider(AIProvider):

    def __init__(self):
        self._client = None
        self.default_model = "openai/gpt-oss-20b"

    def _get_client(self) -> AsyncGroq:
        if not self._client:
            api_key = settings.GROQ_API_KEY
            http_client = httpx.AsyncClient()
            self._client = AsyncGroq(api_key=api_key, http_client=http_client)
        return self._client

    @property
    def provider_name(self) -> str:
        return "groq"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Generate text using Groq."""
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                messages=messages,
                model=self.default_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return AIResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
            )
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            from fastapi import HTTPException
            if "429" in str(e) or "rate_limit" in str(e).lower():
                raise HTTPException(status_code=429, detail="Groq API Rate Limit Reached. Please wait a minute and try again.")
            raise HTTPException(status_code=500, detail=f"AI Provider Error: {e}")

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> AIResponse:
        """Generate structured JSON output using Groq (forces JSON mode)."""
        client = self._get_client()

        structured_system = (system_prompt or "") + (
            "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no code fences, no explanation."
        )

        messages = []
        if structured_system:
            messages.append({"role": "system", "content": structured_system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                messages=messages,
                model=self.default_model,
                temperature=temperature,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            return AIResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
            )
        except Exception as e:
            logger.error(f"Groq structured generation failed: {e}")
            from fastapi import HTTPException
            if "429" in str(e) or "rate_limit" in str(e).lower():
                raise HTTPException(status_code=429, detail="Groq API Rate Limit Reached. Please wait a minute and try again.")
            raise HTTPException(status_code=500, detail=f"AI Provider Error: {e}")


# Singleton
groq_provider = GroqProvider()
