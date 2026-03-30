import logging
import uuid

from fastapi import APIRouter

from api.schemas import ChatRequest, ChatResponse, SourceDocument
from retrieval.retriever import retrieve
from llm.generator import generate_answer

router = APIRouter()
logger = logging.getLogger("api.chat")


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest):
    """
    Send a question and receive an answer grounded in the knowledge base.

    - Retrieves relevant documents from the vector store
    - Generates an answer using the configured LLM
    - Returns the answer together with the source documents used
    """
    session_id = request.session_id or str(uuid.uuid4())
    question = request.question.strip()

    logger.info(f"[{session_id}] Question: {question}")

    documents = retrieve(question)

    if not documents:
        logger.warning(f"[{session_id}] No documents retrieved")
        return ChatResponse(
            answer="Tôi không tìm thấy thông tin phù hợp trong dữ liệu hiện có.",
            session_id=session_id,
            sources=[],
        )

    context = "\n\n".join(
        f"[{i+1}] {doc.text}\n(Nguồn: {doc.metadata})"
        for i, doc in enumerate(documents)
    )

    answer = generate_answer(context, question)
    logger.info(f"[{session_id}] Answer generated successfully")

    sources = [
        SourceDocument(id=doc.id, score=doc.score, text=doc.text, metadata=doc.metadata)
        for doc in documents
    ]

    return ChatResponse(answer=answer, session_id=session_id, sources=sources)
