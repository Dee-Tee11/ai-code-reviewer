"""
Sistema RAG para AI Code Reviewer
Indexa codebase e fornece contexto relevante para reviews
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


# ═══════════════════════════════════════════════════════════
# 📊 DATA CLASSES
# ═══════════════════════════════════════════════════════════

@dataclass
class CodeChunk:
    """Representa um pedaço de código indexado"""
    id: str
    type: str  # "file", "function", "class", "component"
    path: str
    name: str
    content: str
    language: str
    line_start: int
    line_end: int
    imports: List[str]
    exports: List[str]
    parent_file: Optional[str]
    last_modified: str
    commit_sha: Optional[str]

@dataclass
class RetrievalContext:
    """Contexto recuperado do RAG"""
    similar_files: List[Dict]  # Ficheiros semanticamente similares
    related_functions: List[Dict]  # Funções/componentes relacionados
    dependencies: Dict[str, List[str]]  # Grafo de dependências
    architecture_docs: List[Dict]  # Documentação relevante


# ═══════════════════════════════════════════════════════════
# 🧠 CODEBASE RAG
# ═══════════════════════════════════════════════════════════

class CodebaseRAG:
    """Sistema RAG para indexação e retrieval de código"""
    
    def __init__(self, 
                 persist_directory: str = "./chroma_db",
                 model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa o sistema RAG
        
        Args:
            persist_directory: Diretório para persistir ChromaDB
            model_name: Nome do modelo de embeddings
        """
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(exist_ok=True)
        
        # Inicializar modelo de embeddings
        print(f"🧠 Loading embedding model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        
        # Inicializar ChromaDB
        print(f"💾 Initializing ChromaDB at {persist_directory}")
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Criar/obter coleções
        self.files_collection = self.client.get_or_create_collection(
            name="files",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.functions_collection = self.client.get_or_create_collection(
            name="functions",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Grafo de dependências (armazenado localmente)
        self.dependency_graph_path = self.persist_dir / "dependencies.json"
        self.dependency_graph = self._load_dependency_graph()
    
    # ═══════════════════════════════════════════════════════
    # 📥 INDEXAÇÃO
    # ═══════════════════════════════════════════════════════
    
    def index_file(self, chunk: CodeChunk) -> bool:
        """
        Indexa um ficheiro completo (Nível 1)
        
        Args:
            chunk: CodeChunk com informação do ficheiro
            
        Returns:
            True se indexado com sucesso
        """
        try:
            # Gerar embedding
            embedding = self.embedding_model.encode(chunk.content).tolist()
            
            # Adicionar à coleção de ficheiros
            self.files_collection.add(
                ids=[chunk.id],
                embeddings=[embedding],
                documents=[chunk.content],
                metadatas=[{
                    "type": chunk.type,
                    "path": chunk.path,
                    "name": chunk.name,
                    "language": chunk.language,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "imports": json.dumps(chunk.imports),
                    "exports": json.dumps(chunk.exports),
                    "last_modified": chunk.last_modified,
                    "commit_sha": chunk.commit_sha or ""
                }]
            )
            
            print(f"  ✅ Indexed file: {chunk.path}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error indexing {chunk.path}: {e}")
            return False
    
    def index_function(self, chunk: CodeChunk) -> bool:
        """
        Indexa uma função/componente (Nível 2)
        
        Args:
            chunk: CodeChunk com informação da função
            
        Returns:
            True se indexado com sucesso
        """
        try:
            # Gerar embedding
            embedding = self.embedding_model.encode(chunk.content).tolist()
            
            # Adicionar à coleção de funções
            self.functions_collection.add(
                ids=[chunk.id],
                embeddings=[embedding],
                documents=[chunk.content],
                metadatas=[{
                    "type": chunk.type,
                    "path": chunk.path,
                    "name": chunk.name,
                    "language": chunk.language,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "parent_file": chunk.parent_file or "",
                    "last_modified": chunk.last_modified,
                    "commit_sha": chunk.commit_sha or ""
                }]
            )
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error indexing function {chunk.name}: {e}")
            return False
    
    def update_dependencies(self, filepath: str, imports: List[str], exports: List[str]):
        """
        Atualiza o grafo de dependências (Nível 3)
        
        Args:
            filepath: Caminho do ficheiro
            imports: Lista de imports
            exports: Lista de exports
        """
        # Adicionar/atualizar nó no grafo
        self.dependency_graph[filepath] = {
            "imports": imports,
            "exports": exports,
            "imported_by": []
        }
        
        # Atualizar imported_by nos ficheiros que este importa
        for imported_file in imports:
            if imported_file in self.dependency_graph:
                if filepath not in self.dependency_graph[imported_file]["imported_by"]:
                    self.dependency_graph[imported_file]["imported_by"].append(filepath)
        
        # Salvar grafo
        self._save_dependency_graph()
    
    def delete_file_chunks(self, filepath: str):
        """
        Remove todos os chunks de um ficheiro
        (útil para re-indexação)
        
        Args:
            filepath: Caminho do ficheiro a remover
        """
        file_id = f"file:{filepath}"
        
        try:
            # Remover ficheiro
            self.files_collection.delete(ids=[file_id])
            
            # Remover funções desse ficheiro
            results = self.functions_collection.get(
                where={"parent_file": file_id}
            )
            
            if results['ids']:
                self.functions_collection.delete(ids=results['ids'])
            
            # Remover do grafo de dependências
            if filepath in self.dependency_graph:
                del self.dependency_graph[filepath]
                self._save_dependency_graph()
            
            print(f"  🗑️ Deleted chunks for: {filepath}")
            
        except Exception as e:
            print(f"  ⚠️ Error deleting {filepath}: {e}")
    
    # ═══════════════════════════════════════════════════════
    # 🔍 RETRIEVAL
    # ═══════════════════════════════════════════════════════
    
    def get_context(self, 
                    filepath: str, 
                    patch: Optional[str] = None,
                    top_k: int = 5) -> RetrievalContext:
        """
        Obtém contexto relevante para um ficheiro modificado
        
        Args:
            filepath: Caminho do ficheiro modificado
            patch: Diff do commit (opcional)
            top_k: Número de resultados a retornar por categoria
            
        Returns:
            RetrievalContext com contexto relevante
        """
        print(f"🔍 Retrieving context for: {filepath}")
        
        # 1. Buscar ficheiros similares (Nível 1)
        similar_files = self._search_similar_files(filepath, patch, top_k)
        
        # 2. Buscar funções relacionadas (Nível 2)
        related_functions = self._search_related_functions(filepath, patch, top_k)
        
        # 3. Buscar dependências (Nível 3)
        dependencies = self._get_dependencies(filepath)
        
        # 4. Buscar documentação relevante
        architecture_docs = self._search_architecture_docs(filepath, top_k=2)
        
        context = RetrievalContext(
            similar_files=similar_files,
            related_functions=related_functions,
            dependencies=dependencies,
            architecture_docs=architecture_docs
        )
        
        return context
    
    def _search_similar_files(self, 
                              filepath: str, 
                              patch: Optional[str],
                              top_k: int) -> List[Dict]:
        """Busca ficheiros semanticamente similares"""
        try:
            # Usar patch se disponível, senão buscar ficheiro atual
            query_text = patch if patch else self._get_file_content(filepath)
            
            if not query_text:
                return []
            
            # Gerar embedding da query
            query_embedding = self.embedding_model.encode(query_text).tolist()
            
            # Buscar similares
            results = self.files_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k + 1  # +1 porque pode incluir o próprio ficheiro
            )
            
            # Filtrar o próprio ficheiro e formatar resultados
            similar = []
            for i, doc_id in enumerate(results['ids'][0]):
                if doc_id != f"file:{filepath}":
                    similar.append({
                        "id": doc_id,
                        "path": results['metadatas'][0][i]['path'],
                        "content": results['documents'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })
            
            return similar[:top_k]
            
        except Exception as e:
            print(f"  ⚠️ Error searching similar files: {e}")
            return []
    
    def _search_related_functions(self,
                                  filepath: str,
                                  patch: Optional[str],
                                  top_k: int) -> List[Dict]:
        """Busca funções/componentes relacionados"""
        try:
            query_text = patch if patch else self._get_file_content(filepath)
            
            if not query_text:
                return []
            
            # Gerar embedding
            query_embedding = self.embedding_model.encode(query_text).tolist()
            
            # Buscar funções similares
            results = self.functions_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Formatar resultados
            functions = []
            for i, doc_id in enumerate(results['ids'][0]):
                functions.append({
                    "id": doc_id,
                    "name": results['metadatas'][0][i]['name'],
                    "path": results['metadatas'][0][i]['path'],
                    "content": results['documents'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
            
            return functions
            
        except Exception as e:
            print(f"  ⚠️ Error searching related functions: {e}")
            return []
    
    def _get_dependencies(self, filepath: str) -> Dict[str, List[str]]:
        """Obtém dependências diretas do ficheiro"""
        if filepath not in self.dependency_graph:
            return {"imports": [], "imported_by": []}
        
        node = self.dependency_graph[filepath]
        return {
            "imports": node.get("imports", []),
            "imported_by": node.get("imported_by", [])
        }
    
    def _search_architecture_docs(self, filepath: str, top_k: int) -> List[Dict]:
        """Busca documentação de arquitetura relevante"""
        # TODO: Implementar busca em READMEs, docs, etc.
        # Por agora retorna vazio
        return []
    
    def _get_file_content(self, filepath: str) -> Optional[str]:
        """Obtém conteúdo de um ficheiro do índice"""
        try:
            file_id = f"file:{filepath}"
            result = self.files_collection.get(ids=[file_id])
            
            if result['documents']:
                return result['documents'][0]
            return None
            
        except:
            return None
    
    # ═══════════════════════════════════════════════════════
    # 💾 PERSISTENCE
    # ═══════════════════════════════════════════════════════
    
    def _load_dependency_graph(self) -> Dict:
        """Carrega grafo de dependências do disco"""
        if self.dependency_graph_path.exists():
            try:
                with open(self.dependency_graph_path) as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_dependency_graph(self):
        """Salva grafo de dependências no disco"""
        try:
            with open(self.dependency_graph_path, 'w') as f:
                json.dump(self.dependency_graph, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving dependency graph: {e}")
    
    # ═══════════════════════════════════════════════════════
    # 📊 STATS & UTILITIES
    # ═══════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do índice"""
        files_count = self.files_collection.count()
        functions_count = self.functions_collection.count()
        dependencies_count = len(self.dependency_graph)
        
        return {
            "total_files": files_count,
            "total_functions": functions_count,
            "total_dependencies": dependencies_count,
            "storage_path": str(self.persist_dir)
        }
    
    def reset(self):
        """Reset completo do índice (cuidado!)"""
        self.client.reset()
        self.dependency_graph = {}
        self._save_dependency_graph()
        print("🗑️ Index reset complete")


# ═══════════════════════════════════════════════════════════
# 🔧 HELPER: Gerar ID único
# ═══════════════════════════════════════════════════════════

def generate_chunk_id(type: str, path: str, name: str, line_start: int) -> str:
    """
    Gera ID único para um chunk
    
    Args:
        type: "file" ou "function"
        path: Caminho do ficheiro
        name: Nome da função/componente
        line_start: Linha inicial
        
    Returns:
        ID único no formato: "type:path:name:line"
    """
    if type == "file":
        return f"file:{path}"
    else:
        return f"func:{path}:{name}:{line_start}"