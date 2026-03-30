import logging
import os
from core.settings_loader import load_settings
from retrieval.retriever import retrieve
from llm.generator import generate_answer

settings = load_settings()
logger = logging.getLogger("chat")

MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", 512))

def chat(question: str) -> str:
    if not question:
        logger.warning("Received empty question.")
        return "Xin vui lòng nhập câu hỏi."
    
    if len(question) > MAX_QUERY_LENGTH:
        logger.warning(f"Question length {len(question)} exceeds maximum of {MAX_QUERY_LENGTH}. Truncating.")
        question = question[:MAX_QUERY_LENGTH]
    logger.info(f"Received question: {question}")

    try:
        documents = retrieve(question)
        if not documents:
            logger.info("No relevant documents found for the question.")
            return "Xin lỗi, tôi không tìm thấy thông tin liên quan để trả lời câu hỏi của bạn."
        
        context = "\n\n".join(
            f"[{i+1}] {doc.text} \n(Nguồn: {doc.metadata})" for i, doc in enumerate(documents)
        )

        answer = generate_answer(context, question)
        logger.info("Generated answer successfully.")  
        return answer

    except ValueError as e:
        logger.error(f"Error during retrieval: {e}")
        return "Xin lỗi, đã xảy ra lỗi khi tìm kiếm thông tin."

def main():
    while True:
        question = input("Bạn: ")
        if question.lower() in {"exit", "quit", "thoát"}:
            print("Tạm biệt!")
            break
        answer = chat(question)
        print(f"Chatbot: {answer}")

if __name__ == "__main__":
    main()