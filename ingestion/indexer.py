 # создание эмбеддингов, запись в Chroma
import os
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from ingestion.loaders import load_pdfs, load_text_files, load_chm_files
from ingestion.chunker import get_chunker

def build_index():
    # Настройка эмбеддингов
    embedding_model = os.getenv("EMBEDDING_MODEL", "d0rj/e5-small-en-ru")
    Settings.embed_model = HuggingFaceEmbedding(model_name=embedding_model)
    # openai/gpt-oss-120b
    # openai/gpt-oss-20b
    # d0rj/e5-small-en-ru
        # intfloat/multilingual-e5-base
        # paraphrase-multilingual-MiniLM
    # Подключение к ChromaDB 
    chroma_client = chromadb.PersistentClient(path="chroma_db")
    collection = chroma_client.get_or_create_collection("support_knowledge")
    vector_store = ChromaVectorStore(chroma_collection=collection)

    # Загрузка документов
    print("Загрузка документов...")
    docs = load_pdfs("data/docs") + load_text_files("data/docs")+ load_chm_files("data/chm")
    print(f"Загружено {len(docs)} документов")
    if not docs:
        print("Нет документов для индексации")
        return

    # Разбивка на чанки
    print("Разбивка на чанки...")
    chunker = get_chunker()
    nodes = chunker.get_nodes_from_documents(docs)
    print(f"Создано {len(nodes)} узлов")
    # Создание индексного хранилища 
    from llama_index.core import VectorStoreIndex
    index = VectorStoreIndex.from_vector_store(vector_store)
    index.insert_nodes(nodes)    
    index.storage_context.persist(persist_dir="storage")  
    print(f"Индексация завершена. Добавлено {len(nodes)} чанков.")