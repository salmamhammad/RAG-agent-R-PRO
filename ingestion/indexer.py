 # создание эмбеддингов, запись в Chroma
import os
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from ingestion.loaders import load_pdfs, load_text_files, load_chm_files, load_jsonl_files,load_faq_json_files
from ingestion.chunker import get_chunker
from ingestion.state import get_files_state, load_state, save_state

ROOT_DIRS = ["data/docs", "data/chm", "data/jsonl"]
def build_index():
    # Настройка эмбеддингов
    embedding_model = os.getenv("EMBEDDING_MODEL", "d0rj/e5-small-en-ru")
    Settings.embed_model = HuggingFaceEmbedding(
       model_name=embedding_model,
       max_length=512
    )
    # openai/gpt-oss-120b
    # openai/gpt-oss-20b
    # d0rj/e5-small-en-ru
        # intfloat/multilingual-e5-base
        # paraphrase-multilingual-MiniLM
    # Подключение к ChromaDB 
    chroma_client = chromadb.PersistentClient(path="chroma_db")
    collection = chroma_client.get_or_create_collection("support_knowledge")
    vector_store = ChromaVectorStore(chroma_collection=collection)

    # # Загружаем сохранённое состояние и текущее
    prev_state = load_state()
    current_state = get_files_state(ROOT_DIRS)
    
    # # Определяем файлы для обработки
    files_to_process = []
    for file, info in current_state.items():
        if file not in prev_state:
            files_to_process.append(file)
            print(f" Новый файл: {file}")
        elif prev_state[file] != info:
            files_to_process.append(file)
            print(f" Изменён файл: {file}")

    if not files_to_process:
        print(" Нет новых или изменённых файлов. Индексация не требуется.")
        return

    print(f" Обрабатываем files_to_process{len(files_to_process)} файлов...")
      
    # # Загрузка документов
    print("Загрузка документов...")
    all_docs =load_pdfs("data/docs") + load_text_files("data/docs")+ load_chm_files("data/chm") + load_jsonl_files("data/jsonl")+load_faq_json_files('data/faq')
    print(f"Загружено all_docs {len(all_docs)} документов для индексации")

    filtered_docs = []
    for doc in all_docs:
        # источник хранится в метаданных как "source" – это полный путь
        source = doc.metadata.get("source", "")
        rel_path = os.path.relpath(source, start=".")
        if rel_path in files_to_process:
            filtered_docs.append(doc)
            print(f"добавить файл: {file}")
    if not filtered_docs:
        print("Не найдено содержимого для указанных файлов.")
        return
    print(f"Загружено filtered_docs {len(filtered_docs)} документов для индексации")
    # Разбивка на чанки
    print("Разбивка на чанки...")
    chunker = get_chunker()
    nodes = chunker.get_nodes_from_documents(filtered_docs)
    print(f"Создано {len(nodes)} узлов")
    # Создание индексного хранилища 
    from llama_index.core import VectorStoreIndex
    index = VectorStoreIndex.from_vector_store(vector_store)
    index.insert_nodes(nodes)    
    index.storage_context.persist(persist_dir="storage")  
    save_state(current_state)
    print(f"Индексация завершена. Добавлено {len(nodes)} чанков.")