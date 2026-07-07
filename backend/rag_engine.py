import os
import logging
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from backend.chroma_client import get_vector_store
from backend.llm_provider import LLMProvider
from backend.groq_provider import GroqProvider
from backend.utils import format_sources, setup_logging, get_logger

# Настраиваем логирование
setup_logging(log_file="logs/app.log", level=logging.INFO)
logger = get_logger(__name__)  
class RAGEngine:
    def __init__(self, llm: LLMProvider = None, **llm_kwargs):
        # Устанавливаем локальную модель эмбеддингов (поддержка русского)
        top_k = int(os.getenv("TOP_K", "5"))
        embedding_model = os.getenv("EMBEDDING_MODEL", "d0rj/e5-small-en-ru")
        Settings.embed_model = HuggingFaceEmbedding(model_name=embedding_model)
        # openai/gpt-oss-120b
        # openai/gpt-oss-20b
        # d0rj/e5-small-en-ru
        #qwen/qwen3-32b

        self.vector_store = get_vector_store()
        # Создаём индекс из векторного хранилища
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        self.retriever = VectorIndexRetriever(index=self.index, similarity_top_k=top_k)
        
        # Если llm не передан, создаём GroqProvider с переданными параметрами
        if llm is None:
            self.llm = GroqProvider(**llm_kwargs)
        else:
            self.llm = llm

    def retrieve(self, query: str):
        nodes = self.retriever.retrieve(query)
        return nodes

    def answer(self, query: str, history: list = None) -> dict:
        nodes = self.retrieve(query)

        # Если есть релевантные чанки – работаем с контекстом
        if nodes:
            context = "\n\n".join([node.get_content() for node in nodes])
            sources = format_sources(nodes, max_text_len=200)
            system_prompt = (
                "Ты — ИИ-помощник техподдержки. Отвечай строго на основе предоставленного контекста. "
                "Если ответа нет в контексте, честно скажи, что не знаешь, и предложи обратиться к инженеру. "
                "Не выдумывай информацию. Отвечай на русском языке."
            )
            user_content = f"Контекст:\n{context}\n\nВопрос пользователя: {query}"
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-5:])  # последние 5 сообщений
            messages.append({"role": "user", "content": user_content})
            answer = self.llm.generate(messages)
            return {"answer": answer, "sources": sources}

        # Если нет релевантных чанков
        else:
            logger.info(f"failure: true...")
            # Обычный ответ "не знаю" через LLM 
            system_prompt = (
              "не нашёл в базе знаний, обратитесь к инженеру "
            )
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-5:])
            messages.append({"role": "user", "content": query})
            answer = self.llm.generate(messages)
            return {"answer": answer, "sources": []}