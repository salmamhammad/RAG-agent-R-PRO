import requests
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np

def diagnose_system():
    print("🔍 RAG SYSTEM DIAGNOSTIC")
    print("=" * 50)
    
    # 1. Check backend
    print("\n1️⃣ Checking backend...")
    try:
        resp = requests.get("http://localhost:8000/health", timeout=5)
        print(f"   ✅ Backend running: {resp.json()}")
    except:
        print("   ❌ Backend not running")
        return
    
    # 2. Check ChromaDB
    print("\n2️⃣ Checking vector database...")
    try:
        client = chromadb.PersistentClient(path="chroma_db")
        collection = client.get_collection("support_knowledge")
        count = collection.count()
        print(f"   📊 Total chunks: {count}")
        if count == 0:
            print("   ❌ Database is empty! Run indexing.")
    except:
        print("   ❌ ChromaDB not found or corrupted")
    
    # 3. Test a real query
    print("\n3️⃣ Testing a real query...")
    test_queries = [
        "Как обновить лицензию?",
        "Что такое R-Pro?",
        "Системные требования"
    ]
    for q in test_queries[:2]:
        try:
            resp = requests.post("http://localhost:8000/chat", 
                               json={"question": q, "history": []}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print(f"\n   ✅ Query: {q[:50]}...")
                print(f"   📝 Answer: {data['answer'][:100]}...")
                print(f"   📚 Sources: {len(data.get('sources', []))}")
            else:
                print(f"\n   ❌ Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"\n   ❌ Failed: {str(e)}")

if __name__ == "__main__":
    diagnose_system()