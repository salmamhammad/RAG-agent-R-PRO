# загрузка PDF, текстовых файлов, chm файлов
import os
from typing import List
from pypdf import PdfReader
from llama_index.core import Document
import shutil
import tempfile
import subprocess
# загрузка PDF
def load_pdfs(directory: str) -> List[Document]:
    docs = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".pdf"):
                file_path = os.path.join(root, file)
                try:
                    reader = PdfReader(file_path)
                    text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                    if text.strip():
                        # В метаданные сохраняем относительный путь для удобства
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