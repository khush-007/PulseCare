import asyncio

import pytest

from backend.app.chatbot.graph import llm
from backend.app.core.config import Settings


def test_llm_api_key_accepts_primary_and_legacy_names(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "primary-test-value")
    monkeypatch.setenv("GEMINI_API_KEY", "legacy-test-value")
    primary = Settings(_env_file=None)
    assert primary.LLM_API_KEY == "primary-test-value"

    monkeypatch.setenv("LLM_API_KEY", "")
    legacy = Settings(_env_file=None)
    assert legacy.LLM_API_KEY == "legacy-test-value"

    monkeypatch.setenv("LLM_API_KEY", "   ")
    whitespace_primary = Settings(_env_file=None)
    assert whitespace_primary.LLM_API_KEY == "legacy-test-value"

    monkeypatch.delenv("LLM_API_KEY")
    legacy_only = Settings(_env_file=None)
    assert legacy_only.LLM_API_KEY == "legacy-test-value"

    monkeypatch.delenv("GEMINI_API_KEY")
    missing = Settings(_env_file=None)
    assert missing.LLM_API_KEY is None


@pytest.mark.asyncio
async def test_gemini_uses_installed_sdk_config(monkeypatch):
    from google import genai

    captured = {}

    class FakeModels:
        async def generate_content(self, **kwargs):
            captured["request"] = kwargs
            return type("Response", (), {"text": "  grounded answer  "})()

    class FakeAio:
        def __init__(self):
            self.models = FakeModels()

        async def aclose(self):
            captured["closed"] = True

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.aio = FakeAio()

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(llm.settings, "LLM_MODEL", "test-model")

    answer = await llm._generate_gemini("user question", "system rules", 0.35, 4.0)

    assert answer == "grounded answer"
    assert captured["client"]["http_options"].timeout == 4000
    assert captured["request"]["model"] == "test-model"
    assert captured["request"]["contents"] == "user question"
    assert captured["request"]["config"].system_instruction == "system rules"
    assert captured["request"]["config"].temperature == 0.35
    assert captured["closed"] is True


@pytest.mark.asyncio
async def test_openai_passes_system_prompt_temperature_and_timeout(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured["request"] = kwargs
            message = type("Message", (), {"content": "answer"})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

        async def close(self):
            captured["closed"] = True

    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeClient)
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(llm.settings, "LLM_MODEL", "test-model")
    monkeypatch.setattr(llm.settings, "LLM_BASE_URL", None)

    answer = await llm._generate_openai("question", "system rules", 0.45, 7.0)

    assert answer == "answer"
    assert captured["request"]["model"] == "test-model"
    assert captured["request"]["messages"] == [
        {"role": "system", "content": "system rules"},
        {"role": "user", "content": "question"},
    ]
    assert captured["request"]["temperature"] == 0.45
    assert captured["client"]["timeout"] == 7.0
    assert captured["closed"] is True


@pytest.mark.asyncio
async def test_generate_completion_uses_configured_temperature(monkeypatch):
    captured = {}

    async def fake_gemini(prompt, system_prompt, temperature, timeout_seconds):
        captured.update(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
        return "answer"

    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(llm.settings, "LLM_TEMPERATURE", 0.6)
    monkeypatch.setattr(llm.settings, "LLM_TIMEOUT_SECONDS", 8.0)
    monkeypatch.setattr(llm, "_generate_gemini", fake_gemini)

    result = await llm.generate_completion("question", "system rules")

    assert result == "answer"
    assert captured == {
        "prompt": "question",
        "system_prompt": "system rules",
        "temperature": 0.6,
        "timeout_seconds": 8.0,
    }


@pytest.mark.asyncio
async def test_provider_failure_is_transparent_and_never_falls_back(monkeypatch):
    async def fail_provider(*_args):
        raise ValueError("provider detail must not be returned")

    def fail_mock(*_args):
        raise AssertionError("mock fallback must not run")

    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_generate_gemini", fail_provider)
    monkeypatch.setattr(llm, "_generate_mock_completion", fail_mock)

    with pytest.raises(llm.LLMProviderError, match="gemini.*ValueError") as error:
        await llm.generate_completion("question")

    assert "provider detail" not in str(error.value)


@pytest.mark.asyncio
async def test_provider_failure_reports_only_safe_status_metadata(monkeypatch, caplog):
    class ProviderError(Exception):
        code = 403
        status = "PERMISSION_DENIED"

    async def fail_provider(*_args):
        raise ProviderError("private key and response body must not be logged")

    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_generate_gemini", fail_provider)

    with pytest.raises(llm.LLMProviderError) as error:
        await llm.generate_completion("question")

    diagnostic = str(error.value) + caplog.text
    assert "HTTP 403" in diagnostic
    assert "PERMISSION_DENIED" in diagnostic
    assert "private key" not in diagnostic


@pytest.mark.asyncio
async def test_provider_timeout_is_bounded(monkeypatch):
    async def slow_provider(*_args):
        await asyncio.sleep(0.15)
        return "late answer"

    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(llm.settings, "LLM_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(llm, "_generate_gemini", slow_provider)

    with pytest.raises(llm.LLMProviderError, match="timed out"):
        await llm.generate_completion("question")


@pytest.mark.asyncio
async def test_mock_provider_runs_only_when_explicitly_selected(monkeypatch):
    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "mock")
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", None)
    monkeypatch.setattr(
        llm,
        "_generate_mock_completion",
        lambda prompt, system: f"mock:{prompt}:{system}",
    )

    assert await llm.generate_completion("question", "rules") == "mock:question:rules"


@pytest.mark.asyncio
async def test_missing_provider_key_fails_without_mock_fallback(monkeypatch):
    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", None)
    monkeypatch.setattr(
        llm,
        "_generate_mock_completion",
        lambda *_args: pytest.fail("mock fallback must not run"),
    )

    with pytest.raises(RuntimeError, match="LLM_API_KEY is missing"):
        await llm.generate_completion("question")
