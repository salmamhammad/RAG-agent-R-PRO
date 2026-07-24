 # создание эмбеддингов, запись в Chroma
import os
from dotenv import load_dotenv
from llama_index.core import Settings, Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from ingestion.loaders import load_pdfs, load_text_files, load_chm_files, load_jsonl_files,load_faq_json_files, extract_images_from_chm, load_html_directories, collect_images_from_html_folder
from ingestion.chunker import get_chunker
from ingestion.state import get_files_state, load_state, save_state

from backend.image_captioner import generate_caption
from ingestion.loaders import extract_images_from_pdf
# Загружаем переменные окружения 
load_dotenv()

DATA_DOCS = os.getenv("DATA_DOCS", "data/docs")
DATA_CHM = os.getenv("DATA_CHM", "data/chm")
DATA_JSONL = os.getenv("DATA_JSONL", "data/jsonl")
DATA_FAQ = os.getenv("DATA_FAQ", "data/faq")
DATA_IMAGE = os.getenv("DATA_IMAGE", "data/images")
DATA_HTML=os.getenv("DATA_HTML", "data/chm_html")
ROOT_DIRS = [DATA_DOCS, DATA_CHM, DATA_JSONL, DATA_FAQ]
def build_index():
    # Настройка эмбеддингов
    embedding_model = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
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

    print(f" Обрабатываем {len(files_to_process)} файлов...")
    # # работа с изображением
    image_docs = []
    PROCESS_IMAGES= os.getenv("PROCESS_IMAGES", "false")
    if PROCESS_IMAGES.lower() == "true":
        os.makedirs(DATA_IMAGE, exist_ok=True)
        print("Обработка изображений из pdf.")
        pdf_docs = load_pdfs(DATA_DOCS)  # теперь каждый документ содержит абсолютный путь в metadata["source"]
        for pdf_doc in pdf_docs:
           pdf_path = pdf_doc.metadata.get("source", "")
           if os.path.exists(pdf_path):
               image_paths = extract_images_from_pdf(pdf_path, DATA_IMAGE)
               for img_path in image_paths:
                   caption = generate_caption(img_path)
                   if caption:
                        doc = Document(
                        text=f"Изображение: {caption}",
                        metadata={
                           "source": pdf_path,
                           "image_path": img_path,
                           "type": "image"
                        }
                        )
                        image_docs.append(doc)
        print("Обработка изображений из chm.")
        for chm_folder in os.listdir(DATA_HTML):
            folder_path = os.path.join(DATA_HTML, chm_folder)
            if os.path.isdir(folder_path):
                images = collect_images_from_html_folder(folder_path)
                for img_path in images:
                    caption = generate_caption(img_path)
                    if caption:
                        doc = Document(
                            text=f"Изображение: {caption}",
                            metadata={
                                "source": chm_folder,
                                "image_path": img_path,
                                "type": "image"
                            }
                        )
                        image_docs.append(doc)
    else:
        print("Обработка изображений отключена.")
    # # Загрузка документов
    print("Загрузка документов...")
    all_docs = (
       load_pdfs(DATA_DOCS)
       + load_text_files(DATA_DOCS)
    #    + load_chm_files(DATA_CHM)         
       + load_jsonl_files(DATA_JSONL)
       + load_faq_json_files(DATA_FAQ)
       + load_html_directories(DATA_HTML)  
       + image_docs 
    )  
    print(f"Загружено all_docs {len(all_docs)} документов для индексации")

    filtered_docs = []
    for doc in all_docs:
        source = doc.metadata.get("source", "")
        rel_path = os.path.relpath(source, start=".")
        if rel_path in files_to_process:
            filtered_docs.append(doc)
            # print(f"добавить файл: {os.path.basename(source)}") 
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