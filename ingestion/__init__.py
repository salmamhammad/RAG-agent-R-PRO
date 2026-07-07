# ingestion/__init__.py

from .chunker import get_chunker
from .indexer import build_index
from .loaders import load_pdfs,load_text_files



__all__ = [
    'get_chunker',
    'build_index',
    'load_pdfs',
    'load_text_files'
]