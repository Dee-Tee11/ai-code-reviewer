#!/usr/bin/env python3
"""
Context retrieval layer
"""

from typing import Dict, List, Optional
from pathlib import Path

from .models import RetrievalContext


class ContextRetriever:
    """Recupera contexto relevante da codebase"""
    
    def __init__(self, storage):
        """
        Args:
            storage: ChromaStorage instance
        """
        self.storage = storage
    
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
            count = self.storage.count()
            if count == 0:
                print(f"  ⚠️ RAG database is empty")
                return context
            
            # 1. Criar query baseada no filepath e patch
            query_text = self._build_query(filepath, patch)
            
            # 2. Criar embedding da query
            query_embedding = self.storage.encode(query_text)
            
            # 3. Buscar itens similares
            results = self.storage.query(
                query_embedding=query_embedding,
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
            
            results = self.storage.get(
                where={
                    "$and": [
                        {"file": {"$eq": filepath}},
                        {"type": {"$eq": "file"}}
                    ]
                }
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
    
    def search_similar_code(self, code_snippet: str, top_k: int = 5) -> List[Dict]:
        """Busca código similar ao snippet fornecido"""
        try:
            count = self.storage.count()
            if count == 0:
                return []
            
            embedding = self.storage.encode(code_snippet)
            
            results = self.storage.query(
                query_embedding=embedding,
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