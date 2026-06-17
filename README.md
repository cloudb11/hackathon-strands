# AI Hackathon Boilerplate (Strands Agent + RAG)

A conversational AI assistant with RAG (Retrieval-Augmented Generation), multi-turn conversation memory, and persistent session storage — built with the Strands Agents SDK.

## Key Features

- Conversation Memory — Per-session agents remember the full conversation history using SummarizingConversationManager (summarizes older messages instead of discarding them)
- Session Persistence — Conversations persist to disk via FileSessionManager and survive server restarts
- Smart RAG Chunking — Recursive, boundary-aware text splitting (paragraph → sentence → word) instead of naive character slicing
- Auto-Injected KB Context — Every query automatically retrieves relevant knowledge base chunks and injects them into the prompt (no reliance on tool-calling behavior)
- Persistent Vector Store — ChromaDB with PersistentClient so ingested documents survive restarts
- Multi-Format Ingestion — Supports .txt, .pdf, and .docx file uploads

## Directory Structure

```text
hackathon-strands/
├── backend/
│   ├── main.py              # FastAPI server with /ingest, /query, /session, /health endpoints
│   ├── ai_service.py        # Strands Agent setup with per-session memory & auto KB retrieval
│   ├── tools.py             # Agent tools (knowledge base search)
│   ├── rag.py               # RAG pipeline: smart chunking, persistent ingestion, filtered retrieval
│   ├── requirements.txt     # Python dependencies
│   ├── .sessions/           # [auto-created] Persisted conversation sessions
│   └── .chroma_db/          # [auto-created] Persistent ChromaDB vector store
├── frontend/
│   ├── index.html           # Single-page UI with session management
│   ├── app.js               # Frontend logic (upload, chat, session tracking)
│   └── style.css            # Styling
└── README.md
```

## Quick Start

1. Install dependencies
cd backend
pip install -r requirements.txt

2. Configure AI provider
Edit ai_service.py — uncomment the model provider you need. Set environment variables:

### For Bedrock (default)
export AWS_REGION="eu-central-1"
export AI_MODEL="eu.anthropic.claude-sonnet-4-5-20250929-v1:0"

### For OpenAI / compatible
export AI_API_KEY="your-key"
export AI_API_URL="https://api.openai.com/v1"
export AI_MODEL="gpt-4o"

### For Anthropic direct
export AI_MODEL="claude-sonnet-4-20250514"

3. Run backend
cd backend
uvicorn main:app --reload --port 8000

4. Run frontend
cd frontend
python -m http.server 3000
Open http://localhost:3000

API Endpoints
Method	Endpoint	Description
POST	/ingest	Upload a file (.txt, .pdf, .docx) to the knowledge base
POST	/query	Ask a question ({ "question": "...", "session_id": "..." })
POST	/session	Create a new conversation session explicitly
GET	/health	Health check
Multi-Turn Conversation Example
# First message — no session_id, one is auto-created
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "My name is Alice"}'
# → {"answer": "Hello Alice!", "session_id": "abc-123-..."}

# Follow-up — pass session_id back, agent remembers context
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is my name?", "session_id": "abc-123-..."}'
# → {"answer": "Your name is Alice!", "session_id": "abc-123-..."}

Architecture
┌─────────────┐       ┌──────────────────────────────────────────────┐
│  Frontend   │       │                  Backend                     │
│  (app.js)   │       │                                              │
│             │ POST  │  ┌──────────┐    ┌────────────────────────┐  │
│  tracks     │──────►│  │ main.py  │───►│ ai_service.py          │  │
│  session_id │ /query│  │ (FastAPI)│    │                        │  │
│             │◄──────│  └──────────┘    │  Per-session Agent     │  │
│             │       │                  │  ├─ SummarizingConvMgr │  │
└─────────────┘       │                  │  ├─ FileSessionManager │  │
                      │                  │  └─ Auto KB injection  │  │
                      │                  └────────────┬───────────┘  │
                      │                               │              │
                      │                  ┌────────────▼───────────┐  │
                      │                  │ rag.py                 │  │
                      │                  │  ├─ Recursive chunking │  │
                      │                  │  ├─ ChromaDB Persistent│  │
                      │                  │  └─ Distance filtering │  │
                      │                  └────────────────────────┘  │
                      └──────────────────────────────────────────────┘
How Queries Work
User sends a question (with optional session_id)
Backend auto-retrieves relevant KB chunks via retrieve_context()
KB context is injected into the prompt as a [KNOWLEDGE BASE CONTEXT] block
The per-session Strands Agent processes the augmented question with full conversation history
Agent can also call search_knowledge_base tool for additional targeted searches
Response is returned with the session_id for follow-up messages
Conversation Memory
SummarizingConversationManager — When context overflows, summarizes the oldest 30% of messages instead of discarding them. Always keeps the last 10 messages verbatim.
FileSessionManager — Persists session state to disk (.sessions/ folder). Conversations survive server restarts.
Smart Chunking (RAG)
Text is split using a recursive strategy with priority:

Paragraph boundaries (\n\n)
Sentence endings (. ! ?)
Word boundaries (spaces)
Hard character split (last resort)
Chunks use SHA-256 IDs with source filename + index for collision resistance.

Reset / Fresh Start
To start with a completely clean slate, delete the auto-generated data folders:

# Delete all conversation sessions
rm -rf backend/.sessions

# Delete all ingested knowledge base data
rm -rf backend/.chroma_db
Both folders are automatically re-created on the next server startup — no code changes needed.

Customization
Changing the System Prompt
Set the SYSTEM_PROMPT environment variable:

export SYSTEM_PROMPT="You are a medical assistant. Always cite sources from the knowledge base."
Adding More Tools
Create new functions in tools.py with the @tool decorator, then add them to the tools list in ai_service.py:

@tool
def analyze_sentiment(text: str) -> str:
    """Analyze the sentiment of the given text."""
    # your logic here
    return result
Tuning RAG Parameters
In rag.py:

max_size — Maximum chunk size in characters (default: 500)
overlap — Character overlap between chunks (default: 50)
max_distance — Similarity distance threshold for filtering retrieval results (default: 1.5)
In ai_service.py:

summary_ratio — Fraction of oldest messages to summarize on overflow (default: 0.3)
preserve_recent_messages — Number of recent messages to always keep verbatim (default: 10)
Dependencies
Package	Purpose
fastapi / uvicorn	API server
strands-agents	Agent SDK (conversation managers, session mgmt)
strands-agents-tools	Built-in tool utilities
boto3	AWS Bedrock model access
chromadb	Vector store (persistent)
python-multipart	File upload support
python-docx	.docx parsing
PyPDF2	.pdf parsing
