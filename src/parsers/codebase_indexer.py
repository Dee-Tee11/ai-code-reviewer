#!/usr/bin/env python3
"""
Indexer para codebase completo ou incremental
"""

from pathlib import Path
from typing import Dict, List

from .file_indexer import FileIndexer


class CodebaseIndexer:
    """Indexa codebase completo ou incremental"""
    
    # Diretórios a ignorar
    IGNORE_DIRS = {
        'node_modules', 'dist', 'build', '.git', '__pycache__',
        '.next', '.nuxt', 'venv', 'env', '.venv', 'coverage',
        '.pytest_cache', '.mypy_cache', 'chroma_db'
    }
    
    # Ficheiros a ignorar
    IGNORE_FILES = {
        '.pyc', '.map', '.min.js', '.bundle.js', 
        'package-lock.json', 'yarn.lock', 'poetry.lock'
    }
    
    def __init__(self, repo_path: str, rag):
        self.repo_path = Path(repo_path).resolve()
        self.rag = rag
        self.file_indexer = FileIndexer(rag)
    
    def index_all(self) -> Dict:
        """
        Indexa codebase completo
        
        Returns:
            Estatísticas da indexação
        """
        print(f"🚀 Starting full indexation of: {self.repo_path}")
        
        files_found = []
        
        # Descobrir todos os ficheiros relevantes
        for ext in ['.py', '.ts', '.tsx', '.jsx', '.js']:
            files_found.extend(self.repo_path.rglob(f"*{ext}"))
        
        # Filtrar ficheiros
        files_to_index = [
            f for f in files_found 
            if self._should_index(f)
        ]
        
        print(f"📊 Found {len(files_to_index)} files to index")
        
        # Indexar cada ficheiro
        success_count = 0
        error_count = 0
        
        for filepath in files_to_index:
            try:
                if self.file_indexer.index_file(filepath, self.repo_path):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"❌ Unexpected error indexing {filepath}: {e}")
                error_count += 1
        
        # Estatísticas finais
        stats = {
            "total_files": len(files_to_index),
            "success": success_count,
            "errors": error_count,
            "rag_stats": self.rag.get_stats()
        }
        
        print(f"\n✅ Indexation complete!")
        print(f"  Success: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total indexed: {stats['rag_stats']['total_files']} files, {stats['rag_stats']['total_functions']} functions")
        
        return stats
    
    def index_files(self, filepaths: List[str]) -> Dict:
        """
        Indexa lista específica de ficheiros (incremental)
        
        Args:
            filepaths: Lista de caminhos relativos
            
        Returns:
            Estatísticas da indexação
        """
        print(f"🔄 Incremental indexation of {len(filepaths)} files")
        
        success_count = 0
        error_count = 0
        
        for filepath_str in filepaths:
            filepath = self.repo_path / filepath_str
            
            if not filepath.exists():
                print(f"⚠️ File not found: {filepath}")
                continue
            
            if not self._should_index(filepath):
                print(f"⏭️ Skipping: {filepath}")
                continue
            
            # Remover chunks antigos do ficheiro
            self.rag.delete_file_chunks(filepath_str)
            
            # Re-indexar
            try:
                if self.file_indexer.index_file(filepath, self.repo_path):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"❌ Error indexing {filepath}: {e}")
                error_count += 1
        
        stats = {
            "files_processed": len(filepaths),
            "success": success_count,
            "errors": error_count,
            "rag_stats": self.rag.get_stats()
        }
        
        print(f"\n✅ Incremental update complete!")
        print(f"  Success: {success_count}")
        print(f"  Errors: {error_count}")
        
        return stats
    
    def _should_index(self, filepath: Path) -> bool:
        """Verifica se deve indexar este ficheiro"""
        # Verificar diretórios ignorados
        for part in filepath.parts:
            if part in self.IGNORE_DIRS:
                return False
        
        # Verificar extensão ignorada
        if filepath.suffix in self.IGNORE_FILES:
            return False
        
        # Verificar se é ficheiro de teste (opcional - comentar se quiser indexar testes)
        # if 'test' in filepath.name.lower() or 'spec' in filepath.name.lower():
        #     return False
        
        return True