#!/usr/bin/env python3
"""
Data models para o sistema RAG
"""

import hashlib
from typing import List, Optional, Dict
from dataclasses import dataclass, field


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
    
    def has_context(self) -> bool:
        """Verifica se existe contexto relevante"""
        return (
            len(self.similar_files) > 0 or 
            len(self.related_functions) > 0 or
            bool(self.dependencies.get('imports')) or
            bool(self.dependencies.get('imported_by'))
        )


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