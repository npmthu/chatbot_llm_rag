import logging
import ollama
import time
from llm.prompt import build_prompt
from core.settings_loader import load_settings

settings = load_settings()
logger = logging.getLogger("llm")

LLM_CONFIG = settings["llm"]
MODEL_PROVIDER = LLM_CONFIG.get("provider", "ollama")
MODEL_NAME = LLM_CONFIG.get("model_name", "qwen2.5:3b")
MODEL_BASE_URL = LLM_CONFIG.get("base_url", "http://localhost:11434")
MODEL_API_KEY = LLM_CONFIG.get("api_key", "ollama")
MODEL_TEMPERATURE = LLM_CONFIG.get("temperature", 0.2)
MODEL_MAX_TOKENS = LLM_CONFIG.get("max_tokens", 1024)
MODEL_TIMEOUT = LLM_CONFIG.get("timeout", 60)


def generate_answer(context: str, question: str) -> str:
    start = time.time()
    if not context or not context.strip():
        logger.warning("Received empty context for answer generation.")
        return "Dữ liệu ngữ cảnh không được để trống."

    if not question or not question.strip():
        logger.warning("Received empty question for answer generation.")
        return "Câu hỏi không được để trống."

    prompt = build_prompt(context, question)
    logger.info(f"Generating answer using model: {MODEL_NAME} (provider: {MODEL_PROVIDER})")

    try:
        if MODEL_PROVIDER == "ollama":
            answer = _generate_ollama(prompt)
        elif MODEL_PROVIDER == "openai":
            answer = _generate_openai(prompt)
        else:
            logger.error(f"Unsupported model provider: {MODEL_PROVIDER}")
            return "Nhà cung cấp mô hình không được hỗ trợ."

        logger.info(f"Answer generation completed in {time.time() - start:.2f}s")
        return answer

    except Exception as e:
        logger.error(f"Error during answer generation: {e}")
        return "Đã xảy ra lỗi trong quá trình tạo câu trả lời."


def _generate_ollama(prompt: str) -> str:
    try:
        client = ollama.Client(host=MODEL_BASE_URL, timeout=MODEL_TIMEOUT)
        response = client.chat(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": prompt}],
            options={"temperature": MODEL_TEMPERATURE, "num_predict": MODEL_MAX_TOKENS},
        )
        return response["message"]["content"].strip()
    except ollama.RequestError as e:
        logger.error(f"Failed to connect to Ollama at {MODEL_BASE_URL}: {e}")
        return "Không thể kết nối Ollama. Hãy kiểm tra Ollama đang chạy và LLM_BASE_URL."
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error: {e}")
        return "Ollama phản hồi lỗi. Hãy kiểm tra model đã pull chưa (ollama pull qwen2.5:3b)."


def _generate_openai(prompt: str) -> str:
    from openai import OpenAI, APIConnectionError, APIStatusError
    try:
        client = OpenAI(base_url=MODEL_BASE_URL, api_key=MODEL_API_KEY, timeout=MODEL_TIMEOUT)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": prompt}],
            temperature=MODEL_TEMPERATURE,
            max_tokens=MODEL_MAX_TOKENS,
        )
        return response.choices[0].message.content.strip()
    except APIConnectionError as e:
        logger.error(f"Failed to connect to OpenAI-compatible API at {MODEL_BASE_URL}: {e}")
        return "Không thể kết nối đến dịch vụ LLM. Hãy kiểm tra LLM_BASE_URL và LLM_API_KEY."
    except APIStatusError as e:
        logger.error(f"API status error: {e.status_code} — {e.message}")
        return "Dịch vụ LLM trả về lỗi. Hãy kiểm tra API key và model name."