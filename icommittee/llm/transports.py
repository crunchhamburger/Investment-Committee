"""Provider transports. Live transports import their SDKs lazily, so the
offline path has no third-party dependencies beyond pydantic and PyYAML.

Model spec strings: "fixture", "openai:<model>", "anthropic:<model>".
Credentials come only from the provider's standard environment variables
(OPENAI_API_KEY, ANTHROPIC_API_KEY); nothing is read from files or code.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from .client import PermanentError, TransientError


class FixtureTransport:
    """Replays recorded responses keyed by role/stage. Deterministic and offline.

    A fixture file may hold a single response or a mapping keyed by
    meta['variant'] (e.g. the analyst being challenged)."""

    def __init__(self, root: Path, mutate: Optional[Callable[[dict, dict], dict]] = None):
        self.root = Path(root)
        self.mutate = mutate  # adversarial tests inject faults here

    def send(self, *, system, user, schema_name, schema, temperature, timeout, meta):
        path = self.root / f"{meta['role']}.{meta['stage']}.json"
        if not path.exists():
            raise PermanentError(f"no fixture for {meta['role']}/{meta['stage']} at {path}")
        data = json.loads(path.read_text())
        variant = meta.get("variant")
        if variant is not None and isinstance(data, dict) and "_variants" in data:
            data = data["_variants"].get(variant, data.get("_default"))
            if data is None:
                raise PermanentError(f"fixture {path.name} has no variant {variant!r}")
        if self.mutate:
            data = self.mutate(meta, data)
        text = json.dumps(data)
        return text, len(system + user) // 4, len(text) // 4


class OpenAITransport:
    def __init__(self, model: str):
        try:
            import openai  # noqa: F401
        except ImportError as e:
            raise PermanentError("pip install openai to use openai:* models") from e
        self.model = model
        self._client = None

    def send(self, *, system, user, schema_name, schema, temperature, timeout, meta):
        import openai
        if self._client is None:
            self._client = openai.OpenAI(timeout=timeout, max_retries=0)
        kwargs = dict(model=self.model,
                      messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                      response_format={"type": "json_schema",
                                       "json_schema": {"name": schema_name, "schema": schema, "strict": False}})
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            resp = self._client.chat.completions.create(**kwargs)
        except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError,
                openai.InternalServerError) as e:
            raise TransientError(str(e)) from e
        except openai.OpenAIError as e:
            raise PermanentError(str(e)) from e
        u = resp.usage
        return resp.choices[0].message.content or "", getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0)


class AnthropicTransport:
    """Structured output via a forced tool call whose input_schema is the target schema."""

    def __init__(self, model: str, max_tokens: int = 8000):
        try:
            import anthropic  # noqa: F401
        except ImportError as e:
            raise PermanentError("pip install anthropic to use anthropic:* models") from e
        self.model = model
        self.max_tokens = max_tokens
        self._client = None

    def send(self, *, system, user, schema_name, schema, temperature, timeout, meta):
        import anthropic
        if self._client is None:
            self._client = anthropic.Anthropic(timeout=timeout, max_retries=0)
        kwargs = dict(model=self.model, max_tokens=self.max_tokens, system=system,
                      messages=[{"role": "user", "content": user}],
                      tools=[{"name": schema_name, "description": "Return the structured result.",
                              "input_schema": schema}],
                      tool_choice={"type": "tool", "name": schema_name})
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            resp = self._client.messages.create(**kwargs)
        except (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError,
                anthropic.InternalServerError) as e:
            raise TransientError(str(e)) from e
        except anthropic.APIError as e:
            raise PermanentError(str(e)) from e
        block = next((b for b in resp.content if getattr(b, "type", "") == "tool_use"), None)
        if block is None:
            raise PermanentError("model did not return the structured tool call")
        return json.dumps(block.input), resp.usage.input_tokens, resp.usage.output_tokens


def make_transport_factory(fixture_root: Optional[Path] = None, mutate=None):
    cache: dict[str, object] = {}

    def factory(spec: str):
        if spec not in cache:
            if spec == "fixture":
                if fixture_root is None:
                    raise PermanentError("fixture model requested but no fixture directory configured")
                cache[spec] = FixtureTransport(fixture_root, mutate)
            elif spec.startswith("openai:"):
                cache[spec] = OpenAITransport(spec.split(":", 1)[1])
            elif spec.startswith("anthropic:"):
                cache[spec] = AnthropicTransport(spec.split(":", 1)[1])
            else:
                raise PermanentError(f"unknown model spec {spec!r}; use fixture | openai:<m> | anthropic:<m>")
        return cache[spec]

    return factory
