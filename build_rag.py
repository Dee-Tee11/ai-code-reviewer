#!/usr/bin/env python3
"""
Script para construir a base de dados RAG (ChromaDB) a partir do código do repositório.
"""

import os
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import ast
import hashlib

class CodeExtractor:
    """Extrai funções e classes de arquivos Python."""
    
    @staticmethod
    def extract_functions(file_path):
        """Extrai funções de um arquivo Python."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    # Pega o código da função
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    func_code = '\n'.join(content.split('\n')[start_line:end_line])
                    
                    # Pega o docstring se existir
                    docstring = ast.get_docstring(node) or ""
                    
                    functions.append({
                        'name': func_name,
                        'code': func_code,
                        'docstring': docstring,
                        'file': str(file_path),
                        'type': 'function'
                    })
                
                elif isinstance(node, ast.ClassDef):
                    class_name = node.name
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    class_code = '\n'.join(content.split('\n')[start_line:end_line])
                    
                    docstring = ast.get_docstring(node) or ""
                    
                    functions.append({
                        'name': class_name,
                        'code': class_code,
                        'docstring': docstring,
                        'file': str(file_path),
                        'type': 'class'
                    })
            
            return functions
        except Exception as e:
            print(f"⚠️ Error parsing {file_path}: {e}")
            return []

class RAGBuilder:
    """Constrói a base de dados RAG."""
    
    def __init__(self, db_path='./chroma_db', model_name='all-MiniLM-L6-v2'):
        self.db_path = db_path
        self.model_name = model_name
        print(f"🧠 Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        print(f"💾 Initializing ChromaDB at {db_path}")
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Cria ou pega a coleção
        try:
            self.collection = self.client.get_collection("codebase")
            print("📚 Using existing collection")
        except:
            self.collection = self.client.create_collection("codebase")
            print("📚 Created new collection")
    
    def scan_repository(self, repo_path='.', extensions=['.py', '.js', '.ts', '.java', '.go']):
        """Escaneia o repositório e indexa o código."""
        print(f"🔍 Scanning repository: {repo_path}")
        
        repo_path = Path(repo_path)
        all_items = []
        
        # Procura por arquivos de código
        for ext in extensions:
            files = list(repo_path.rglob(f'*{ext}'))
            print(f"  Found {len(files)} {ext} files")
            
            for file_path in files:
                # Ignora diretórios comuns
                if any(skip in str(file_path) for skip in ['.git', 'node_modules', '__pycache__', 'venv', '.venv']):
                    continue
                
                if ext == '.py':
                    items = CodeExtractor.extract_functions(file_path)
                    all_items.extend(items)
                else:
                    # Para outras linguagens, indexa o arquivo completo
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        all_items.append({
                            'name': file_path.name,
                            'code': content,
                            'docstring': '',
                            'file': str(file_path),
                            'type': 'file'
                        })
                    except Exception as e:
                        print(f"⚠️ Error reading {file_path}: {e}")
        
        print(f"📊 Total items extracted: {len(all_items)}")
        return all_items
    
    def index_items(self, items):
        """Indexa os itens na ChromaDB."""
        if not items:
            print("⚠️ No items to index")
            return
        
        print(f"🔨 Indexing {len(items)} items...")
        
        # Prepara dados para indexação
        documents = []
        metadatas = []
        ids = []
        
        for item in items:
            # Cria o documento para embedding
            doc = f"{item['name']}\n{item['docstring']}\n{item['code']}"
            documents.append(doc)
            
            # Metadata
            metadatas.append({
                'name': item['name'],
                'file': item['file'],
                'type': item['type'],
                'docstring': item['docstring'][:500]  # Limita tamanho
            })
            
            # ID único baseado no hash do conteúdo
            item_id = hashlib.md5(doc.encode()).hexdigest()
            ids.append(item_id)
        
        # Cria embeddings
        print("🧮 Creating embeddings...")
        embeddings = self.model.encode(documents, show_progress_bar=True)
        
        # Adiciona à coleção em lotes
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            end_idx = min(i + batch_size, len(documents))
            
            self.collection.upsert(
                documents=documents[i:end_idx],
                embeddings=embeddings[i:end_idx].tolist(),
                metadatas=metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )
            
            print(f"  ✅ Indexed {end_idx}/{len(documents)} items")
        
        print(f"✅ RAG database built successfully!")
        print(f"   - Total items: {len(items)}")
        print(f"   - Database path: {self.db_path}")

def main():
    """Função principal."""
    print("=" * 60)
    print("🚀 RAG Database Builder")
    print("=" * 60)
    
    # Pega o workspace do GitHub Actions ou diretório atual
    workspace = os.getenv('GITHUB_WORKSPACE', '.')
    db_path = os.getenv('RAG_DB_PATH', './chroma_db')
    
    print(f"📂 Workspace: {workspace}")
    print(f"💾 Database path: {db_path}")
    print()
    
    # Inicializa o builder
    builder = RAGBuilder(db_path=db_path)
    
    # Escaneia o repositório
    items = builder.scan_repository(workspace)
    
    # Indexa os itens
    builder.index_items(items)
    
    print()
    print("=" * 60)
    print("✅ RAG database ready to use!")
    print("=" * 60)

if __name__ == '__main__':
    main()