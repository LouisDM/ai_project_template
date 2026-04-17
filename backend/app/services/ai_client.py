"""Anthropic Claude SDK 封装 — 带重试、语义化错误、可调试日志。

使用示例:
    from app.services.ai_client import call_claude, AIServiceUnavailableError

    try:
        response_text = await call_claude(
            system_prompt="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Hello"}],
        )
    except AIServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
"""
import asyncio
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# 默认模型 — 可按需换成 claude-opus-4-6 等
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 8192


class AIServiceUnavailableError(Exception):
    """Raised when all retries fail due to API errors (not empty results)."""
    pass


def get_client() -> anthropic.Anthropic:
    """Return a configured Anthropic client (supports third-party proxy via base_url)."""
    kwargs = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_base_url:
        kwargs["base_url"] = settings.anthropic_base_url
    return anthropic.Anthropic(**kwargs)


async def call_claude(
    system_prompt: str,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = 0,
    max_retries: int = 3,
) -> str:
    """Call Claude API with retry on rate limits and service errors.

    Returns the raw response text. Caller is responsible for parsing (JSON, etc).

    Raises AIServiceUnavailableError when all retries fail due to API errors,
    so HTTP routers can surface a clear 503 instead of an empty result.
    """
    client = get_client()
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages,
            )
            return message.content[0].text
        except anthropic.RateLimitError as e:
            wait = 5 * (attempt + 1)
            logger.warning("Claude rate limited (attempt %d), waiting %ds: %s", attempt + 1, wait, e)
            last_error = e
            await asyncio.sleep(wait)
        except anthropic.APIStatusError as e:
            # 500/503/529 (overloaded) etc — retry with longer backoff
            wait = 8 * (attempt + 1)
            logger.warning("Claude API status error %d (attempt %d), waiting %ds: %s",
                           e.status_code, attempt + 1, wait, e)
            last_error = e
            await asyncio.sleep(wait)
        except Exception as e:
            wait = 3 * (attempt + 1)
            logger.error("Claude API call failed (attempt %d), waiting %ds: %s", attempt + 1, wait, e)
            last_error = e
            await asyncio.sleep(wait)

    raise AIServiceUnavailableError(
        f"AI 服务暂时不可用，请稍后重试。（错误: {last_error}）"
    )
