# загрузка PDF, текстовых файлов
import os
from typing import List
from pypdf import PdfReader
from llama_index.core import Document

def load_pdfs(directory: str) -> List[Document]:
    docs = []
    for file in os.listdir(directory):
        if file.endswith(".pdf"):
            reader = PdfReader(os.path.join(directory, file))
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            docs.append(Document(text=text, metadata={"source": file}))
    return docs

def load_text_files(directory: str) -> List[Document]:
    docs = []
    for file in os.listdir(directory):
        if file.endswith(".txt") or file.endswith(".md"):
            with open(os.path.join(directory, file), "r", encoding="utf-8") as f:
                text = f.read()
            docs.append(Document(text=text, metadata={"source": file}))
    return docs