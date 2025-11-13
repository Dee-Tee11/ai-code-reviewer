#!/usr/bin/env python3
"""
Sistema RAG completo para Code Review
Fornece contexto relevante da codebase durante o review
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


# ═══════════════════════════════════════════════════════════
# 📦 DATA CLASSES
# ═══════════════════════════════════════════════════════════

@dataclass
class CodeChunk:
    """Representa um chunk de código (ficheiro, função, classe)"""
    id: str
    type: str  # file, function, class, component
    path: str
    name: str
    content: str
    language: str
    line_start: int
    line_end: int
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    parent_file: Optional[str] = None
    last_modified: str = ""
    commit_sha: Optional[str] = None


@dataclass
class RetrievalContext:
    """Contexto recuperado do RAG"""
    similar_files: List[Dict] = field(default_factory=list)
    related_functions: List[Dict] = field(default_factory=list)
    dependencies: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# 🔧 UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════

def generate_chunk_id(chunk_type: str, filepath: str, name: str, line: int) -> str:
    """
    Gera ID único para um chunk
    
    Args:
        chunk_type: Tipo do chunk (file, function, class)
        filepath: Caminho do ficheiro
        name: Nome da função/classe
        line: Linha inicial
    
    Returns:
        ID único (hash MD5)
    """
    unique_str = f"{chunk_type}:{filepath}:{name}:{line}"
    return hashlib.md5(unique_str.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════
# 🧠 CODEBASE RAG
# ═══════════════════════════════════════════════════════════

class CodebaseRAG:
    """Sistema RAG para recuperar contexto da codebase"""
    
    def __init__(self, persist_directory: str = "./chroma_db", model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa o sistema RAG
        
        Args:
            persist_directory: Caminho para a base de dados ChromaDB
            model_name: Nome do modelo de embeddings
        """
        self.persist_directory = persist_directory
        self.model_name = model_name
        
        print(f"🧠 Loading embedding model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            raise
        
        print(f"💾 Initializing ChromaDB at {persist_directory}")
        
        # Criar diretório se não existir
        os.makedirs(persist_directory, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        except Exception as e:
            print(f"❌ Failed to initialize ChromaDB: {e}")
            raise
        
        # Tentar carregar coleção existente
        try:
            self.collection = self.client.get_collection("codebase")
            count = self.collection.count()
            print(f"  ✅ Connected to existing collection with {count} items")
        except Exception as e:
            print(f"  ℹ️ Collection 'codebase' not found, creating new...")
            try:
                self.collection = self.client.create_collection("codebase")
                print(f"  ✅ Empty collection created")
            except Exception as create_error:
                print(f"❌ Failed to create collection: {create_error}")
                raise
    
    # ═══════════════════════════════════════════════════════════
    # 📥 INDEXING METHODS
    # ═══════════════════════════════════════════════════════════
    
    def index_file(self, chunk: CodeChunk) -> bool:
        """
        Indexa um ficheiro completo
        
        Args:
            chunk: CodeChunk representando o ficheiro
        
        Returns:
            True se sucesso
        """
        try:
            # Criar documento para embedding
            doc = f"File: {chunk.name}\nPath: {chunk.path}\n{chunk.content}"
            
            # Criar embedding
            embedding = self.model.encode(doc).tolist()
            
            # Metadata
            metadata = {
                'type': chunk.type,
                'file': chunk.path,
                'name': chunk.name,
                'language': chunk.language,
                'line_start': chunk.line_start,
                'line_end': chunk.line_end,
                'imports': ','.join(chunk.imports),
                'exports': ','.join(chunk.exports),
                'last_modified': chunk.last_modified
            }
            
            # Adicionar à coleção
            self.collection.upsert(
                documents=[doc],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[chunk.id]
            )
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error indexing file {chunk.path}: {e}")
            return False
    
    def index_function(self, chunk: CodeChunk) -> bool:
        """
        Indexa uma função ou classe
        
        Args:
            chunk: CodeChunk representando a função/classe
        
        Returns:
            True se sucesso
        """
        try:
            # Criar documento para embedding
            doc = f"{chunk.type}: {chunk.name}\nFile: {chunk.path}\n{chunk.content}"
            
            # Criar embedding
            embedding = self.model.encode(doc).tolist()
            
            # Metadata
            metadata = {
                'type': chunk.type,
                'file': chunk.path,
                'name': chunk.name,
                'language': chunk.language,
                'line_start': chunk.line_start,
                'line_end': chunk.line_end,
                'parent_file': chunk.parent_file or '',
                'last_modified': chunk.last_modified
            }
            
            # Adicionar à coleção
            self.collection.upsert(
                documents=[doc],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[chunk.id]
            )
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error indexing function {chunk.name}: {e}")
            return False
    
    def update_dependencies(self, filepath: str, imports: List[str], exports: List[str]):
        """
        Atualiza as dependências de um ficheiro
        
        Args:
            filepath: Caminho do ficheiro
            imports: Lista de imports
            exports: Lista de exports
        """
        try:
            # Buscar o ficheiro na coleção
            results = self.collection.get(
                where={"file": filepath, "type": "file"}
            )
            
            if results and results['ids']:
                file_id = results['ids'][0]
                
                # Atualizar metadata
                self.collection.update(
                    ids=[file_id],
                    metadatas=[{
                        'imports': ','.join(imports),
                        'exports': ','.join(exports)
                    }]
                )
                
        except Exception as e:
            print(f"  ⚠️ Error updating dependencies for {filepath}: {e}")
    
    def delete_file_chunks(self, filepath: str):
        """
        Remove todos os chunks de um ficheiro
        
        Args:
            filepath: Caminho do ficheiro
        """
        try:
            results = self.collection.get(
                where={"file": filepath}
            )
            
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"  🗑️ Deleted {len(results['ids'])} chunks from {filepath}")
                
        except Exception as e:
            print(f"  ⚠️ Error deleting chunks for {filepath}: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # 🔍 RETRIEVAL METHODS
    # ═══════════════════════════════════════════════════════════
    
    def get_context(
        self, 
        filepath: str, 
        patch: Optional[str] = None, 
        top_k: int = 3
    ) -> RetrievalContext:
        """
        Recupera contexto relevante para um ficheiro
        
        Args:
            filepath: Caminho do ficheiro a ser reviewado
            patch: Diff/patch do ficheiro (opcional)
            top_k: Número de resultados a retornar por categoria
        
        Returns:
            RetrievalContext com informação relevante
        """
        context = RetrievalContext()
        
        try:
            # Verificar se a coleção está vazia
            count = self.collection.count()
            if count == 0:
                print(f"  ⚠️ RAG database is empty")
                return context
            
            # 1. Criar query baseada no filepath e patch
            query_text = self._build_query(filepath, patch)
            
            # 2. Criar embedding da query
            query_embedding = self.model.encode(query_text).tolist()
            
            # 3. Buscar itens similares
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k * 3, count)
            )
            
            # 4. Processar resultados
            if results and results['documents']:
                context = self._process_results(results, filepath, top_k)
            
            return context
            
        except Exception as e:
            print(f"  ⚠️ Error retrieving context: {e}")
            return context
    
    def _build_query(self, filepath: str, patch: Optional[str]) -> str:
        """Constrói a query para buscar contexto"""
        query_parts = [f"file: {filepath}"]
        
        # Adicionar extensão do ficheiro
        ext = Path(filepath).suffix
        query_parts.append(f"extension: {ext}")
        
        # Adicionar partes do patch se disponível
        if patch:
            patch_lines = [
                line for line in patch.split('\n')
                if not line.startswith(('@@', '---', '+++', 'diff'))
            ][:10]
            
            if patch_lines:
                query_parts.append("code: " + " ".join(patch_lines))
        
        return "\n".join(query_parts)
    
    def _process_results(
        self, 
        results: Dict, 
        current_file: str, 
        top_k: int
    ) -> RetrievalContext:
        """Processa os resultados da query"""
        context = RetrievalContext()
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        files_data = []
        functions_data = []
        
        for doc, meta, distance in zip(documents, metadatas, distances):
            if meta.get('file') == current_file:
                continue
            
            item = {
                'content': doc,
                'path': meta.get('file', 'unknown'),
                'name': meta.get('name', 'unknown'),
                'type': meta.get('type', 'unknown'),
                'relevance': 1 - distance
            }
            
            if meta.get('type') in ['function', 'class', 'component']:
                functions_data.append(item)
            else:
                files_data.append(item)
        
        files_data.sort(key=lambda x: x['relevance'], reverse=True)
        functions_data.sort(key=lambda x: x['relevance'], reverse=True)
        
        context.similar_files = files_data[:top_k]
        context.related_functions = functions_data[:top_k]
        context.dependencies = self._infer_dependencies(current_file)
        
        return context
    
    def _infer_dependencies(self, filepath: str) -> Dict:
        """Infere dependências básicas do ficheiro"""
        dependencies = {
            'imports': [],
            'imported_by': []
        }
        
        try:
            filename = Path(filepath).stem
            
            results = self.collection.get(
                where={"file": filepath, "type": "file"}
            )
            
            if results and results['metadatas']:
                for meta in results['metadatas']:
                    imports_str = meta.get('imports', '')
                    exports_str = meta.get('exports', '')
                    
                    if imports_str:
                        dependencies['imports'] = imports_str.split(',')
                    if exports_str:
                        dependencies['imported_by'] = exports_str.split(',')
            
        except Exception as e:
            print(f"  ⚠️ Error inferring dependencies: {e}")
        
        return dependencies
    
    # ═══════════════════════════════════════════════════════════
    # 📊 UTILITY METHODS
    # ═══════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da base de dados"""
        try:
            count = self.collection.count()
            
            if count > 0:
                results = self.collection.get(limit=count)
                metadatas = results['metadatas']
                
                files = set()
                functions = 0
                dependencies_count = 0
                
                for meta in metadatas:
                    if meta.get('file'):
                        files.add(meta['file'])
                    if meta.get('type') in ['function', 'class', 'component']:
                        functions += 1
                    
                    # Contar imports e exports como dependências
                    imports = meta.get('imports', '')
                    exports = meta.get('exports', '')
                    if imports:
                        dependencies_count += len(imports.split(','))
                    if exports:
                        dependencies_count += len(exports.split(','))
                
                return {
                    'total_items': count,
                    'total_files': len(files),
                    'total_functions': functions,
                    'total_dependencies': dependencies_count  # ✅ ADICIONADO!
                }
            
            return {
                'total_items': 0,
                'total_files': 0,
                'total_functions': 0,
                'total_dependencies': 0  # ✅ ADICIONADO!
            }
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
            return {
                'total_items': 0,
                'total_files': 0,
                'total_functions': 0,
                'total_dependencies': 0  # ✅ ADICIONADO!
            }
    
    def reset(self):
        """Remove toda a coleção e recria vazia"""
        try:
            self.client.delete_collection("codebase")
            print("  🗑️ Collection deleted")
        except:
            pass
    
    def search_similar_code(self, code_snippet: str, top_k: int = 5) -> List[Dict]:
        """Busca código similar ao snippet fornecido"""
        try:
            count = self.collection.count()
            if count == 0:
                return []
            
            embedding = self.model.encode(code_snippet).tolist()
            
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, count)
            )
            
            similar_items = []
            if results and results['documents']:
                for doc, meta, dist in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                ):
                    similar_items.append({
                        'content': doc,
                        'file': meta.get('file', 'unknown'),
                        'name': meta.get('name', 'unknown'),
                        'type': meta.get('type', 'unknown'),
                        'similarity': 1 - dist
                    })
            
            return similar_items
            
        except Exception as e:
            print(f"⚠️ Error searching similar code: {e}")
            return []