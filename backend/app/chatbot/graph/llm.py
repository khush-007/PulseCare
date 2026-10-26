import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from backend.app.core.config import settings

logger = logging.getLogger("pulsecare.chatbot.llm")


async def generate_completion(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.1,
) -> str:
    """Generate completion using configured LLM provider."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini" and settings.LLM_API_KEY:
        try:
            # Use the official Google Generative AI SDK
            import google.generativeai as genai
            genai.configure(api_key=settings.LLM_API_KEY)
            model = genai.GenerativeModel(settings.LLM_MODEL)
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = model.generate_content(full_prompt)
            # Extract text from response
            if hasattr(response, "text"):
                return response.text or ""
            elif isinstance(response, list) and response:
                return getattr(response[0], "text", "") or ""
            else:
                return ""
        except Exception as e:
            logger.warning(f"Gemini API call failed, falling back to mock: {str(e)}")

    elif provider == "openai" and settings.LLM_API_KEY:
        try:
            import urllib.request
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            body = json.dumps({
                "model": settings.LLM_MODEL,
                "messages": messages,
                "temperature": temperature,
            }).encode("utf-8")
            
            url = f"{settings.LLM_BASE_URL or 'https://api.openai.com/v1'}/chat/completions"
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI API call failed, falling back to mock: {str(e)}")

    # Default Mock LLM: Deterministic synthesis based on prompt & context
    return _generate_mock_completion(prompt, system_prompt)


def _generate_mock_completion(prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    Deterministic synthesis mock that processes prompt instructions and structured context.
    """
    p_lower = prompt.lower()
    
    # Classification prompts
    if "classify the user query into one or more routes" in p_lower:
        routes = []
        if any(w in p_lower for w in ["book", "appointment", "schedule", "my visit", "booked"]):
            if "my" in p_lower or "check my" in p_lower:
                routes.append("personal_data")
            else:
                routes.append("doctor_service_lookup")
        if any(w in p_lower for w in ["doctor", "cardiologist", "neurologist", "pediatrician", "dermatologist", "orthopedic", "dr."]):
            routes.append("doctor_service_lookup")
        if any(w in p_lower for w in ["medicine", "amoxicillin", "lisinopril", "metformin", "ibuprofen", "paracetamol", "drug", "pill", "tablet", "dosage"]):
            routes.append("medicine_info")
        if any(w in p_lower for w in ["pain", "fever", "cough", "symptom", "dizzy", "headache", "chest", "rash"]):
            routes.append("triage_handoff")
        if any(w in p_lower for w in ["faq", "policy", "insurance", "cancel", "how does", "what is pulsecare", "features", "website", "hours", "fee"]):
            routes.append("website_help")
        if any(w in p_lower for w in ["diabetes", "blood pressure", "guideline", "hypertension", "skin cancer", "melanoma", "health"]):
            routes.append("health_general")
        if any(w in p_lower for w in ["hello", "hi", "hey", "good morning", "thanks", "thank you", "who are you"]):
            routes.append("direct_llm")
            
        if not routes:
            if any(w in p_lower for w in ["weather", "crypto", "recipe", "stock", "movie", "politics", "president"]):
                return json.dumps(["out_of_scope"])
            return json.dumps(["website_help"])
        return json.dumps(list(dict.fromkeys(routes)))

    # Direct LLM greetings
    if any(g in p_lower for g in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return "Hello! I am PulseCare's AI Healthcare Assistant. I can help you find doctors, explore medical services, look up medicine information, check your appointments, or guide you through clinical triage. How can I assist you today?"

    return "PulseCare offers comprehensive healthcare appointment scheduling, verified doctor directories, and instant AI clinical triage support."


async def stream_completion(
    prompt: str,
    system_prompt: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Yield tokens asynchronously for streaming output."""
    full_text = await generate_completion(prompt, system_prompt)
    words = full_text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
