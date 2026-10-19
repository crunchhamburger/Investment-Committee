"""Structured LLM calls with caching, retries, timeouts, validation and cost logging.

Providers are thin `Transport`s. Everything else (cache, retry, schema
repair, accounting) lives here so it is tested once, offline.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class TransientError(Exception):
    """Retryable: rate limit, timeout, connection, 5xx."""


class PermanentError(Exception):
    """Not retryable: auth, bad request, missing fixture."""


@dataclass
class CallRecord:
    role: str
    stage: str
    model: str
    cache_hit: bool
    latency_s: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Optional[float] = None
    attempts: int = 1
    repaired: bool = False
    error: Optional[str] = None


class Transport(Protocol):
    def send(self, *, system: str, user: str, schema_name: str, schema: dict,
             temperature: Optional[float], timeout: float, meta: dict) -> tuple[str, int, int]: ...


def inline_refs(schema: dict) -> dict:
    """Dereference $defs so every provider sees a self-contained schema."""
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                return walk(copy.deepcopy(defs[name]))
            return {k: walk(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


@dataclass
class StructuredLLM:
    model_for: Callable[[str], str]
    transport_for: Callable[[str], Transport]
    cache_dir: Optional[Path] = None
    timeout_s: float = 90.0
    max_retries: int = 4
    temperature: Optional[float] = 0.2
    pricing: dict = field(default_factory=dict)
    sleep: Callable[[float], None] = time.sleep
    records: list[CallRecord] = field(default_factory=list)

    def call(self, *, role: str, stage: str, system: str, user: str, schema: type[T],
             meta: Optional[dict] = None) -> T:
        model = self.model_for(role)
        meta = dict(meta or {}, role=role, stage=stage)
        js = inline_refs(schema.model_json_schema())
        key = hashlib.sha256(json.dumps(
            [model, system, user, js, self.temperature], sort_keys=True).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json" if self.cache_dir else None
        t0 = time.perf_counter()
        if path and path.exists():
            text = json.loads(path.read_text())["text"]
            obj = schema.model_validate_json(text)
            self.records.append(CallRecord(role, stage, model, True, time.perf_counter() - t0, attempts=0))
            return obj

        transport = self.transport_for(model)
        rec = CallRecord(role, stage, model, False, 0.0, attempts=0)
        prompt = user
        for repair in range(2):
            text, tin, tout = self._send_with_retry(transport, rec, system, prompt, schema.__name__, js, meta)
            rec.input_tokens += tin
            rec.output_tokens += tout
            try:
                obj = schema.model_validate_json(text)
                break
            except ValidationError as e:
                if repair == 1:
                    rec.error = f"schema validation failed after repair: {e.errors()[:3]}"
                    rec.latency_s = time.perf_counter() - t0
                    self.records.append(rec)
                    raise PermanentError(rec.error) from e
                rec.repaired = True
                prompt = (user + "\n\nYour previous output failed schema validation:\n"
                          + json.dumps(e.errors()[:10], default=str)
                          + "\nReturn corrected JSON only.")
        rec.latency_s = time.perf_counter() - t0
        if model in self.pricing:
            pin, pout = self.pricing[model]
            rec.cost_usd = (rec.input_tokens * pin + rec.output_tokens * pout) / 1e6
        self.records.append(rec)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"model": model, "role": role, "stage": stage, "text": text}))
        return obj

    def _send_with_retry(self, transport, rec, system, user, name, js, meta):
        last: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            rec.attempts += 1
            try:
                return transport.send(system=system, user=user, schema_name=name, schema=js,
                                      temperature=self.temperature, timeout=self.timeout_s, meta=meta)
            except TransientError as e:
                last = e
                if attempt == self.max_retries:
                    break
                self.sleep(min(30.0, (2 ** attempt) * 0.5 + random.random() * 0.25))
        rec.error = f"transient failure after {rec.attempts} attempts: {last}"
        self.records.append(rec)
        raise PermanentError(rec.error)

    def summary(self) -> dict:
        live = [r for r in self.records if not r.cache_hit]
        return {
            "calls": len(self.records),
            "cache_hits": sum(r.cache_hit for r in self.records),
            "input_tokens": sum(r.input_tokens for r in self.records),
            "output_tokens": sum(r.output_tokens for r in self.records),
            "cost_usd": (sum(r.cost_usd for r in live if r.cost_usd is not None)
                         if any(r.cost_usd is not None for r in live) else None),
            "latency_s": round(sum(r.latency_s for r in self.records), 3),
            "retries": sum(max(r.attempts - 1, 0) for r in self.records),
            "repairs": sum(r.repaired for r in self.records),
            "models": sorted({r.model for r in self.records}),
            "records": [asdict(r) for r in self.records],
        }
