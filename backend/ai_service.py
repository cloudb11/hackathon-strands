import os
import uuid
import logging
from strands import Agent
from strands.agent.conversation_manager import SummarizingConversationManager
from strands.session import FileSessionManager

logger = logging.getLogger(__name__)

# --- MODEL CONFIGURATION ---
# Uncomment the model you need based on what organizers provide.

# Option 1: AWS Bedrock (default)
from strands.models import BedrockModel
model = BedrockModel(
    model_id=os.environ.get("AI_MODEL", "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    region_name=os.environ.get("AWS_REGION", "eu-central-1")
)

# Option 2: OpenAI / OpenAI-compatible endpoint
# from strands.models import OpenAIModel
# model = OpenAIModel(
#     model_id=os.environ.get("AI_MODEL", "gpt-4o"),
#     client_args={"api_key": os.environ.get("AI_API_KEY", ""), "base_url": os.environ.get("AI_API_URL", "https://api.openai.com/v1")}
# )

# Option 3: Anthropic direct
# from strands.models import AnthropicModel
# model = AnthropicModel(model_id=os.environ.get("AI_MODEL", "claude-sonnet-4-20250514"))

from tools import search_knowledge_base
from rag import retrieve_context

SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT",
    "You are a helpful AI assistant with access to a knowledge base and full conversation memory. "
    "IMPORTANT RULES:\n"
    "1. You REMEMBER everything the user has told you in this conversation.\n"
    "2. Relevant knowledge base context is AUTOMATICALLY provided with each question in a [KNOWLEDGE BASE CONTEXT] block. "
    "Always check this block and use the information if it is relevant to the user's question.\n"
    "3. Combine conversation history AND knowledge base context to give the best answer.\n"
    "4. You can also use the search_knowledge_base tool to do additional targeted searches if needed.\n"
    "5. Only say information is unavailable if BOTH conversation history AND the knowledge base have no answer."
)

# --- SESSION STORAGE ---
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), ".sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# --- PER-SESSION AGENT CACHE ---
_session_agents: dict[str, Agent] = {}


def _create_agent(session_id: str) -> Agent:
    """Create a new agent with conversation memory and session persistence."""

    # SummarizingConversationManager: summarizes older messages instead of discarding them.
    # This preserves critical context even in long conversations.
    conversation_manager = SummarizingConversationManager(
        summary_ratio=0.3,               # Summarize the oldest 30% of messages on overflow
        preserve_recent_messages=10,      # Always keep the last 10 messages verbatim
    )

    # FileSessionManager: persists conversation history to disk so it survives restarts.
    session_manager = FileSessionManager(
        session_id=session_id,
        sessions_dir=SESSIONS_DIR,
    )

    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_knowledge_base],
        conversation_manager=conversation_manager,
        session_manager=session_manager,
    )


def get_or_create_session(session_id: str | None = None) -> str:
    """Return an existing session_id or generate a new one."""
    if session_id and session_id in _session_agents:
        print(f"[SESSION] Reusing existing session: {session_id}")
        return session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        print(f"[SESSION] Created NEW session: {session_id}")
    else:
        print(f"[SESSION] session_id={session_id!r} NOT in cache (cache keys: {list(_session_agents.keys())}), re-creating")
    _session_agents[session_id] = _create_agent(session_id)
    return session_id


def ask_agent(question: str, session_id: str | None = None) -> dict:
    """Ask the agent a question within a session (conversation memory preserved)."""
    session_id = get_or_create_session(session_id)
    agent = _session_agents[session_id]
    print(f"[AGENT] Session {session_id}: {len(agent.messages)} messages in history before call")

    # Always pre-fetch relevant KB context and inject it into the prompt
    kb_docs = retrieve_context(question)
    if kb_docs:
        kb_context = "\n---\n".join(kb_docs)
        augmented_question = (
            f"{question}\n\n"
            f"[KNOWLEDGE BASE CONTEXT - use this information if relevant to the question above]:\n"
            f"{kb_context}"
        )
        print(f"[AGENT] Injected {len(kb_docs)} KB chunks into prompt")
    else:
        augmented_question = question
        print(f"[AGENT] No KB context found for this query")

    response = agent(augmented_question)
    print(f"[AGENT] Session {session_id}: {len(agent.messages)} messages in history after call")
    return {"answer": str(response), "session_id": session_id}

