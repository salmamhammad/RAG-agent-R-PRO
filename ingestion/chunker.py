# разбивка на чанки
from llama_index.core.node_parser import SentenceSplitter

def get_chunker():
    return SentenceSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separator=" ",
        paragraph_separator="\n\n"
    )