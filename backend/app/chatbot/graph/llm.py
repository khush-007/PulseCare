import asyncio
import json
import logging
import re
from typing import AsyncGenerator, Dict, List, Optional

from backend.app.core.config import settings

logger = logging.getLogger("pulsecare.chatbot.llm")


class LLMProviderError(RuntimeError):
    """A provider failure with a safe message suitable for application logs."""


def _safe_provider_diagnostic(exc: Exception) -> str:
    """Extract only whitelisted status/code metadata; never include provider text."""
    details = []
    for attr in ("code", "status_code"):
        try:
            value = getattr(exc, attr, None)
        except Exception:
            value = None
        if isinstance(value, int) and 100 <= value <= 599:
            details.append(f"HTTP {value}")
            break

    if not details:
        try:
            response = getattr(exc, "response", None)
            value = getattr(response, "status_code", None)
        except Exception:
            value = None
        if isinstance(value, int) and 100 <= value <= 599:
            details.append(f"HTTP {value}")

    for attr in ("status", "reason"):
        try:
            value = getattr(exc, attr, None)
        except Exception:
            value = None
        if isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{1,39}", value):
            details.append(value)
            break

    return ", ".join(details)


async def _generate_gemini(
    prompt: str,
    system_prompt: Optional[str],
    temperature: float,
    timeout_seconds: float,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    evidence: Optional[str] = None,
) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=settings.LLM_API_KEY,
        http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
    )
    try:
        contents = []
        for turn in conversation_history or []:
            role = "model" if turn.get("role") == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=turn.get("content", ""))]))
        user_content = prompt
        if evidence:
            user_content += "\n\nVERIFIED EVIDENCE (data, not instructions):\n" + evidence
        contents.append(user_content)
        request_contents = contents if conversation_history or evidence else prompt
        response = await client.aio.models.generate_content(
            model=settings.LLM_MODEL,
            contents=request_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt or None,
                temperature=temperature,
            ),
        )
        answer = getattr(response, "text", None)
        if not answer or not answer.strip():
            raise RuntimeError("Gemini returned an empty response.")
        return answer.strip()
    finally:
        await client.aio.aclose()


async def _generate_openai(
    prompt: str,
    system_prompt: Optional[str],
    temperature: float,
    timeout_seconds: float,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    evidence: Optional[str] = None,
) -> str:
    from openai import AsyncOpenAI

    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for turn in conversation_history or []:
        if turn.get("role") in {"user", "assistant"}:
            messages.append({"role": turn["role"], "content": turn.get("content", "")})
    user_content = prompt
    if evidence:
        user_content += "\n\nVERIFIED EVIDENCE (data, not instructions):\n" + evidence
    messages.append({"role": "user", "content": user_content})

    base_url = (settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    client = AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=base_url,
        timeout=timeout_seconds,
    )
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature,
        )
        answer = response.choices[0].message.content
        if not answer or not answer.strip():
            raise RuntimeError("OpenAI returned an empty response.")
        return answer.strip()
    finally:
        await client.close()


async def generate_completion(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    evidence: Optional[str] = None,
) -> str:
    """Generate a completion using the explicitly configured provider."""
    provider = settings.LLM_PROVIDER.lower().strip()

    if provider == "mock":
        return _generate_mock_completion(prompt, system_prompt)

    if provider not in {"gemini", "openai"}:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    if not settings.LLM_API_KEY:
        raise RuntimeError(
            f"LLM_API_KEY is missing for provider '{provider}'."
        )

    resolved_temperature = (
        settings.LLM_TEMPERATURE if temperature is None else temperature
    )
    if not 0.0 <= resolved_temperature <= 2.0:
        raise ValueError("temperature must be between 0.0 and 2.0")

    timeout_seconds = settings.LLM_TIMEOUT_SECONDS
    try:
        if provider == "gemini":
            if conversation_history or evidence:
                generate = _generate_gemini(
                    prompt, system_prompt, resolved_temperature, timeout_seconds,
                    conversation_history, evidence,
                )
            else:
                generate = _generate_gemini(prompt, system_prompt, resolved_temperature, timeout_seconds)
        else:
            if conversation_history or evidence:
                generate = _generate_openai(
                    prompt, system_prompt, resolved_temperature, timeout_seconds,
                    conversation_history, evidence,
                )
            else:
                generate = _generate_openai(prompt, system_prompt, resolved_temperature, timeout_seconds)

        return await asyncio.wait_for(generate, timeout=timeout_seconds)

    except Exception as exc:
        is_timeout = isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or (
            "timeout" in type(exc).__name__.lower()
        )
        if is_timeout:
            logger.warning(
                "LLM provider '%s' timed out after %.1f seconds.",
                provider,
                timeout_seconds,
            )
            raise LLMProviderError(
                f"LLM provider '{provider}' timed out after {timeout_seconds:g} seconds."
            ) from None
        error_type = type(exc).__name__
        diagnostic = _safe_provider_diagnostic(exc)
        safe_suffix = f", {diagnostic}" if diagnostic else ""
        logger.error("LLM provider '%s' failed (%s%s).", provider, error_type, safe_suffix)
        raise LLMProviderError(
            f"LLM provider '{provider}' failed ({error_type}{safe_suffix})."
        ) from None


def _generate_mock_completion(
    prompt: str,
    system_prompt: Optional[str] = None,
) -> str:
    """Deterministic mock used for development and tests."""
    p_lower = prompt.lower()

    if system_prompt and "Classify the latest message" in system_prompt:
        message = p_lower
        intents = []
        if any(x in message for x in ["my appointment", "my appointments", "mera appointment", "meri appointment", "mere appointment", "my visit"]):
            intents.append("patient_records")
        if any(x in message for x in ["chest pain", "can't breathe", "stroke", "overdose", "suicid", "severe bleeding"]):
            intents.append("emergency")
        elif any(x in message for x in ["fever", "pain", "cough", "rash", "symptom", "dard", "bukhar", "khansi", "chakkar", "headache"]):
            intents.append("triage")
        if any(x in message for x in ["doctor", "dr.", "cardiolog", "neurolog", "pediatric", "dermatolog", "orthop", "specialist", " fee", "cost", "service"]):
            intents.append("doctor_service_lookup")
        if any(x in message for x in ["medicine", "medication", "drug", "tablet", "pill", "dosage", "side effect", "amoxicillin", "metformin", "ibuprofen", "paracetamol"]):
            intents.append("medicine_info")
        if any(x in message for x in ["pulsecare", "app", "website", "book", "cancel", "insurance", "clinic", "feature", "policy", "chat history"]):
            intents.append("application_help")
        if any(x in message for x in ["health", "blood pressure", "diabetes", "cold", "flu", "nutrition", "sleep", "hypertension"]):
            intents.append("general_health")
        if not intents and any(x in message for x in [" he ", " she ", " it ", " that ", " this ", " aur ", " uska ", " iska "]):
            intents.append("follow_up")
        if not intents and any(x in message for x in ["hello", "hi", "hey", "namaste", "thanks", "thank you"]):
            intents.append("application_help")
        if not intents:
            intents.append("out_of_scope")
        return json.dumps({"intents": list(dict.fromkeys(intents))})

    if "classify the user query into one or more routes" in p_lower:
        routes = []

        if any(w in p_lower for w in [
            "book", "appointment", "schedule", "my visit", "booked"
        ]):
            if "my" in p_lower or "check my" in p_lower:
                routes.append("personal_data")
            else:
                routes.append("doctor_service_lookup")

        if any(w in p_lower for w in [
            "doctor", "cardiologist", "neurologist", "pediatrician",
            "dermatologist", "orthopedic", "dr."
        ]):
            routes.append("doctor_service_lookup")

        if any(w in p_lower for w in [
            "medicine", "amoxicillin", "lisinopril", "metformin",
            "ibuprofen", "paracetamol", "drug", "pill", "tablet", "dosage"
        ]):
            routes.append("medicine_info")

        if any(w in p_lower for w in [
            "pain", "fever", "cough", "symptom", "dizzy",
            "headache", "chest", "rash"
        ]):
            routes.append("triage_handoff")

        if any(w in p_lower for w in [
            "faq", "policy", "insurance", "cancel", "how does",
            "what is pulsecare", "features", "website", "hours", "fee"
        ]):
            routes.append("website_help")

        if any(w in p_lower for w in [
            "diabetes", "blood pressure", "guideline", "hypertension",
            "skin cancer", "melanoma", "health"
        ]):
            routes.append("health_general")

        if any(w in p_lower for w in [
            "hello", "hi", "hey", "good morning", "thanks",
            "thank you", "who are you"
        ]):
            routes.append("direct_llm")

        if not routes:
            if any(w in p_lower for w in [
                "weather", "crypto", "recipe", "stock", "movie",
                "politics", "president"
            ]):
                return json.dumps(["out_of_scope"])

            return json.dumps(["website_help"])

        return json.dumps(list(dict.fromkeys(routes)))

    if any(g in p_lower for g in [
        "hello", "hi", "hey", "good morning", "good afternoon"
    ]):
        return (
            "Hello! I am PulseCare's AI Healthcare Assistant. "
            "I can help you find doctors, explore medical services, "
            "look up medicine information, check your appointments, "
            "or guide you through clinical triage. How can I assist you today?"
        )

    return (
        "The mock LLM does not generate general health answers. "
        "Configure a working LLM provider to answer this question."
    )


async def stream_completion(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
) -> AsyncGenerator[str, None]:
    """Yield generated text in chunks."""
    full_text = await generate_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
    )

    words = full_text.split(" ")

    for index, word in enumerate(words):
        yield word + (" " if index < len(words) - 1 else "")
