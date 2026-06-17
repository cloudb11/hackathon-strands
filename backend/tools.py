from strands import tool
from rag import retrieve_context


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information relevant to the query. Use this tool to find context before answering user questions."""
    docs = retrieve_context(query)
    if not docs:
        return "No relevant documents found in the knowledge base."
    return "\n---\n".join(docs)

