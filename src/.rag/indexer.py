#!/usr/bin/env python3
"""
Indexer - Parseia e indexa codebase do CinemaWebApp
Suporta Python, TypeScript, TSX, JSX
"""

#!/usr/bin/env python3
"""
Indexer - Parseia e indexa codebase do CinemaWebApp
Suporta Python, TypeScript, TSX, JSX
"""

# Fix Windows encoding for emojis
import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import argparse

# Importar o sistema RAG
from codebase_rag import CodebaseRAG, CodeChunk, generate_chunk_id

# ═══════════════════════════════════════════════════════════
# 🐍 PYTHON PARSER
# ═══════════════════════════════════════════════════════════

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
            
            func_code = '\n'.join(lines[line_start-1:line_end])
            
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


# ═══════════════════════════════════════════════════════════
# 📘 TYPESCRIPT/TSX PARSER
# ═══════════════════════════════════════════════════════════

class TypeScriptParser:
    """Parser para ficheiros TypeScript e TSX usando regex"""
    
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
            imports.append(match.group(1))
        
        # Extrair exports
        export_matches = re.finditer(TypeScriptParser.EXPORT_PATTERN, content)
        for match in export_matches:
            exports.append(match.group(1))
        
        lines = content.split('\n')
        
        # Extrair funções, componentes e classes
        for match in re.finditer(TypeScriptParser.FUNCTION_PATTERN, content):
            chunk = TypeScriptParser._create_chunk_from_match(
                filepath, content, lines, match, "function"
            )
            if chunk:
                chunks.append(chunk)
        
        for match in re.finditer(TypeScriptParser.CONST_FUNCTION_PATTERN, content):
            chunk = TypeScriptParser._create_chunk_from_match(
                filepath, content, lines, match, "function"
            )
            if chunk:
                chunks.append(chunk)
        
        for match in re.finditer(TypeScriptParser.COMPONENT_PATTERN, content):
            chunk = TypeScriptParser._create_chunk_from_match(
                filepath, content, lines, match, "component"
            )
            if chunk:
                chunks.append(chunk)
        
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
            
            line_start = content[:start_pos].count('\n') + 1
            line_end = TypeScriptParser._find_closing_bracket(
                lines, line_start - 1, content[start_pos:]
            )
            
            func_code = '\n'.join(lines[line_start-1:line_end])
            
            # Limitar tamanho (max 100 linhas)
            if line_end - line_start > 100:
                line_end = line_start + 100
                func_code = '\n'.join(lines[line_start-1:line_end]) + "\n// ... (truncated)"
            
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
        
        return start_line + 30


# ═══════════════════════════════════════════════════════════
# 📂 FILE INDEXER
# ═══════════════════════════════════════════════════════════

class FileIndexer:
    """Indexa ficheiros individuais"""
    
    def __init__(self, rag: CodebaseRAG):
        self.rag = rag
        self.parsers = {
            '.py': PythonParser(),
            '.ts': TypeScriptParser(),
            '.tsx': TypeScriptParser(),
            '.jsx': TypeScriptParser(),
            '.js': TypeScriptParser()
        }
    
    def index_file(self, filepath: Path, repo_root: Path) -> bool:
        """Indexa um ficheiro completo"""
        try:
            relative_path = filepath.relative_to(repo_root)
        except ValueError:
            relative_path = filepath
        
        print(f"📄 Indexing: {relative_path}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")
            return False
        
        ext = filepath.suffix
        if ext not in self.parsers:
            print(f"  ⚠️ Unsupported extension: {ext}")
            return False
        
        parser = self.parsers[ext]
        function_chunks, imports, exports = parser.parse_file(relative_path, content)
        
        # Indexar ficheiro completo
        file_chunk = CodeChunk(
            id=f"file:{relative_path}",
            type="file",
            path=str(relative_path),
            name=filepath.name,
            content=content,
            language=self._get_language(ext),
            line_start=1,
            line_end=len(content.split('\n')),
            imports=imports,
            exports=exports,
            parent_file=None,
            last_modified=datetime.now().isoformat(),
            commit_sha=None
        )
        
        success = self.rag.index_file(file_chunk)
        
        if not success:
            return False
        
        # Indexar funções/componentes
        for chunk in function_chunks:
            self.rag.index_function(chunk)
        
        print(f"  ✅ Indexed: 1 file + {len(function_chunks)} functions")
        
        # Atualizar dependências
        self.rag.update_dependencies(str(relative_path), imports, exports)
        
        return True
    
    @staticmethod
    def _get_language(ext: str) -> str:
        """Mapeia extensão para linguagem"""
        lang_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.js': 'javascript'
        }
        return lang_map.get(ext, 'unknown')


# ═══════════════════════════════════════════════════════════
# 📦 CODEBASE INDEXER
# ═══════════════════════════════════════════════════════════

class CodebaseIndexer:
    """Indexa codebase completo ou incremental"""
    
    IGNORE_DIRS = {
        'node_modules', 'dist', 'build', '.git', '__pycache__',
        '.next', '.nuxt', 'venv', 'env', '.venv', 'coverage',
        '.pytest_cache', '.mypy_cache', 'chroma_db', '.rag'
    }
    
    IGNORE_FILES = {
        '.pyc', '.map', '.min.js', '.bundle.js', 
        'package-lock.json', 'yarn.lock', 'poetry.lock'
    }
    
    def __init__(self, repo_path: str, rag: CodebaseRAG):
        self.repo_path = Path(repo_path).resolve()
        self.rag = rag
        self.file_indexer = FileIndexer(rag)
    
    def index_all(self) -> Dict:
        """Indexa codebase completo"""
        print(f"🚀 Starting full indexation of: {self.repo_path}")
        
        files_found = []
        for ext in ['.py', '.ts', '.tsx', '.jsx', '.js']:
            files_found.extend(self.repo_path.rglob(f"*{ext}"))
        
        files_to_index = [f for f in files_found if self._should_index(f)]
        
        print(f"📊 Found {len(files_to_index)} files to index")
        
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
        
        stats = {
            "total_files": len(files_to_index),
            "success": success_count,
            "errors": error_count,
            "rag_stats": self.rag.get_stats()
        }
        
        print(f"\n✅ Indexation complete!")
        print(f"  Success: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total: {stats['rag_stats']['total_files']} files, {stats['rag_stats']['total_functions']} functions")
        
        return stats
    
    def index_files(self, filepaths: List[str]) -> Dict:
        """Indexa lista específica de ficheiros (incremental)"""
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
            
            # Remover chunks antigos
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
        for part in filepath.parts:
            if part in self.IGNORE_DIRS:
                return False
        
        if filepath.suffix in self.IGNORE_FILES:
            return False
        
        return True


# ═══════════════════════════════════════════════════════════
# 🚀 MAIN / CLI
# ═══════════════════════════════════════════════════════════

def main():
    """Entry point do script"""
    parser = argparse.ArgumentParser(
        description="Index CinemaWebApp codebase for RAG"
    )
    
    parser.add_argument(
        '--root',
        type=str,
        required=True,
        help='Path to project root'
    )
    
    parser.add_argument(
        '--db',
        type=str,
        required=True,
        help='Path to ChromaDB storage'
    )
    
    parser.add_argument(
        '--update',
        action='store_true',
        help='Incremental update mode'
    )
    
    parser.add_argument(
        '--files',
        type=str,
        help='File with list of files to update (one per line)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Inicializar RAG
    print("🧠 Initializing RAG system...")
    rag = CodebaseRAG(persist_directory=args.db)
    
    # Inicializar indexer
    indexer = CodebaseIndexer(args.root, rag)
    
    # Executar indexação
    if args.update and args.files:
        # Modo incremental
        with open(args.files, 'r') as f:
            files = [line.strip() for line in f if line.strip()]
        stats = indexer.index_files(files)
    else:
        # Modo completo
        stats = indexer.index_all()
    
    # Mostrar estatísticas finais
    if args.verbose:
        print("\n" + "="*50)
        print("📊 FINAL STATISTICS")
        print("="*50)
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")


if __name__ == "__main__":
    main()