#!/usr/bin/env python3
"""
Indexer para ficheiros individuais
"""

from pathlib import Path
from datetime import datetime

from codebase_rag import CodeChunk
from .python_parser import PythonParser
from .typescript_parser import TypeScriptParser


class FileIndexer:
    """Indexa ficheiros individuais"""
    
    def __init__(self, rag):
        self.rag = rag
        self.parsers = {
            '.py': PythonParser(),
            '.ts': TypeScriptParser(),
            '.tsx': TypeScriptParser(),
            '.jsx': TypeScriptParser(),
            '.js': TypeScriptParser()
        }
    
    def index_file(self, filepath: Path, repo_root: Path) -> bool:
        """
        Indexa um ficheiro completo
        
        Args:
            filepath: Caminho absoluto do ficheiro
            repo_root: Raiz do repositório
            
        Returns:
            True se indexado com sucesso
        """
        # Calcular path relativo
        try:
            relative_path = filepath.relative_to(repo_root)
        except ValueError:
            relative_path = filepath
        
        print(f"📄 Indexing: {relative_path}")
        
        # Ler conteúdo
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")
            return False
        
        # Detectar parser
        ext = filepath.suffix
        if ext not in self.parsers:
            print(f"  ⚠️ Unsupported extension: {ext}")
            return False
        
        parser = self.parsers[ext]
        
        # Parse do ficheiro
        function_chunks, imports, exports = parser.parse_file(relative_path, content)
        
        # 1. Indexar ficheiro completo (Nível 1)
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
        
        # 2. Indexar funções/componentes (Nível 2)
        for chunk in function_chunks:
            self.rag.index_function(chunk)
        
        print(f"  ✅ Indexed: 1 file + {len(function_chunks)} functions")
        
        # 3. Atualizar dependências (Nível 3)
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