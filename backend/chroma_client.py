# инициализация ChromaDB
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

def get_vector_store():
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection("support_knowledge")
    return ChromaVectorStore(chroma_collection=collection)