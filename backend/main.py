import io
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from ai_service import ask_agent, get_or_create_session
from rag import ingest_text

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def extract_text(filename: str, content: bytes) -> str:
    if filename.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif filename.endswith(".pdf"):
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        return content.decode("utf-8", errors="ignore")


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    content = await file.read()
    text = extract_text(file.filename, content)
    count = ingest_text(text, metadata={"source": file.filename})
    return {"chunks_stored": count}


@app.post("/query")
async def query(payload: dict):
    question = payload["question"]
    session_id = payload.get("session_id")
    print(f"[DEBUG /query] Received session_id={session_id!r} (type={type(session_id).__name__})")
    result = ask_agent(question, session_id=session_id)
    print(f"[DEBUG /query] Returning session_id={result['session_id']!r}")
    return result


@app.post("/session")
async def create_session():
    """Create a new conversation session explicitly."""
    session_id = get_or_create_session()
    return {"session_id": session_id}


@app.get("/health")
def health():
    return {"status": "ok"}

