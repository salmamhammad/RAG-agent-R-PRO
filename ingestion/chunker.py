# ingestion/chunker.py
from llama_index.core.node_parser import SentenceSplitter

def get_chunker():
    return SentenceSplitter(
        chunk_size=256,            
        chunk_overlap=30,
        separator=" ",
        paragraph_separator="\n\n",
        include_metadata=False       
    )