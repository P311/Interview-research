"""Thin wrapper around an OpenAI-compatible chat completions API (DeepSeek,
OpenRouter, or any other provider speaking the same protocol) for the one call shape
every node needs: structured extraction.

No cheap provider offers Anthropic's hosted web-search tool, so retrieval is handled
separately in search.py - this module only ever talks to the configured chat model,
never the internet directly.
"""

import json
from typing import Optional, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from jobagent.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY or "missing")

T = TypeVar("T", bound=BaseModel)


def extract(
    *, system: str, user: str, schema: Type[T], max_tokens: int = 8000, temperature: Optional[float] = None
) -> T:
    """One-shot structured extraction: prompt in, validated Pydantic model out.

    Uses JSON-object mode rather than a provider-specific strict-schema feature,
    since that's the one structured-output mechanism supported broadly across
    OpenAI-compatible providers. One repair attempt on a validation failure - cheap
    models follow schema instructions less reliably than a frontier model.

    temperature is left unset (provider default) unless a caller passes one -
    judgment/classification calls (fit_check) should pass something low, since
    determinism matters more than diversity for those.
    """
    if not LLM_API_KEY:
        raise RuntimeError(
            "Set JOBAGENT_LLM_API_KEY to your provider's API key "
            "(and JOBAGENT_LLM_BASE_URL / JOBAGENT_LLM_MODEL if not using DeepSeek)."
        )

    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    messages = [
        {
            "role": "system",
            "content": (
                f"{system}\n\n"
                "Respond with a single JSON object only - no prose, no markdown fences. "
                f"It must validate against this JSON Schema:\n{schema_json}"
            ),
        },
        {"role": "user", "content": user},
    ]

    kwargs = {"model": LLM_MODEL, "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
    if temperature is not None:
        kwargs["temperature"] = temperature

    last_error: Exception = RuntimeError("unreachable")
    for _ in range(2):
        response = client.chat.completions.create(messages=messages, **kwargs)
        content = response.choices[0].message.content
        try:
            data = json.loads(content)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {"role": "user", "content": f"That response was invalid: {e}. Return corrected JSON only."}
            )

    raise last_error
