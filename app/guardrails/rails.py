import re

import logfire
from langchain_groq import ChatGroq
from nemoguardrails import RailsConfig, LLMRails

from app.config import settings
from app.guardrails.colang_rules import (
    COLANG_CONTENT,
    OFF_TOPIC_RESPONSE,
    RAIL_INDICATORS,
    YAML_CONTENT,
)


_rails: LLMRails | None = None
_guard_llm: ChatGroq | None = None

_SCOPE_PROMPT = """You are a topic gate for an Enterprise IT assistant.
The assistant may only discuss:
- Kubernetes (deployments, scaling, operators, networking)
- Intel hardware (CPUs, FPGAs, NICs, SR-IOV)
- Enterprise networking (SDN, VLANs, BGP, routing)
Greetings, farewells, and questions about what the assistant can do are also allowed.

Everything else is out of scope, including movies, TV, Netflix, sports, weather, food, jokes, homework, and general knowledge.

User message:
\"\"\"{message}\"\"\"

Reply with exactly one token: IN_SCOPE or OUT_OF_SCOPE.
"""


def initialize_rails() -> None:
    """
    Build the NeMo LLMRails singleton at app startup.
    Uses the smaller Groq model for intent classification at the gate.
    The primary RAG model stays on the heavier gateway config.
    """
    global _rails, _guard_llm

    guard_llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROK_FALLBACK_MODEL,
        temperature=0,
        reasoning_effort="low",
    )

    config = RailsConfig.from_content(
        colang_content=COLANG_CONTENT,
        yaml_content=YAML_CONTENT
    )

    _rails = LLMRails(config, llm=guard_llm)
    _guard_llm = guard_llm
    logfire.info("🛡️ NeMo Guardrails initialised.", model=settings.GROK_FALLBACK_MODEL)
    
    


def _message_in_scope(message: str) -> bool:
    """True when the message is enterprise IT, or a greeting / farewell / capabilities ask."""
    if _guard_llm is None:
        return True

    result = _guard_llm.invoke(_SCOPE_PROMPT.format(message=message))
    text = (result.content or "").upper()
    # OUT_OF_SCOPE contains the substring IN_SCOPE, so match the full token.
    tokens = re.findall(r"OUT_OF_SCOPE|IN_SCOPE", text)

    if not tokens:
        logfire.warning("Scope check was unclear; blocking.", verdict=text[:200])
        return False
    return tokens[-1] == "IN_SCOPE"


def guard(message: str) -> tuple[bool, str | None]:
    """
    Run a user message through the NeMo rails gate.

    Returns:
        (True,  rail_response) — a rail fired; return this response immediately,
                                skip the RAG pipeline entirely.
        (False, None)          — message is clean; proceed to LangGraph.
    """
    if _rails is None:
        logfire.warning("⚠️ Guardrails not initialised — skipping gate.")
        return False, None

    with logfire.span("🛡️ Guardrails Check"):
        result = _rails.generate(messages=[{"role": "user", "content": message}])

        # NeMo returns {'role': 'assistant', 'content': '...'} — extract text
        content = result.get("content", "") if isinstance(result, dict) else str(result)

        fired = any(indicator in content for indicator in RAIL_INDICATORS)

        if fired:
            logfire.info(f"🛡️ Guardrails fired | query='{message[:80]}'")
            return True, content

        if not _message_in_scope(message):
            logfire.info(f"🛡️ Off-topic blocked | query='{message[:80]}'")
            return True, OFF_TOPIC_RESPONSE

        logfire.info("✅ Guardrails passed.")
        return False, None
