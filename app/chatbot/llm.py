"""LLM initialisation for the FINSURE assistant.

Uses Groq by default (fast, cost-effective). Swap the provider by setting
CHATBOT_PROVIDER=openai and OPENAI_API_KEY, or CHATBOT_PROVIDER=gemini and
GEMINI_API_KEY. Default stays on Groq to match the DRM_Chatbot baseline.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_llm():
    provider = os.getenv("CHATBOT_PROVIDER", "groq").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to FINSURE_BACKEND/.env or export it "
                "in your shell before starting the server."
            )
        model = os.getenv("CHATBOT_MODEL", "llama-3.1-8b-instant")
        return ChatGroq(model=model, api_key=api_key, temperature=0.2)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        model = os.getenv("CHATBOT_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, api_key=api_key, temperature=0.2)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        model = os.getenv("CHATBOT_MODEL", "gemini-1.5-flash")
        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0.2)

    raise ValueError(f"Unknown CHATBOT_PROVIDER: {provider!r}. Use groq, openai, or gemini.")
