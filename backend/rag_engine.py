import os
import logging
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, Settings, Document
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from backend.chroma_client import get_vector_store
from backend.llm_provider import LLMProvider,  get_llm_provider 
from backend.groq_provider import GroqProvider
from backend.utils import format_sources, setup_logging, get_logger, load_forbidden_terms, contains_forbidden_term, is_term_in_context
from llama_index.core.schema import NodeWithScore, TextNode
# Загружаем переменные окружения 
load_dotenv()

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
        self.forbidden_terms = load_forbidden_terms()
        # Если llm не передан, создаём GroqProvider с переданными параметрами
        if llm is None:
            self.llm = get_llm_provider(**llm_kwargs)
        else:
            self.llm = llm
            
    def count_chunks(self):
        return self.vector_store._collection.count()

    def retrieve(self, query: str):
        print(f" Запрос: {query[:100]}...")
        # nodes = self.retriever.retrieve(query)
        # print(f" Найдено чанков: {len(nodes)}")
        # if nodes:
        #     print(f" Первый чанк: {nodes[0].get_content()[:100]}...")
        ####################################################
        from llama_index.core import Settings
        query_embedding = Settings.embed_model.get_query_embedding(query)
    
        # Выполняем поиск напрямую через ChromaDB (без where)
        results = self.vector_store._collection.query(
            query_embeddings=[query_embedding],
            n_results=self.retriever.similarity_top_k,
            where=None  # явно передаём None вместо {}
        )
    
        # Преобразуем результаты в Nodes       
        nodes = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                # TextNode
                node = TextNode(text=doc)
                if results['metadatas'] and results['metadatas'][0]:
                    node.metadata = results['metadatas'][0][i]
        
                #  Оборачиваем его в NodeWithScore и присваиваем score
                score = results['distances'][0][i] if 'distances' in results else 1.0
                nodes.append(NodeWithScore(node=node, score=score))
        
        return nodes

    def answer(self, query: str, history: list = None) -> dict:
        nodes = self.retrieve(query)

        # Если есть релевантные чанки – работаем с контекстом
        if nodes:
            context = "\n\n".join([node.get_content() for node in nodes])
            sources = format_sources(nodes, max_text_len=200)
            system_prompt = (
                "Ты — ИИ-помощник техподдержки. поприветствуй пользователя "
                "Отвечай строго на основе предоставленного контекста. "
                "Не делай предположений. Не используйте свои знания вне контекста. "
                "Не выдумывай информацию. Отвечай на русском языке."
            )
            user_content = f"Контекст:\n{context}\n\nВопрос пользователя: {query}\n\nВажно: если ответа нет в контексте, скажи, что не знаешь."
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-8:])  # последние 8 сообщений
            messages.append({"role": "user", "content": user_content})
            # logger.info(f"messages:{messages}")
            answer = self.llm.generate(messages)
            # проверка на запрещённые термины 
            if self.forbidden_terms:
                # Проверяем, есть ли в ответе запрещённые термины
                found_terms = [term for term in self.forbidden_terms if term in answer.lower()]
                if found_terms:
                    # Проверяем, есть ли какой-либо из найденных терминов в контексте
                    terms_in_context = [term for term in found_terms if is_term_in_context(term, context)]
                    if not terms_in_context:
                        # Ни один из запрещённых терминов не найден в контексте -> заменяем ответ
                        answer = (
                            "Извините, в предоставленных материалах нет информации, которая позволила бы ответить на этот вопрос. "
                            "Пожалуйста, обратитесь к инженеру поддержки."
                        )
                        # Логируем факт замены
                        logger.warning(f"Ответ заменён из-за запрещённых терминов: {found_terms} (отсутствуют в контексте)")
            images = []
            for node in nodes:
                img_path = node.metadata.get("image_path")
                if img_path and img_path not in images:
                    images.append(img_path)
            return {"answer": answer, "sources": sources, "has_context": True, "images": images}

        # Если нет релевантных чанков
        else:
            logger.info(f"node: false")
            # Обычный ответ "не знаю" через LLM 
            system_prompt = (
              "честно скажи, что не знаешь,"
              "не нашёл в базе знаний,  обратитесь к инженеру "
              "Не выдумывай информацию. Отвечай на русском языке."
            )
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-8:])
            messages.append({"role": "user", "content": query})
            answer = self.llm.generate(messages)
            if self.forbidden_terms and contains_forbidden_term(answer, self.forbidden_terms):
                answer = (
                    "Извините, я не могу ответить на этот вопрос, так как он выходит за рамки моей компетенции. "
                    "Пожалуйста, обратитесь к инженеру поддержки."
                )
                logger.warning("Ответ заменён (нет контекста, но модель упомянула запрещённый термин).")
            return {"answer": answer, "sources": [], "has_context": False}
        
    def add_document(self, text: str, metadata: dict = None):
        """Добавляет новый документ в векторную базу (для ответов инженера)."""
        from ingestion.chunker import get_chunker
        if metadata is None:
           metadata = {"source": "engineer_response"}
        for key, value in list(metadata.items()):
            if isinstance(value, str) and len(value) > 200:
               metadata[key] = value[:200] + "..."

        doc = Document(text=text, metadata=metadata)
        chunker = get_chunker()
        nodes = chunker.get_nodes_from_documents([doc])
        if nodes:
           self.index.insert_nodes(nodes)
           self.index.storage_context.persist(persist_dir="storage")
           print(f" Добавлен ответ инженера в RAG: {text[:50]}...")
        else:
           print(" Не удалось создать узлы для ответа инженера.")