import os
import logging
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, Settings, Document
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.node_parser import SentenceSplitter
from typing import List, Optional
from backend.chroma_client import get_vector_store
from backend.llm_provider import LLMProvider,  get_llm_provider 
from backend.groq_provider import GroqProvider
from backend.utils import format_sources, setup_logging, get_logger, load_forbidden_terms, contains_forbidden_term, is_term_in_context, parse_response
from llama_index.core.schema import NodeWithScore, TextNode
# Загружаем переменные окружения 
load_dotenv()

# Настраиваем логирование
setup_logging(log_file="logs/app.log", level=logging.INFO)
logger = get_logger(__name__)  
class RAGEngine:
    def __init__(self, llm: LLMProvider = None, **llm_kwargs):
        # Устанавливаем локальную модель эмбеддингов (поддержка русского)
        
        self.vector_top_k = int(os.getenv("VECTOR_TOP_K", "30")) 
        self.bm25_top_k = int(os.getenv("BM25_TOP_K", "30")) 
        self.top_k = int(os.getenv("TOP_K", "5"))  
        embedding_model = os.getenv("EMBEDDING_MODEL", "d0rj/e5-small-en-ru")
        Settings.embed_model = HuggingFaceEmbedding(model_name=embedding_model, max_length=512)
        # openai/gpt-oss-120b
        # openai/gpt-oss-20b
        # d0rj/e5-small-en-ru
        #qwen/qwen3-32b

        self.vector_store = get_vector_store()
        # Создаём индекс из векторного хранилища
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        self._build_bm25_retriever()
        manual_filters = MetadataFilters(filters=[ExactMatchFilter(key="source_type", value="manual")])
        self.retriever_manual = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=self.vector_top_k,
            filters=manual_filters
        )
        self.retriever_all = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=self.vector_top_k
        )
        self._build_bm25_retriever()
        # self.retriever = VectorIndexRetriever(index=self.index, similarity_top_k=self.vector_top_k, filters=filters)
        self.forbidden_terms = load_forbidden_terms()
        # Если llm не передан, создаём GroqProvider с переданными параметрами
        if llm is None:
            self.llm = get_llm_provider(**llm_kwargs)
        else:
            self.llm = llm
    
    def _build_bm25_retriever(self):
        """Создать средство поиска BM25 из всех документов в индексе."""
        try:
            # Извлечь все узлы из индекса
            all_nodes = list(self.index.docstore.docs.values())
            if not all_nodes:
                logger.warning("No nodes found for BM25 index.")
                self.bm25_retriever = None
                return

            # При необходимости можно использовать простой разветвитель
            self.bm25_retriever = BM25Retriever.from_defaults(
                nodes=all_nodes,
                similarity_top_k=self.bm25_top_k
            )
            logger.info(f"BM25 index built with {len(all_nodes)} nodes.")
        except Exception as e:
            logger.error(f"Failed to build BM25 retriever: {e}")
            self.bm25_retriever = None    
    
    def _normalize_score(self, score, min_val=None, max_val=None):
        """Простая нормализация минимума-максимума."""
        if min_val is None or max_val is None:
            return score
        if max_val == min_val:
            return 1.0
        return (score - min_val) / (max_val - min_val)
                
    def count_chunks(self):
        return self.vector_store._collection.count()

    def _hybrid_retrieve_with_retriever(self, query: str, retriever, filter_for_bm25: Optional[str] = None) -> List[NodeWithScore]:
        """
       Выполнить гибридный поиск, используя заданный векторный поисковик.
При желании отфильтровать результаты BM25 по типу источника (если задан параметр filter_for_bm25).
        """
        # Векторный поиск
        vector_nodes = retriever.retrieve(query)
        vector_scores = {n.node.node_id: n.score for n in vector_nodes}

        # Поиск BM25
        bm25_nodes = []
        if self.bm25_retriever:
            try:
                bm25_nodes = self.bm25_retriever.retrieve(query)
            except Exception as e:
                logger.warning(f"BM25 search failed: {e}")

        # Если запрашивается фильтр BM25, сохраняйте только те, у которых совпадает source_type.
        if filter_for_bm25 and bm25_nodes:
            bm25_nodes = [n for n in bm25_nodes if n.node.metadata.get("source_type") == filter_for_bm25]

        bm25_scores = {n.node.node_id: n.score for n in bm25_nodes}

        # Объединение и нормализация оценок
        all_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
        if not all_ids:
            return []
    
        all_scores = list(vector_scores.values()) + list(bm25_scores.values())
        min_s = min(all_scores) if all_scores else 0
        max_s = max(all_scores) if all_scores else 1

        merged = []
        for node_id in all_ids:
            vec_score = vector_scores.get(node_id, 0.0)
            bm25_score = bm25_scores.get(node_id, 0.0)

            norm_vec = self._normalize_score(vec_score, min_s, max_s)
            norm_bm25 = self._normalize_score(bm25_score, min_s, max_s)

            combined = 0.6 * norm_vec + 0.4 * norm_bm25

            # найти соответствующий узел
            node = None
            if node_id in [n.node.node_id for n in vector_nodes]:
                node = next(n.node for n in vector_nodes if n.node.node_id == node_id)
            elif node_id in [n.node.node_id for n in bm25_nodes]:
                node = next(n.node for n in bm25_nodes if n.node.node_id == node_id)

            if node:
                merged.append(NodeWithScore(node=node, score=combined))

        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:self.top_k]

    def hybrid_retrieve(self, query: str) -> List[NodeWithScore]:
       # Во-первых, старайтесь получать данные только из источников, указанных вручную.
       nodes = self._hybrid_retrieve_with_retriever(query, self.retriever_manual, filter_for_bm25="manual")
       if nodes:
          print("Sample node metadata:", nodes[0].metadata)
          logger.info(f"Retrieved {len(nodes)} nodes from manual sources.")
          return nodes

       # получить из всех источников
       logger.info("No manual nodes found, falling back to all sources.")
       nodes = self._hybrid_retrieve_with_retriever(query, self.retriever_all, filter_for_bm25=None)
       return nodes

    def retrieve(self, query: str):
        # Legacy method – keep for backward compatibility or replace with hybrid_retrieve
        return self.hybrid_retrieve(query)

    def _enrich_query_with_history(self, query: str, history: list = None) -> str:
        """Если пользователь задал уточняющий вопрос, объедините его с предыдущим вопросом."""
        if history and len(history) > 0:
            last_user_msg = None
            for msg in reversed(history):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break
            if last_user_msg:
                if last_user_msg.lower() != query.lower():
                    return f"{last_user_msg} {query}"
        return query
    
    def answer(self, query: str, history: list = None) -> dict:
        search_query = self._enrich_query_with_history(query, history)
        nodes = self.retrieve(search_query)

        # Если есть релевантные чанки – работаем с контекстом
        if nodes:
            context = "\n\n".join([node.get_content() for node in nodes])
            sources = format_sources(nodes, max_text_len=200)
            
            for src, n in zip(sources, nodes):
                src["section"] = n.node.metadata.get("section", "")
                src["page"] = n.node.metadata.get("page_title", "")
                src["source_type"] = n.node.metadata.get("source_type", "")
                
            system_prompt = (
                   "Ты — ИИ-помощник техподдержки. "
                   "Твоя задача — дать полезный ответ на основе ПРЕДОСТАВЛЕННОГО КОНТЕКСТА. "
                   "Если в контексте есть информация, которая позволяет ответить на вопрос, используй её, даже если она не является дословным совпадением. "
                   "Ты можешь обобщать, перефразировать и комбинировать факты из разных частей контекста. "
                   "Если в контексте нет информации, которая хотя бы косвенно относится к вопросу, честно скажи: "
                   "«В предоставленных материалах нет информации по этому вопросу. Обратитесь к инженеру поддержки.» "
                   "Не выдумывай информацию, которой нет в контексте. Отвечай на русском языке."
            )
            user_content = f"Контекст:\n{context}\n\nВопрос пользователя: {query}\n\nВажно: если ответа нет в контексте, скажи, что не знаешь."
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-8:])  # последние 8 сообщений
            messages.append({"role": "user", "content": user_content})
            # logger.info(f"messages:{messages}")
            answer = self.llm.generate(messages)
            answer, think_content = parse_response(answer)
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
            return {"answer": answer, "sources": sources, "think": think_content, "has_context": True, "images": images}

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
            answer, think_content = parse_response(answer)

            if self.forbidden_terms and contains_forbidden_term(answer, self.forbidden_terms):
                answer = (
                    "Извините, я не могу ответить на этот вопрос, так как он выходит за рамки моей компетенции. "
                    "Пожалуйста, обратитесь к инженеру поддержки."
                )
                logger.warning("Ответ заменён (нет контекста, но модель упомянула запрещённый термин).")
            return {"answer": answer, "sources": [], "think": think_content, "has_context": False, "images": []}
        
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
           self._build_bm25_retriever()
        else:
           print(" Не удалось создать узлы для ответа инженера.")