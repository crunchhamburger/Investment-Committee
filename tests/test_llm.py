import json

import pytest
from pydantic import BaseModel

from icommittee.llm.client import PermanentError, StructuredLLM, TransientError, inline_refs


class Out(BaseModel):
    x: int


class Inner(BaseModel):
    a: int


class Nested(BaseModel):
    items: list[Inner]


class FakeTransport:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def send(self, **kw):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item, 10, 5


def client(t, **kw):
    return StructuredLLM(model_for=lambda r: "m", transport_for=lambda m: t, sleep=lambda s: None, **kw)


def test_retries_transient_then_succeeds():
    t = FakeTransport([TransientError("429"), TransientError("timeout"), json.dumps({"x": 1})])
    c = client(t, max_retries=3)
    assert c.call(role="r", stage="s", system="", user="", schema=Out).x == 1
    assert c.records[-1].attempts == 3 and c.summary()["retries"] == 2


def test_gives_up_after_max_retries():
    t = FakeTransport([TransientError("x")] * 3)
    with pytest.raises(PermanentError):
        client(t, max_retries=2).call(role="r", stage="s", system="", user="", schema=Out)


def test_schema_repair_once():
    t = FakeTransport(['{"x": "not an int"}', '{"x": 2}'])
    c = client(t)
    assert c.call(role="r", stage="s", system="", user="", schema=Out).x == 2
    assert c.records[-1].repaired


def test_schema_failure_after_repair_raises():
    t = FakeTransport(['{"y": 1}', '{"y": 1}'])
    with pytest.raises(PermanentError, match="validation"):
        client(t).call(role="r", stage="s", system="", user="", schema=Out)


def test_cache_avoids_second_call(tmp_path):
    t = FakeTransport([json.dumps({"x": 3})])
    c = client(t, cache_dir=tmp_path)
    c.call(role="r", stage="s", system="a", user="b", schema=Out)
    assert c.call(role="r", stage="s", system="a", user="b", schema=Out).x == 3
    assert t.calls == 1 and c.summary()["cache_hits"] == 1


def test_cost_accounting():
    t = FakeTransport([json.dumps({"x": 1})])
    c = client(t, pricing={"m": (3.0, 15.0)})
    c.call(role="r", stage="s", system="", user="", schema=Out)
    assert c.summary()["cost_usd"] == pytest.approx((10 * 3 + 5 * 15) / 1e6)


def test_inline_refs_removes_defs():
    s = inline_refs(Nested.model_json_schema())
    assert "$defs" not in json.dumps(s) and "$ref" not in json.dumps(s)
    assert s["properties"]["items"]["items"]["properties"]["a"]["type"] == "integer"
