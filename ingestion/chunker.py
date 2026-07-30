# ingestion/chunker.py
from llama_index.core.node_parser import SentenceSplitter

def get_chunker():
    return SentenceSplitter(
        chunk_size=512,            
        chunk_overlap=100,
        separator=" ",
        paragraph_separator="\n\n",
        include_metadata=True          
    )