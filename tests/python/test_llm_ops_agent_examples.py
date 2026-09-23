# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Offline behavior checks for executable examples shipped in the LLM ops agent."""
from __future__ import annotations

import ast
import re
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

AGENT = Path(__file__).resolve().parents[2] / "app/agents/llm-ops-engineer.md"


class RequestTimeout(Exception):
    pass


class ServerFailure(Exception):
    pass


@pytest.fixture
def examples(monkeypatch):
    """Provide only the two documented SDK exception types; never a network client."""
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        APITimeoutError=RequestTimeout, InternalServerError=ServerFailure,
    ))
    namespace = {}
    blocks = re.findall(r"```python\n(.*?)```", AGENT.read_text(), re.DOTALL)
    assert blocks, "Agent has no Python examples"
    for block in blocks:
        tree = ast.parse(block, filename=str(AGENT))
        exec(compile(tree, str(AGENT), "exec"), namespace)
    return namespace


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.requests = []
        self.options = None
        self.responses = SimpleNamespace(create=self.create)

    def with_options(self, **options):
        self.options = options
        return self

    def create(self, **request):
        self.requests.append(request)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_cache_key_is_order_independent_and_changes_with_context(examples):
    key = examples["response_cache_key"]
    request = {"provider": "openai", "model": "configured-primary", "input": "question",
               "instructions": "policy", "reasoning": {"effort": "medium"}}
    expected = key("tenant/access", "revision-1", request)
    assert key("tenant/access", "revision-1", dict(reversed(list(request.items())))) == expected
    assert key("other-tenant/access", "revision-1", request) != expected
    assert key("tenant/access", "revision-2", request) != expected
    for field, value in (("model", "configured-fallback"), ("input", "changed"),
                         ("instructions", "other-policy"), ("reasoning", {"effort": "high"})):
        assert key("tenant/access", "revision-1", {**request, field: value}) != expected


@pytest.mark.parametrize("scope,revision", [("", "v1"), ("tenant", "")])
def test_cache_key_requires_scope_and_revision(examples, scope, revision):
    with pytest.raises(ValueError):
        examples["response_cache_key"](scope, revision, {"input": "test"})


def test_fallback_reports_selected_route_without_changing_request(examples):
    response = SimpleNamespace(model="configured-fallback", status="completed", output_text="ok")
    client = FakeClient([RequestTimeout(), response])
    requests = [{"model": "configured-primary", "input": "test"},
                {"model": "configured-fallback", "input": "test"}]
    assert examples["response_with_fallback"](client, requests) == (response, 1)
    assert client.requests == requests
    assert client.options == {"max_retries": 0, "timeout": 30.0}


@pytest.mark.parametrize("error", [ValueError("bad request"), PermissionError("not authorized")])
def test_fallback_propagates_nontransient_errors_without_trying_another_model(examples, error):
    client = FakeClient([error, object()])
    with pytest.raises(type(error)):
        examples["response_with_fallback"](client, [{"model": "primary"}, {"model": "fallback"}])
    assert len(client.requests) == 1


def test_fallback_propagates_last_transient_error_after_bounded_attempts(examples):
    last_error = ServerFailure("still unavailable")
    client = FakeClient([RequestTimeout(), last_error])
    with pytest.raises(ServerFailure) as caught:
        examples["response_with_fallback"](client, [{"model": "primary"}, {"model": "fallback"}])
    assert caught.value is last_error
    assert len(client.requests) == 2


@pytest.mark.parametrize("requests", [[], [{}], [{"model": ""}], [{"model": "x"}] * 4])
def test_fallback_rejects_missing_models_and_unbounded_routes_before_calling(examples, requests):
    client = FakeClient([])
    with pytest.raises(ValueError):
        examples["response_with_fallback"](client, requests)
    assert client.requests == []


def test_incomplete_response_is_returned_for_validation_without_fallback(examples):
    response = SimpleNamespace(status="incomplete", output_text="")
    client = FakeClient([response, object()])
    assert examples["response_with_fallback"](client, [{"model": "primary"}, {"model": "fallback"}]) == (response, 0)
    assert len(client.requests) == 1


def test_token_cost_splits_cached_input_and_counts_output_once(examples):
    rates = {"input": Decimal("2"), "cached_input": Decimal("0.5"), "output": Decimal("8")}
    assert examples["text_token_cost"](1000, 400, 250, rates) == Decimal("0.0034")
    with pytest.raises(KeyError):
        examples["text_token_cost"](1000, 400, 250, {})


@pytest.mark.parametrize("counts", [(10, 11, 2), (-1, 0, 0), (True, 0, 1), (1, 0, -2)])
def test_token_cost_rejects_invalid_usage(examples, counts):
    rates = {"input": Decimal("2"), "cached_input": Decimal("0.5"), "output": Decimal("8")}
    with pytest.raises(ValueError):
        examples["text_token_cost"](*counts, rates)


def test_token_cost_rejects_unusable_rates(examples):
    for rate in (Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(ValueError):
            examples["text_token_cost"](1, 0, 1, {"input": rate, "cached_input": Decimal(0), "output": Decimal(1)})
