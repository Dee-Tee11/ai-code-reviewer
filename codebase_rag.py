#!/usr/bin/env python3
"""
Sistema RAG completo para Code Review - Entry Point
Fornece contexto relevante da codebase durante o review

A lógica está modularizada em src/rag/
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Adicionar src/ ao Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag.models import CodeChunk, RetrievalContext, generate_chunk_id
from src.rag.storage import ChromaStorage
from src.rag.retriever import ContextRetriever


class CodebaseRAG:
    """Sistema RAG para recuperar contexto da codebase"""
    
    def __init__(self, persist_directory: str = "./chroma_db", model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa o sistema RAG
        
        Args:
            persist_directory: Caminho para a base de dados ChromaDB
            model_name: Nome do modelo de embeddings
        """
        # Inicializar storage
        self.storage = ChromaStorage(persist_directory, model_name)
        
        # Inicializar retriever
        self.retriever = ContextRetriever(self.storage)
    
    # ═══════════════════════════════════════════════════════════
    # INDEXING METHODS (delegados ao storage)
    # ═══════════════════════════════════════════════════════════
    
    def index_file(self, chunk: CodeChunk) -> bool:
        """Indexa um ficheiro completo"""
        return self.storage.index_file(chunk)
    
    def index_function(self, chunk: CodeChunk) -> bool:
        """Indexa uma função ou classe"""
        return self.storage.index_function(chunk)
    
    def update_dependencies(self, filepath: str, imports: List[str], exports: List[str]):
        """Atualiza as dependências de um ficheiro"""
        self.storage.update_dependencies(filepath, imports, exports)
    
    def delete_file_chunks(self, filepath: str):
        """Remove todos os chunks de um ficheiro"""
        self.storage.delete_file_chunks(filepath)
    
    # ═══════════════════════════════════════════════════════════
    # RETRIEVAL METHODS (delegados ao retriever)
    # ═══════════════════════════════════════════════════════════
    
    def get_context(
        self, 
        filepath: str, 
        patch: Optional[str] = None, 
        top_k: int = 3
    ) -> RetrievalContext:
        """Recupera contexto relevante para um ficheiro"""
        return self.retriever.get_context(filepath, patch, top_k)
    
    def search_similar_code(self, code_snippet: str, top_k: int = 5) -> List[Dict]:
        """Busca código similar ao snippet fornecido"""
        return self.retriever.search_similar_code(code_snippet, top_k)
    
    # ═══════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da base de dados"""
        return self.storage.get_stats()
    
    def reset(self):
        """Remove toda a coleção e recria vazia"""
        self.storage.reset()


# Export public API
__all__ = [
    'CodebaseRAG',
    'CodeChunk',
    'RetrievalContext',
    'generate_chunk_id'
]