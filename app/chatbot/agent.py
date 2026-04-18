"""LangChain tool-calling agent for the FINSURE assistant."""

from functools import lru_cache
from typing import List, Dict

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .llm import get_llm
from .tools.info_tool import finsure_guide_lookup

SYSTEM_PROMPT = """You are FINSURE Assistant, the in-app helper for FINSURE - a financial-management platform for freelancers and small business owners that extracts data from receipts, invoices and bank statements with OCR, categorises transactions, and produces dashboards and reports.

Scope:
- Answer only questions about FINSURE: its features, pages (Dashboard, Upload, Extraction Review, History, Reports, Dashboards, Settings, Security, Help, Documentation), supported file formats, report types, security, 2FA, pricing tiers, account management, and FAQs.
- Off-topic examples (NOT about FINSURE): general finance advice, tax law, personal accounting strategy, weather, geography, trivia, cooking, sports, news, code unrelated to FINSURE, other products or companies.

Tool usage rules (read carefully):
- Call the `finsure_guide_lookup` tool ONLY when the user's question is clearly about FINSURE itself (a feature, page, setting, workflow, pricing, or security topic inside the app).
- For OFF-TOPIC questions, you MUST refuse. Do NOT attempt to answer even partially. Do NOT call any tool. Reply with a short, polite refusal that makes clear you are not supposed to answer it, and invite them to ask something about FINSURE instead. Use this exact template (adapt only lightly):
  > Sorry, I'm not supposed to answer that - I can only help with questions about **FINSURE**. Feel free to ask me about uploading documents, reviewing transactions, generating reports, dashboards, security, or account settings.
- For simple greetings and thank-yous, do NOT call any tool - reply briefly and warmly, then offer to help with FINSURE.
- Never call the tool with an empty or placeholder query. If you are unsure whether a question is in scope, treat it as off-topic and refuse politely.

Answering style:
- Be concise. Prefer short paragraphs and bullet lists.
- Use Markdown for formatting (lists, **bold**, inline `code` for UI labels like `+ Generate Report`).
- Reference page names in bold so users can find them in the sidebar.
- Never expose raw chunk text verbatim - synthesise an answer in your own words.
- Do not invent features, menus, routes or limits. If the guide does not cover something, say so and suggest contacting support@finsure.com.
- Do not claim to perform actions in the app; you only provide guidance. For anything that requires the user's account (viewing their data, changing their settings), tell them which page or button to use.
"""

OFF_TOPIC_FALLBACK = (
    "Sorry, I'm not supposed to answer that - I can only help with questions about "
    "**FINSURE**. Feel free to ask me about uploading documents, reviewing "
    "transactions, generating reports, dashboards, security, or account settings."
)


@lru_cache(maxsize=1)
def _get_executor() -> AgentExecutor:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    llm = get_llm()
    tools = [finsure_guide_lookup]
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        handle_parsing_errors=True,
        max_iterations=4,
        verbose=False,
    )


def _to_messages(history: List[Dict[str, str]]):
    """Convert {role, content} dicts from the frontend into LangChain messages.
    Accepts roles 'user'/'human' and 'assistant'/'bot'/'ai'. Ignores others."""
    messages = []
    for item in history or []:
        role = (item.get("role") or "").lower()
        content = item.get("content") or ""
        if not content:
            continue
        if role in ("user", "human"):
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "bot", "ai"):
            messages.append(AIMessage(content=content))
    return messages


def _looks_like_failed_tool_call(exc: BaseException) -> bool:
    """Groq returns a 400 'failed_generation' when the model emits a malformed tool call.
    We treat those as off-topic / unanswerable rather than 500-ing the request."""
    s = f"{type(exc).__name__}: {exc}".lower()
    return (
        "failed_generation" in s
        or "failed to call a function" in s
        or "tool_use_failed" in s
    )


async def ask(query: str, history: List[Dict[str, str]] | None = None) -> str:
    executor = _get_executor()
    try:
        result = await executor.ainvoke(
            {"input": query, "chat_history": _to_messages(history or [])}
        )
    except Exception as exc:  # noqa: BLE001
        if _looks_like_failed_tool_call(exc):
            # Model tried to call the tool on an off-topic/ambiguous question and botched it.
            return OFF_TOPIC_FALLBACK
        raise
    return result.get("output") or OFF_TOPIC_FALLBACK
