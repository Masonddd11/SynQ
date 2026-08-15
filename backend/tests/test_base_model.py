"""
tests/test_base_model.py — Unit tests for the provider-agnostic model layer.

Tests:
- _get_model() returns an OpenAIModel for llm_provider="openai"
- _get_model() returns an OllamaModel for llm_provider="ollama"
- _get_model() caches the model instance (lazy singleton)
- _build_thinking_config() is a no-op returning None
- get_token_usage() returns {} safely with no usage data
- get_token_usage() normalizes camelCase (inputTokens) and snake_case (prompt_tokens) usage schemas

Requires the strands package (strands-agents[openai,ollama]) to be installed.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agents.base_agent import BaseAgent


class DummyAgent(BaseAgent):
    """Minimal concrete BaseAgent for tests."""

    def get_system_prompt(self) -> str:
        return "test system prompt"

    def get_tools(self) -> list:
        return []


def make_agent(**llm_overrides) -> DummyAgent:
    """Build a DummyAgent with a fake settings object."""
    defaults = {
        "llm_provider": "openai",
        "llm_base_url": "",
        "llm_api_key": "",
        "llm_model": "gpt-4o-mini",
        "llm_temperature": 0.3,
    }
    defaults.update(llm_overrides)
    return DummyAgent(settings=SimpleNamespace(**defaults))


class TestGetModel:
    def test_openai_provider_returns_openai_model(self):
        from strands.models.openai import OpenAIModel

        agent = make_agent(llm_provider="openai")
        model = agent._get_model()
        assert isinstance(model, OpenAIModel)

    def test_ollama_provider_returns_ollama_model(self):
        from strands.models.ollama import OllamaModel

        agent = make_agent(llm_provider="ollama", llm_base_url="http://localhost:11434")
        model = agent._get_model()
        assert isinstance(model, OllamaModel)

    def test_ollama_provider_with_empty_base_url_uses_none_host(self):
        from strands.models.ollama import OllamaModel

        agent = make_agent(llm_provider="ollama", llm_base_url="")
        model = agent._get_model()
        assert isinstance(model, OllamaModel)

    def test_openai_passes_temperature_and_client_args(self):
        from strands.models.openai import OpenAIModel

        agent = make_agent(
            llm_provider="openai",
            llm_base_url="http://localhost:8000/v1",
            llm_api_key="sk-test",
            llm_temperature=0.7,
        )
        model = agent._get_model()
        assert model.config["model_id"] == "gpt-4o-mini"
        assert model.config["params"]["temperature"] == 0.7
        assert model.client_args["base_url"] == "http://localhost:8000/v1"
        assert model.client_args["api_key"] == "sk-test"

    def test_ollama_passes_temperature_and_host(self):
        from strands.models.ollama import OllamaModel

        agent = make_agent(
            llm_provider="ollama",
            llm_base_url="http://localhost:11434",
            llm_temperature=0.5,
        )
        model = agent._get_model()
        assert model.config["model_id"] == "gpt-4o-mini"
        assert model.config["temperature"] == 0.5
        assert model.host == "http://localhost:11434"

    def test_get_model_caches_single_instance(self):
        agent = make_agent()
        first = agent._get_model()
        second = agent._get_model()
        assert first is second


class TestBuildThinkingConfig:
    def test_returns_none_unconditionally(self):
        agent = make_agent()
        assert agent._build_thinking_config() is None


class TestGetTokenUsage:
    def test_empty_when_no_last_result(self):
        agent = make_agent()
        assert agent.get_token_usage() == {}

    def test_empty_when_result_has_no_metrics(self):
        agent = make_agent()
        agent._last_result = SimpleNamespace(metrics=None)
        assert agent.get_token_usage() == {}

    def test_normalizes_camelcase_usage_schema(self):
        agent = make_agent()
        agent._last_result = SimpleNamespace(
            metrics=SimpleNamespace(
                latest_agent_invocation=SimpleNamespace(
                    usage={
                        "inputTokens": 100,
                        "outputTokens": 50,
                        "cacheReadInputTokens": 20,
                        "cacheWriteInputTokens": 5,
                    },
                    cycles=[
                        SimpleNamespace(
                            usage={
                                "inputTokens": 100,
                                "cacheReadInputTokens": 20,
                                "cacheWriteInputTokens": 5,
                            }
                        )
                    ],
                )
            )
        )
        assert agent.get_token_usage() == {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 20,
            "cache_write_tokens": 5,
            "context_size": 125,
        }

    def test_normalizes_openai_schema(self):
        agent = make_agent()
        agent._last_result = SimpleNamespace(
            metrics=SimpleNamespace(
                latest_agent_invocation=SimpleNamespace(
                    usage={
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "prompt_tokens_details": {"cached_tokens": 20},
                    },
                    cycles=[
                        SimpleNamespace(
                            usage={
                                "prompt_tokens": 100,
                                "prompt_tokens_details": {"cached_tokens": 20},
                            }
                        )
                    ],
                )
            )
        )
        assert agent.get_token_usage() == {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 20,
            "cache_write_tokens": None,
            "context_size": 120,
        }

    def test_handles_missing_usage_fields(self):
        agent = make_agent()
        agent._last_result = SimpleNamespace(
            metrics=SimpleNamespace(
                latest_agent_invocation=SimpleNamespace(
                    usage={},
                    cycles=[],
                )
            )
        )
        assert agent.get_token_usage() == {
            "input_tokens": None,
            "output_tokens": None,
            "cache_read_tokens": None,
            "cache_write_tokens": None,
            "context_size": None,
        }

    def test_defensive_except_returns_empty(self):
        agent = make_agent()
        agent._last_result = SimpleNamespace(
            metrics=SimpleNamespace(latest_agent_invocation=None)
        )
        # latest_agent_invocation=None -> usage None -> returns {}
        assert agent.get_token_usage() == {}
