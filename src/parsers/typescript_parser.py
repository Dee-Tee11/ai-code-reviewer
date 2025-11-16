#!/usr/bin/env python3
"""
Parser para ficheiros TypeScript e TSX usando regex
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

from codebase_rag import CodeChunk, generate_chunk_id


class TypeScriptParser:
    """Parser para ficheiros TypeScript e TSX usando regex"""
    
    # Patterns regex
    IMPORT_PATTERN = r"import\s+(?:(?:\*\s+as\s+\w+)|(?:\{[^}]+\})|(?:\w+))\s+from\s+['\"]([^'\"]+)['\"]"
    EXPORT_PATTERN = r"export\s+(?:default\s+)?(?:function|const|class|interface|type)\s+(\w+)"
    FUNCTION_PATTERN = r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{"
    CONST_FUNCTION_PATTERN = r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=]+)\s*=>\s*"
    COMPONENT_PATTERN = r"(?:export\s+)?(?:const|function)\s+([A-Z]\w+)\s*[=:]"
    CLASS_PATTERN = r"(?:export\s+)?class\s+(\w+)"
    
    @staticmethod
    def parse_file(filepath: Path, content: str) -> Tuple[List[CodeChunk], List[str], List[str]]:
        """
        Parseia ficheiro TypeScript/TSX
        
        Returns:
            (chunks, imports, exports)
        """
        chunks = []
        imports = []
        exports = []
        
        # Extrair imports
        import_matches = re.finditer(TypeScriptParser.IMPORT_PATTERN, content)
        for match in import_matches:
            import_path = match.group(1)
            imports.append(import_path)
        
        # Extrair exports
        export_matches = re.finditer(TypeScriptParser.EXPORT_PATTERN, content)
        for match in export_matches:
            export_name = match.group(1)
            exports.append(export_name)
        
        # Extrair funções, componentes e classes
        lines = content.split('\n')
        
        # 1. Funções normais
        for match in re.finditer(TypeScriptParser.FUNCTION_PATTERN, content):
            chunk = TypeScriptParser._create_chunk_from_match(
                filepath, content, lines, match, "function"
            )
            if chunk:
                chunks.append(chunk)
        
        # 2. Arrow functions (const)
        for match in re.finditer(TypeScriptParser.CONST_FUNCTION_PATTERN, content):
            chunk = TypeScriptParser._create_chunk_from_match(
                filepath, content, lines, match, "function"
            )
            if chunk:
                chunks.append(chunk)
        
        # 3. React Components
        for match in re.finditer(TypeScriptParser.COMPONENT_PATTERN, content):
            chunk = TypeScriptParser._create_chunk_from_match(
                filepath, content, lines, match, "component"
            )
            if chunk:
                chunks.append(chunk)
        
        # 4. Classes
        for match in re.finditer(TypeScriptParser.CLASS_PATTERN, content):
            chunk = TypeScriptParser._create_chunk_from_match(
                filepath, content, lines, match, "class"
            )
            if chunk:
                chunks.append(chunk)
        
        return chunks, imports, exports
    
    @staticmethod
    def _create_chunk_from_match(filepath: Path,
                                 content: str,
                                 lines: List[str],
                                 match: re.Match,
                                 chunk_type: str) -> Optional[CodeChunk]:
        """Cria chunk a partir de um regex match"""
        try:
            name = match.group(1)
            start_pos = match.start()
            
            # Encontrar linha inicial
            line_start = content[:start_pos].count('\n') + 1
            
            # Encontrar linha final (procurar pelo closing bracket)
            line_end = TypeScriptParser._find_closing_bracket(
                lines, line_start - 1, content[start_pos:]
            )
            
            # Extrair código
            func_code = '\n'.join(lines[line_start-1:line_end])
            
            # Limitar tamanho (max 100 linhas por chunk)
            if line_end - line_start > 100:
                line_end = line_start + 100
                func_code = '\n'.join(lines[line_start-1:line_end]) + "\n// ... (truncated)"
            
            # Gerar ID
            chunk_id = generate_chunk_id(
                "function",
                str(filepath),
                name,
                line_start
            )
            
            return CodeChunk(
                id=chunk_id,
                type=chunk_type,
                path=str(filepath),
                name=name,
                content=func_code,
                language="typescript",
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
    
    @staticmethod
    def _find_closing_bracket(lines: List[str], 
                             start_line: int, 
                             remaining_content: str) -> int:
        """Encontra a linha do closing bracket"""
        bracket_count = 0
        in_function = False
        
        for i, line in enumerate(lines[start_line:], start=start_line):
            for char in line:
                if char == '{':
                    bracket_count += 1
                    in_function = True
                elif char == '}':
                    bracket_count -= 1
                    if in_function and bracket_count == 0:
                        return i + 1
        
        # Se não encontrar, retornar +30 linhas (default)
        return start_line + 30