# check_chroma.py
import chromadb

client = chromadb.PersistentClient(path="chroma_db")
print(f"Collections: {client.list_collections()}")

# Try to get the collection
try:
    collection = client.get_collection("support_knowledge")
    count = collection.count()
    print(f"Collection 'support_knowledge' has {count} items")
    
    # Get first 3 IDs to confirm
    if count > 0:
        ids = collection.get()['ids'][:3]
        print(f"Sample IDs: {ids}")
    else:
        print("Collection exists but is empty")
except ValueError as e:
    print(f"Collection not found: {e}")