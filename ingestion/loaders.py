# ingestion/loaders.py
import os
import re
import json
import shutil
import tempfile
import subprocess
from typing import List, Optional
from pypdf import PdfReader
from llama_index.core import Document
import fitz
def clean_text(text: str) -> str:
    """Удаляет URL, email, управляющие символы и бинарный мусор."""
    if not text:
        return ""
    # Удаляем URL
    url_pattern = r'https?://\S+|www\.\S+|<https?://[^>]+>|<[^>]+>'
    text = re.sub(url_pattern, '', text)
    # Удаляем email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    text = re.sub(email_pattern, '', text)
    # Заменяем управляющие символы на пробелы
    text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    # Удаляем непечатаемые символы
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    # Оставляем только буквы, цифры, пробелы и базовую пунктуацию
    text = re.sub(r'[^\w\s.,!?;:()"\'\-]', ' ', text)
    # Схлопываем пробелы
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_readable(text):
    if len(text) < 50:
        return False

    # reject lots of gidXXXX
    gid = len(re.findall(r"gid\d+", text))
    if gid > 5:
        return False

    # reject extremely long "words"
    words = text.split()
    if words:
        avg = sum(len(w) for w in words) / len(words)
        if avg > 20:
            return False

    printable = sum(c.isprintable() for c in text) / len(text)

    return printable > 0.95

# ---------- ЗАГРУЗЧИКИ ----------

def load_pdfs(directory: str) -> List[Document]:
    docs = []


    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)

        if not (os.path.isfile(file_path) and file.lower().endswith(".pdf")):
            continue

        try:
            pdf = fitz.open(file_path)

            text_parts = []

            for page_num, page in enumerate(pdf):
                # извлечь текст, сохраняя порядок чтения в максимально возможной степени.
                raw = page.get_text("text")

                if not raw:
                    continue

                cleaned = clean_text(raw)

                if not cleaned:
                    continue

                if not is_readable(cleaned):
                    print(f"Unreadable page {page_num + 1} in {file}")
                    continue

                text_parts.append(cleaned)

            pdf.close()

            if not text_parts:
                print(f"No readable text extracted from: {file}")
                continue

            full_text = "\n".join(text_parts)

            docs.append(
                Document(
                    text=full_text,
                    metadata={
                        "source": os.path.relpath(file_path, start=".")
                    },
                )
            )

        except Exception as e:
            print(f"Error reading {file}: {e}")

    return docs

def load_text_files(directory: str) -> List[Document]:
    docs = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and file.lower().endswith((".txt", ".md")):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
                cleaned = clean_text(raw)
                if cleaned and is_readable(cleaned):
                    rel_path = os.path.relpath(file_path, start=".")
                    docs.append(Document(text=cleaned, metadata={"source": rel_path}))
                else:
                    print(f" Пропущен нечитаемый текст: {file}")
            except Exception as e:
                print(f"Ошибка при чтении {file}: {e}")
    return docs

def load_chm_files(directory: str) -> List[Document]:
    docs = []
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
        extracted = False

        if use_pychm:
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
                    # Декодируем
                    try:
                        html_content = content.decode('utf-8', errors='ignore')
                    except:
                        html_content = content.decode('cp1251', errors='ignore')

                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, 'lxml')
                    for script in soup(["script", "style"]):
                        script.decompose()
                    raw_text = soup.get_text(separator="\n")
                    cleaned = clean_text(raw_text)
                    if cleaned and is_readable(cleaned):
                        all_text.append(cleaned)

                chm_file.CloseCHM()
                extracted = True
            except Exception as e:
                print(f"Ошибка pychm для {file}: {e}. Пробуем 7z...")
                all_text = []

        if not extracted or not all_text:
            # 7z
            seven_zip = shutil.which("7z") or shutil.which("7za")
            if not seven_zip:
                print("7z не найден. Пропускаем CHM файлы.")
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    cmd = [seven_zip, "x", chm_path, f"-o{tmpdir}", "-y"]
                    subprocess.run(cmd, capture_output=True, timeout=60, check=True)

                    from bs4 import BeautifulSoup
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
                                    raw_text = soup.get_text(separator="\n")
                                    cleaned = clean_text(raw_text)
                                    if cleaned and is_readable(cleaned):
                                        all_text.append(cleaned)
                                except Exception as e:
                                    print(f"Ошибка чтения {f}: {e}")
                except Exception as e:
                    print(f"Ошибка 7z для {file}: {e}")

        if all_text:
            combined_text = "\n\n".join(all_text)
            if is_readable(combined_text):
                docs.append(Document(text=combined_text, metadata={"source": file}))
            else:
                print(f" Пропущен нечитаемый CHM: {file}")
        else:
            print(f"Не удалось извлечь текст из CHM: {file}")

    return docs


def load_jsonl_files(
    directory: str,
    text_fields: Optional[List[str]] = None
) -> List[Document]:
    if text_fields is None:
        text_fields = ["subject", "body"]

    docs = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if not (os.path.isfile(file_path) and file.lower().endswith(".jsonl")):
            continue

        rel_path = os.path.relpath(file_path, start=".")

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
            for key in text_fields:
                if key in data and isinstance(data[key], str) and data[key].strip():
                    cleaned = clean_text(data[key])
                    if cleaned and is_readable(cleaned):
                        text_parts.append(cleaned)

            if text_parts:
                full_text = "\n".join(text_parts)
                if is_readable(full_text):
                    docs.append(Document(
                        text=full_text,
                        metadata={"source": rel_path, "line": line_num}
                    ))
                else:
                    print(f" Пропущен нечитаемый текст в {file} строка {line_num}")
            else:
                print(f"Нет текста в строке {line_num} файла {file}")

    return docs

def load_faq_json_files(directory: str) -> List[Document]:
    """
    Загружает JSON-файлы с FAQ из указанной папки.
    Ожидает структуру: { "faq": [ { "category": "...", "question": "...", "answer": "..." } ] }
    Каждый FAQ-элемент становится отдельным Document.
    """
    docs = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if not (os.path.isfile(file_path) and file.lower().endswith(".json")):
            continue

        rel_path = os.path.relpath(file_path, start=".")

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON в {file}: {e}")
            continue
        except Exception as e:
            print(f"Ошибка чтения {file}: {e}")
            continue

        # Проверяем, есть ли ключ "faq" и является ли он списком
        faq_items = data.get("faq")
        if not isinstance(faq_items, list):
            print(f"Файл {file} не содержит ключ 'faq' со списком. Пропускаем.")
            continue

        for idx, item in enumerate(faq_items):
            if not isinstance(item, dict):
                print(f"Пропущен не-словарь в {file}, индекс {idx}")
                continue

            question = item.get("question", "").strip()
            answer = item.get("answer", "").strip()
            category = item.get("category", "").strip()

            if not question or not answer:
                print(f"Пропущен FAQ без вопроса или ответа в {file}, индекс {idx}")
                continue

            # Объединяем вопрос и ответ в один текст
            full_text = f"Вопрос: {question}\nОтвет: {answer}"

            # Очищаем текст
            cleaned = clean_text(full_text)
            if not cleaned or not is_readable(cleaned):
                print(f"Пропущен нечитаемый FAQ в {file}, индекс {idx}")
                continue

            metadata = {
                "source": rel_path,
                "category": category,
                "question": question,
                "faq_index": idx
            }

            docs.append(Document(text=cleaned, metadata=metadata))

    print(f"Загружено {len(docs)} FAQ-записей из JSON-файлов в {directory}")
    return docs
