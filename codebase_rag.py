#!/usr/bin/env python3
"""
Sistema RAG para Code Review
Fornece contexto relevante da codebase durante o review
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

@dataclass
class RetrievalContext:
    """Contexto recuperado do RAG"""
    similar_files: List[Dict] = None
    related_functions: List[Dict] = None
    dependencies: Dict = None
    
    def __post_init__(self):
        if self.similar_files is None:
            self.similar_files = []
        if self.related_functions is None:
            self.related_functions = []
        if self.dependencies is None:
            self.dependencies = {}

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
        self.model = SentenceTransformer(model_name)
        
        print(f"💾 Initializing ChromaDB at {persist_directory}")
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Tentar carregar coleção existente
        try:
            self.collection = self.client.get_collection("codebase")
            count = self.collection.count()
            print(f"  ✅ Connected to existing collection with {count} items")
        except Exception as e:
            print(f"  ⚠️ Collection 'codebase' not found: {e}")
            print(f"  ℹ️ Creating new empty collection...")
            self.collection = self.client.create_collection("codebase")
            print(f"  ✅ Empty collection created")
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da base de dados"""
        try:
            count = self.collection.count()
            
            # Tentar obter metadados para contar ficheiros e funções
            if count > 0:
                results = self.collection.get(limit=count)
                metadatas = results['metadatas']
                
                files = set()
                functions = 0
                
                for meta in metadatas:
                    if meta.get('file'):
                        files.add(meta['file'])
                    if meta.get('type') in ['function', 'class']:
                        functions += 1
                
                return {
                    'total_items': count,
                    'total_files': len(files),
                    'total_functions': functions
                }
            
            return {
                'total_items': 0,
                'total_files': 0,
                'total_functions': 0
            }
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
            return {
                'total_items': 0,
                'total_files': 0,
                'total_functions': 0
            }
    
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
                n_results=min(top_k * 3, count)  # Pedir mais para filtrar depois
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
            # Pegar primeiras linhas do patch (sem headers do diff)
            patch_lines = [
                line for line in patch.split('\n')
                if not line.startswith(('@@', '---', '+++', 'diff'))
            ][:10]  # Primeiras 10 linhas
            
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
        
        # Agrupar por tipo
        files_data = []
        functions_data = []
        
        for i, (doc, meta, distance) in enumerate(zip(documents, metadatas, distances)):
            # Skip o próprio ficheiro
            if meta.get('file') == current_file:
                continue
            
            # Adicionar relevância (menor distância = mais relevante)
            item = {
                'content': doc,
                'path': meta.get('file', 'unknown'),
                'name': meta.get('name', 'unknown'),
                'type': meta.get('type', 'unknown'),
                'relevance': 1 - distance  # Converter distância para score de relevância
            }
            
            if meta.get('type') in ['function', 'class']:
                functions_data.append(item)
            else:
                files_data.append(item)
        
        # Ordenar por relevância e pegar top_k
        files_data.sort(key=lambda x: x['relevance'], reverse=True)
        functions_data.sort(key=lambda x: x['relevance'], reverse=True)
        
        context.similar_files = files_data[:top_k]
        context.related_functions = functions_data[:top_k]
        
        # Tentar inferir dependências simples
        context.dependencies = self._infer_dependencies(current_file)
        
        return context
    
    def _infer_dependencies(self, filepath: str) -> Dict:
        """
        Infere dependências básicas do ficheiro
        (implementação simplificada - pode ser melhorada)
        """
        dependencies = {
            'imports': [],
            'imported_by': []
        }
        
        try:
            # Buscar ficheiros que possam importar/ser importados
            # por este ficheiro (baseado no nome)
            filename = Path(filepath).stem
            
            results = self.collection.get(
                where={"name": {"$contains": filename}},
                limit=10
            )
            
            if results and results['metadatas']:
                for meta in results['metadatas']:
                    if meta.get('file') != filepath:
                        dependencies['imports'].append(meta.get('file', 'unknown'))
            
        except Exception as e:
            print(f"  ⚠️ Error inferring dependencies: {e}")
        
        return dependencies
    
    def search_similar_code(self, code_snippet: str, top_k: int = 5) -> List[Dict]:
        """
        Busca código similar ao snippet fornecido
        
        Args:
            code_snippet: Trecho de código para buscar
            top_k: Número de resultados
        
        Returns:
            Lista de resultados similares
        """
        try:
            count = self.collection.count()
            if count == 0:
                return []
            
            # Criar embedding
            embedding = self.model.encode(code_snippet).tolist()
            
            # Buscar
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, count)
            )
            
            # Formatar resultados
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
    
    def get_file_context(self, filepath: str) -> Optional[Dict]:
        """
        Obtém todo o contexto disponível para um ficheiro específico
        
        Args:
            filepath: Caminho do ficheiro
        
        Returns:
            Dict com todo o contexto do ficheiro ou None
        """
        try:
            results = self.collection.get(
                where={"file": filepath}
            )
            
            if not results or not results['documents']:
                return None
            
            return {
                'documents': results['documents'],
                'metadatas': results['metadatas'],
                'count': len(results['documents'])
            }
            
        except Exception as e:
            print(f"⚠️ Error getting file context: {e}")
            return None