# загрузка PDF, текстовых файлов, chm файлов
import os
from typing import List, Optional
from pypdf import PdfReader
from llama_index.core import Document
import shutil
import tempfile
import subprocess
import json
import chardet
# загрузка PDF
# def load_pdfs(directory: str) -> List[Document]:
#     docs = []
#     for root, _, files in os.walk(directory):
#         for file in files:
#             if file.lower().endswith(".pdf"):
#                 file_path = os.path.join(root, file)
#                 try:
#                     reader = PdfReader(file_path)
#                     text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
#                     if text.strip():
#                         # В метаданные сохраняем относительный путь для удобства
#                         rel_path = os.path.relpath(file_path, start=".")
#                         docs.append(Document(text=text, metadata={"source": rel_path}))
#                 except Exception as e:
#                     print(f"Ошибка при чтении {file}: {e}")
#     return docs
def load_pdfs(directory: str) -> List[Document]:
    docs = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        # Проверяем, что это файл (а не папка) и заканчивается на .pdf
        if os.path.isfile(file_path) and file.lower().endswith(".pdf"):
            try:
                reader = PdfReader(file_path)
                text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                if text.strip():
                    rel_path = os.path.relpath(file_path, start=".")
                    docs.append(Document(text=text, metadata={"source": rel_path}))
            except Exception as e:
                print(f"Ошибка при чтении {file}: {e}")
    return docs

#загрузка текстовых файлов
def load_text_files(directory: str) -> List[Document]:
    docs = []
    for file in os.listdir(directory):
        if file.endswith(".txt") or file.endswith(".md"):
            with open(os.path.join(directory, file), "r", encoding="utf-8") as f:
                text = f.read()
            docs.append(Document(text=text, metadata={"source": file}))
    return docs

# загрузка chm файлов
def load_chm_files(directory: str) -> List[Document]:
    docs = []
    # Проверяем, доступен ли модуль chm (pychm)
    try:
        import chm
        from bs4 import BeautifulSoup
        use_pychm = True
        print("Используем pychm для CHM.")
    except ImportError:
        use_pychm = False
        print("pychm не установлен. Пробуем использовать 7z...")

    for file in os.listdir(directory):
        if not file.lower().endswith(".chm"):
            continue

        chm_path = os.path.join(directory, file)
        all_text = []

        if use_pychm:
            #  pychm 
            try:
                chm_file = chm.CHMFile()
                chm_file.LoadCHM(chm_path)
                files = chm_file.GetFileList()
                for file_info in files:
                    file_path = file_info[0]
                    if not file_path.lower().endswith(('.html', '.htm')):
                        continue
                    content = chm_file.ReadFile(file_path)
                    if not content:
                        continue
                    # Пытаемся декодировать
                    try:
                        html_content = content.decode('utf-8', errors='ignore')
                    except:
                        html_content = content.decode('cp1251', errors='ignore')
                    soup = BeautifulSoup(html_content, 'lxml')
                    for script in soup(["script", "style"]):
                        script.decompose()
                    text = soup.get_text(separator="\n")
                    lines = (line.strip() for line in text.splitlines())
                    text = '\n'.join(line for line in lines if line)
                    if text:
                        all_text.append(text)
                chm_file.CloseCHM()
            except Exception as e:
                print(f"Ошибка pychm для {file}: {e}. Пробуем 7z...")
                use_pychm = False  
                all_text = []  

        if not use_pychm or not all_text:
            #  7z 
            # Проверяем наличие 7z
            seven_zip = shutil.which("7z") or shutil.which("7za")
            if not seven_zip:
                print("7z не найден. Пропускаем CHM файлы.")
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    cmd = [seven_zip, "x", chm_path, f"-o{tmpdir}", "-y"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode != 0:
                        print(f"Ошибка 7z для {file}: {result.stderr}")
                        continue

                    # Читаем все HTML из tmpdir
                    try:
                        from bs4 import BeautifulSoup
                    except ImportError:
                        print("BeautifulSoup не установлен, не могу парсить HTML.")
                        continue

                    for root, _, files in os.walk(tmpdir):
                        for f in files:
                            if f.lower().endswith(('.html', '.htm')):
                                file_path = os.path.join(root, f)
                                try:
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as html_file:
                                        html_content = html_file.read()
                                    soup = BeautifulSoup(html_content, 'lxml')
                                    for script in soup(["script", "style"]):
                                        script.decompose()
                                    text = soup.get_text(separator="\n")
                                    lines = (line.strip() for line in text.splitlines())
                                    text = '\n'.join(line for line in lines if line)
                                    if text:
                                        all_text.append(text)
                                except Exception as e:
                                    print(f"Ошибка чтения {f}: {e}")
                except Exception as e:
                    print(f"Ошибка 7z для {file}: {e}")

        if all_text:
            combined_text = "\n\n".join(all_text)
            docs.append(Document(text=combined_text, metadata={"source": file}))
        else:
            print(f"Не удалось извлечь текст из CHM: {file}")

    return docs

# загрузка jsonl
def detect_encoding(file_path: str) -> str:
    """Определяет кодировку файла по первым 10 000 байт."""
    with open(file_path, "rb") as f:
        raw = f.read(10000)
        result = chardet.detect(raw)
        return result['encoding'] if result['encoding'] else 'utf-8'


def load_jsonl_files(
    directory: str,
    text_fields: Optional[List[str]] = None
) -> List[Document]:
    if text_fields is None:
        text_fields = ["subject", "body", "conversation_topic"]

    docs = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if not (os.path.isfile(file_path) and file.lower().endswith(".jsonl")):
            continue

        rel_path = os.path.relpath(file_path, start=".")

        # Определяем кодировку
        lines = None
        for encoding in ['utf-8', 'cp1251', 'latin-1']:
            try:
                with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                    lines = f.readlines()
                print(f"Чтение {file} в кодировке {encoding}")
                break
            except Exception:
                continue
        if lines is None:
            print(f"Не удалось прочитать {file}")
            continue

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Ошибка парсинга {file}: строка {line_num} - {e}")
                continue

            text_parts = []
            metadata = {
                "source": rel_path,
                "line": line_num
            }

            # Добавляем короткие поля в метаданные
            short_fields = ["folder", "from_name", "from_email", "to", "cc", 
                           "subject", "conversation_id", "conversation_topic", 
                           "has_attachments"]
            for key in short_fields:
                if key in data:
                    value = data[key]
                    if isinstance(value, str):
                        # Обрезаем слишком длинные значения
                        if len(value) > 100:
                            metadata[key] = value[:100] + "..."
                        else:
                            metadata[key] = value
                    else:
                        metadata[key] = value

            # Текстовые поля
            for key in text_fields:
                if key in data and isinstance(data[key], str) and data[key].strip():
                    text_parts.append(data[key].strip())

            # Добавляем количество вложений вместо полного списка
            if "attachments" in data and isinstance(data["attachments"], list):
                metadata["attachments_count"] = len(data["attachments"])

            if text_parts:
                full_text = "\n".join(text_parts)
                docs.append(Document(text=full_text, metadata=metadata))
            else:
                print(f"Нет текста в строке {line_num} файла {file}")

    return docs