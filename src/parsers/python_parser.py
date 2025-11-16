#!/usr/bin/env python3
"""
Parser para ficheiros Python usando AST
"""

import ast
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

from codebase_rag import CodeChunk, generate_chunk_id


class PythonParser:
    """Parser para ficheiros Python usando AST"""
    
    @staticmethod
    def parse_file(filepath: Path, content: str) -> Tuple[List[CodeChunk], List[str], List[str]]:
        """
        Parseia ficheiro Python
        
        Returns:
            (chunks, imports, exports)
        """
        chunks = []
        imports = []
        exports = []
        
        try:
            tree = ast.parse(content)
            
            # Extrair imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Extrair funções e classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    chunk = PythonParser._create_function_chunk(
                        filepath, content, node, "function"
                    )
                    if chunk:
                        chunks.append(chunk)
                        # Se função tem __all__ ou é pública, adicionar a exports
                        if not node.name.startswith('_'):
                            exports.append(node.name)
                
                elif isinstance(node, ast.ClassDef):
                    chunk = PythonParser._create_function_chunk(
                        filepath, content, node, "class"
                    )
                    if chunk:
                        chunks.append(chunk)
                        if not node.name.startswith('_'):
                            exports.append(node.name)
            
            return chunks, imports, exports
            
        except SyntaxError as e:
            print(f"  ⚠️ Syntax error in {filepath}: {e}")
            return [], [], []
    
    @staticmethod
    def _create_function_chunk(filepath: Path, 
                               content: str, 
                               node: ast.AST,
                               chunk_type: str) -> Optional[CodeChunk]:
        """Cria chunk para uma função ou classe"""
        try:
            lines = content.split('\n')
            line_start = node.lineno
            line_end = node.end_lineno or line_start
            
            # Extrair código da função/classe
            func_code = '\n'.join(lines[line_start-1:line_end])
            
            # Gerar ID
            chunk_id = generate_chunk_id(
                "function",
                str(filepath),
                node.name,
                line_start
            )
            
            return CodeChunk(
                id=chunk_id,
                type=chunk_type,
                path=str(filepath),
                name=node.name,
                content=func_code,
                language="python",
                line_start=line_start,
                line_end=line_end,
                imports=[],
                exports=[],
                parent_file=f"file:{filepath}",
                last_modified=datetime.now().isoformat(),
                commit_sha=None
            )
            
        except Exception as e:
            print(f"  ⚠️ Error creating chunk: {e}")
            return None