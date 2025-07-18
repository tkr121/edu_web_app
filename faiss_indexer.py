import re
import sqlite3
import os
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import faiss
import time
from sentence_transformers import SentenceTransformer


class FaissBookSearcher:
    def __init__(self, db_path="faiss/tensorflow_books.db"):
        print("🔍 正在初始化 FaissBookSearcher...")
        self.importer = BookImporter(db_path)
        if not self.importer.faiss_index:
            self.importer.build_faiss_index()

    def search(self, queries: List[str], k=5):
        results = []
        seen_contents = set()  # 避免重复内容

        for query in queries:
            result_ids = self.importer.search(query, k=k)
            print(f"🔍 查询 '{query}' 得到 IDs: {result_ids}")  # 打印 ID 列表
            for cid in result_ids:
                if cid in seen_contents:
                    continue
                self.importer.db.cursor.execute("SELECT content FROM contents WHERE id = ?", (cid,))
                content = self.importer.db.cursor.fetchone()
                print(f"📄 查询 ID={cid} 的结果：{content}")  # 打印查询结果
                if content:
                    results.append(content[0])
                    seen_contents.add(cid)
        return results[:k]


@dataclass
class BookContent:
    book_id: int
    chapter: str
    section: str
    title: str
    content_type: str
    content: str
    parent_id: Optional[int] = None
    id: Optional[int] = None

class TensorFlowBookDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                chapter TEXT,
                section TEXT,
                title TEXT,
                content_type TEXT,
                content TEXT,
                parent_id INTEGER,
                FOREIGN KEY (book_id) REFERENCES books (id),
                FOREIGN KEY (parent_id) REFERENCES contents (id)
            )
        ''')
        self.conn.commit()

    def insert_book(self, title: str, description: str) -> int:
        self.cursor.execute(
            'INSERT INTO books (title, description) VALUES (?, ?)',
            (title, description)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_content(self, content: BookContent) -> int:
        self.cursor.execute(
            '''INSERT INTO contents 
               (book_id, chapter, section, title, content_type, content, parent_id) 
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (content.book_id, content.chapter, content.section, content.title,
             content.content_type, content.content, content.parent_id)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def close(self):
        if self.conn:
            self.conn.close()

class BookContentParser:
    def __init__(self):
        self.title_pattern = re.compile(r'^(#{1,6})\s+(.*?)(?:\n|$)')
        self.image_pattern = re.compile(r'!\[img\]\((.*?)\)')

    def parse_title_level(self, title_line: str) -> Tuple[int, str, str]:
        match = self.title_pattern.match(title_line)
        if not match:
            return 0, "", ""

        level = len(match.group(1))
        title_text = match.group(2).strip()

        section_match = re.match(r'^(\d+(?:\.\d+)*)\s+', title_text)
        section = section_match.group(1) if section_match else ""
        if section:
            title_text = title_text[len(section_match.group(0)):].strip()
        chapter = section.split('.')[0] if section else ""
        return level, section, title_text

    def split_content_blocks(self, content: str) -> List[Dict]:
        blocks, current_text = [], []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            level, section, title_text = self.parse_title_level(line)
            if level > 0:
                if current_text:
                    blocks.append({'type': 'text', 'content': '\n'.join(current_text).strip()})
                    current_text = []
                blocks.append({'type': 'title', 'level': level, 'chapter': section.split('.')[0] if section else "", 'section': section, 'content': title_text})
            else:
                current_text.append(line)
            i += 1

        if current_text:
            blocks.append({'type': 'text', 'content': '\n'.join(current_text).strip()})
        return blocks

    def build_hierarchy(self, blocks: List[Dict]) -> List[Dict]:
        hierarchy, stack = [], []
        for block in blocks:
            if block['type'] == 'title':
                while stack and stack[-1]['level'] >= block['level']:
                    stack.pop()
                block['parent'] = stack[-1] if stack else None
                stack.append(block)
            else:
                block['parent'] = stack[-1] if stack else None
            hierarchy.append(block)
        return hierarchy

class BookImporter:
    def __init__(self, db_path: str):
        self.db = TensorFlowBookDatabase(db_path)
        self.parser = BookContentParser()
        self.content_id_map = {}
        self.id_to_vector_index = {}
        self.faiss_index = None
        self._load_embedding_model()

    def _load_embedding_model(self):
        model_options = [
            {"name": "all-MiniLM-L6-v2", "local_path": "./local_models/all-MiniLM-L6-v2"},
            {"name": "bert-base-nli-mean-tokens", "local_path": "./local_models/bert-base-nli-mean-tokens"}
        ]
        for model_option in model_options:
            try:
                if os.path.exists(model_option["local_path"]):
                    self.embedding_model = SentenceTransformer(model_option["local_path"])
                else:
                    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com/'
                    self.embedding_model = SentenceTransformer(model_option["name"])
                print(f"模型加载成功: {model_option['name']}")
                return
            except Exception as e:
                print(f"加载模型失败: {e}")
        raise RuntimeError("所有模型加载失败")

    def import_book(self, book_title: str, book_description: str, content: str):
        book_id = self.db.insert_book(book_title, book_description)
        blocks = self.parser.split_content_blocks(content)
        hierarchy = self.parser.build_hierarchy(blocks)

        for block in hierarchy:
            parent_id = self.content_id_map.get(id(block['parent']), None)
            if block['type'] == 'title':
                content_obj = BookContent(book_id, block['chapter'], block['section'], block['content'], 'title', block['content'], parent_id)
            else:
                title = block['parent']['content'] if block['parent'] else ""
                chapter = block['parent']['chapter'] if block['parent'] else ""
                section = block['parent']['section'] if block['parent'] else ""
                content_obj = BookContent(book_id, chapter, section, title, 'text', block['content'], parent_id)

            content_id = self.db.insert_content(content_obj)
            self.content_id_map[id(block)] = content_id
        print(f"成功导入 {len(hierarchy)} 个内容块")

    def build_faiss_index(self):
        self.db.cursor.execute("SELECT id, content FROM contents")
        rows = self.db.cursor.fetchall()
        if not rows:
            print("数据库无内容，无法建立索引")
            return

        vectors = []
        self.id_to_vector_index = {}
        for idx, (content_id, content) in enumerate(rows):
            vector = self.embedding_model.encode(content)
            vectors.append(vector)
            self.id_to_vector_index[content_id] = idx

        dimension = len(vectors[0])
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(vectors))
        self.faiss_index = index


        print(f"Faiss索引建立完成，包含 {len(vectors)} 个向量")

    def search(self, query: str, k: int = 5):
        if self.faiss_index is None:
            raise RuntimeError("请先调用 build_faiss_index() 构建索引")
        query_embedding = self.embedding_model.encode(query)
        distances, indices = self.faiss_index.search(query_embedding.reshape(1, -1), k)
        result_ids = []
        for idx in indices[0]:
            for content_id, vector_index in self.id_to_vector_index.items():
                if vector_index == idx:
                    result_ids.append(content_id)
                    break
        return result_ids

    def close(self):
        self.db.close()

### 示例流程
if __name__ == "__main__":
    importer = BookImporter("faiss/tensorflow_books.db")
    try:
        """读取并导入第一本书
        with open(r"C:Users\h1352\Desktop\软件杯\《嵌入式Linux开发实践教程》示例资源-word版课件\《嵌入式Linux开发实践教程》示例资源-word版课件\7.txt", "r", encoding="utf-8") as f:
            content1 = f.read()
        importer.import_book("TensorFlow.js应用开发", "介绍 TensorFlow.js 开发", content1)

        # 读取并导入第二本书
        with open(r"C:Users\h1352\Desktop\软件杯\《嵌入式Linux开发实践教程》示例资源-word版课件\《嵌入式Linux开发实践教程》示例资源-word版课件\8.txt", "r", encoding="utf-8") as f:
            content2 = f.read()
        importer.import_book("TensorFlow Lite", "介绍 TensorFlow Lite 应用", content2)

        with open(r"C:Users\h1352\Desktop\软件杯\《嵌入式Linux开发实践教程》示例资源-word版课件\《嵌入式Linux开发实践教程》示例资源-word版课件\9.txt", "r", encoding="utf-8") as f:
            content3 = f.read()
        importer.import_book("嵌入式 Python 开发", "介绍 嵌入式 Python 开发", content3)"""

        # 构建 Faiss 索引
        importer.build_faiss_index()

        # 搜索示例
        query = "树莓派与 Jetson Nano 开发环境配置"
        results = importer.search(query)
        print("搜索结果ID:", results)
        for cid in results:
            importer.db.cursor.execute("SELECT content FROM contents WHERE id = ?", (cid,))
            content = importer.db.cursor.fetchone()
            if content:
                print(f"内容ID {cid}: {content[0]}")

    finally:
        importer.close()
