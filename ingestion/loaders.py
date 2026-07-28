# ingestion/loaders.py
import os
import re
import json
import shutil
import tempfile
import subprocess
from typing import List, Optional
from bs4 import BeautifulSoup

from pypdf import PdfReader
from llama_index.core import Document
import fitz
from PIL import Image
import io
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

import re

def is_readable(text: str) -> bool:
    if not text or len(text) < 30:
        return False

    # 1. Проверка на наличие осмысленных слов 
    words = re.findall(r'[a-zA-Zа-яА-Я]{3,}', text)
    if len(words) < 3:
        return False

    # 2. Доля букв (алфавитных символов)
    alpha_chars = sum(1 for c in text if c.isalpha())
    total_chars = len(text)
    if total_chars == 0:
        return False
    alpha_ratio = alpha_chars / total_chars
    if alpha_ratio < 0.2:  
        return False

    # 3. Проверка на gidXXXX 
    gid_matches = re.findall(r'gid\d+', text)
  
    gid_len = sum(len(m) for m in gid_matches)
    if gid_len / total_chars > 0.3:
        return False

    # 4. Доля печатаемых символов 
    printable = sum(1 for c in text if c.isprintable()) / total_chars
    if printable < 0.8:
        return False

    return True

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
                        "source": os.path.abspath(file_path)
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

def extract_images_from_chm(chm_path: str, output_dir: str) -> List[str]:
    """
  Извлекает все файлы изображений из CHM-файла и сохраняет их в выходную директорию (output_dir).
Возвращает список абсолютных путей к извлеченным изображениям.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico'}
    image_paths = []

    #  pychm 
    try:
        import chm
        chm_file = chm.CHMFile()
        chm_file.LoadCHM(chm_path)
        files = chm_file.GetFileList()
        for file_info in files:
            file_path = file_info[0]  
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in image_extensions:
                continue
            content = chm_file.ReadFile(file_path)
            if not content:
                continue
            # для создания безопасного имени файла из внутреннего пути
            safe_name = file_path.replace('/', '_').replace('\\', '_')
            if not safe_name:
                safe_name = f"chm_image_{len(image_paths)}.{ext[1:]}"
            save_path = os.path.join(output_dir, safe_name)
            with open(save_path, 'wb') as f:
                f.write(content)
            image_paths.append(os.path.abspath(save_path))
        chm_file.CloseCHM()
        if image_paths:
            return image_paths
    except Exception as e:
        print(f"pychm image extraction failed for {chm_path}: {e}")

    # Fallback: использовать 7z
    seven_zip = shutil.which("7z") or shutil.which("7za")
    if not seven_zip:
        print("7z не найден. Не удается извлечь изображения из CHM.")
        return []

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            cmd = [seven_zip, "x", chm_path, f"-o{tmpdir}", "-y"]
            subprocess.run(cmd, capture_output=True, timeout=60, check=True)

            for root, _, files in os.walk(tmpdir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext not in image_extensions:
                        continue
                    src_path = os.path.join(root, f)
                    # сохранять относительный путь внутри CHM
                    rel_path = os.path.relpath(src_path, tmpdir)
                    safe_name = rel_path.replace('/', '_').replace('\\', '_')
                    save_path = os.path.join(output_dir, safe_name)
                    # избежать коллизий имен
                    if os.path.exists(save_path):
                        base, ext2 = os.path.splitext(safe_name)
                        counter = 1
                        while os.path.exists(os.path.join(output_dir, f"{base}_{counter}{ext2}")):
                            counter += 1
                        save_path = os.path.join(output_dir, f"{base}_{counter}{ext2}")
                    shutil.copy2(src_path, save_path)
                    image_paths.append(os.path.abspath(save_path))
        except Exception as e:
            print(f"извлечение 7z не удалось из-за {chm_path}: {e}")
    return image_paths

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


def extract_images_from_pdf(pdf_path: str, output_dir: str = "data/images") -> List[str]:
    """Извлекает все изображения из PDF и сохраняет их в output_dir.
       Возвращает список путей к сохранённым файлам."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]
            # Генерируем имя файла
            image_filename = f"{os.path.basename(pdf_path)}_page{page_num+1}_img{img_index+1}.{ext}"
            image_path = os.path.join(output_dir, image_filename)
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            image_paths.append(image_path)
    doc.close()
    return image_paths



def load_html_directories(directory: str) -> List[Document]:
    docs = []
    for root_dir in os.listdir(directory):
        root_path = os.path.join(directory, root_dir)
        if not os.path.isdir(root_path):
            continue

        for dirpath, _, filenames in os.walk(root_path):
            for file in filenames:
                if file.lower().endswith(('.htm', '.html')):
                    file_path = os.path.join(dirpath, file)
                    try:
                        # читаем и парсим файл
                        content = None
                        for enc in ['utf-8', 'cp1251', 'latin-1']:
                            try:
                                with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                                    html_content = f.read()
                                content = html_content
                                break
                            except:
                                continue
                        if content is None:
                            continue

                        soup = BeautifulSoup(content, 'lxml')
                        for script in soup(["script", "style"]):
                            script.decompose()
                        text = soup.get_text(separator="\n")
                        cleaned = clean_text(text) if 'clean_text' in globals() else text.strip()
                        if cleaned and is_readable(cleaned):
                            # Создаём документ для этого HTML-файла
                            rel_path = os.path.relpath(file_path, start=directory)
                            docs.append(Document(
                                text=cleaned,
                                metadata={"source": rel_path, "type": "chm_html_single"}
                            ))
                    except Exception as e:
                        print(f"Ошибка чтения {file_path}: {e}")
    print(f"Загружено {len(docs)} отдельных HTML-документов из {directory}")
    return docs

def collect_images_from_html_folder(root_path: str) -> List[str]:
    """
    Рекурсивно обходит папку и возвращает полные пути ко всем файлам изображений.
    """
    image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
    images = []
    for dirpath, _, filenames in os.walk(root_path):
        for file in filenames:
            if os.path.splitext(file)[1].lower() in image_exts:
                images.append(os.path.join(dirpath, file))
    return images