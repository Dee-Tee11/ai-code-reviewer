#!/usr/bin/env python3
"""
Review Models - Dataclasses centralizadas
Contém todos os modelos de dados usados no AI Code Reviewer
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


# ═══════════════════════════════════════════════════════════
# 📝 REVIEW MODELS
# ═══════════════════════════════════════════════════════════

@dataclass
class ReviewComment:
    """
    Representa um comentário de review educativo
    
    Attributes:
        file_path: Caminho do ficheiro
        line_number: Número da linha
        category: Categoria do problema (learning, security, etc)
        severity: Nível de severidade (info, warning, error, critical)
        title: Título do comentário
        content: Conteúdo completo do comentário (em Markdown)
        emoji: Emoji representativo da categoria
    """
    file_path: str
    line_number: int
    category: str
    severity: str
    title: str
    content: str
    emoji: str
    
    def __post_init__(self):
        """Validação dos campos"""
        valid_severities = ["info", "warning", "error", "critical"]
        if self.severity not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}, got {self.severity}")
        
        if self.line_number < 1:
            raise ValueError(f"Line number must be >= 1, got {self.line_number}")


@dataclass
class FileChange:
    """
    Representa uma alteração num ficheiro (commit ou PR)
    
    Attributes:
        filename: Nome/caminho do ficheiro
        status: Estado da alteração (added, modified, deleted)
        additions: Número de linhas adicionadas
        deletions: Número de linhas removidas
        changes: Total de alterações
        patch: Diff/patch do ficheiro
        content: Conteúdo completo do ficheiro (após alterações)
    """
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    content: Optional[str] = None
    
    def __post_init__(self):
        """Validação dos campos"""
        valid_statuses = ["added", "modified", "deleted", "renamed"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got {self.status}")
    
    @property
    def is_deleted(self) -> bool:
        """Verifica se o ficheiro foi apagado"""
        return self.status == "deleted"
    
    @property
    def is_new(self) -> bool:
        """Verifica se o ficheiro é novo"""
        return self.status == "added"
    
    @property
    def has_content(self) -> bool:
        """Verifica se tem conteúdo disponível"""
        return self.content is not None and len(self.content) > 0


# ═══════════════════════════════════════════════════════════
# 🧠 RAG MODELS
# ═══════════════════════════════════════════════════════════

@dataclass
class CodeChunk:
    """
    Representa um chunk de código para indexação no RAG
    
    Pode ser:
    - Um ficheiro completo (type='file')
    - Uma função (type='function')
    - Uma classe (type='class')
    - Um componente React (type='component')
    
    Attributes:
        id: Identificador único (hash MD5)
        type: Tipo do chunk
        path: Caminho relativo do ficheiro
        name: Nome do ficheiro/função/classe
        content: Conteúdo completo do código
        language: Linguagem de programação
        line_start: Linha inicial no ficheiro
        line_end: Linha final no ficheiro
        imports: Lista de imports deste chunk
        exports: Lista de exports deste chunk
        parent_file: ID do ficheiro pai (para funções/classes)
        last_modified: Timestamp da última modificação
        commit_sha: SHA do commit (opcional)
    """
    id: str
    type: str
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
    
    def __post_init__(self):
        """Validação e defaults"""
        valid_types = ["file", "function", "class", "component"]
        if self.type not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}, got {self.type}")
        
        valid_languages = ["python", "javascript", "typescript", "unknown"]
        if self.language not in valid_languages:
            raise ValueError(f"Language must be one of {valid_languages}, got {self.language}")
        
        # Default timestamp se não fornecido
        if not self.last_modified:
            self.last_modified = datetime.now().isoformat()
        
        # Validar linhas
        if self.line_start < 1:
            raise ValueError(f"line_start must be >= 1, got {self.line_start}")
        if self.line_end < self.line_start:
            raise ValueError(f"line_end ({self.line_end}) must be >= line_start ({self.line_start})")
    
    @property
    def line_count(self) -> int:
        """Número de linhas deste chunk"""
        return self.line_end - self.line_start + 1
    
    @property
    def is_file(self) -> bool:
        """Verifica se é um ficheiro completo"""
        return self.type == "file"
    
    @property
    def is_function(self) -> bool:
        """Verifica se é uma função/método"""
        return self.type == "function"


@dataclass
class RetrievalContext:
    """
    Contexto recuperado do sistema RAG
    
    Usado para fornecer informação relevante durante o code review:
    - Ficheiros similares na codebase
    - Funções/componentes relacionados
    - Dependências do ficheiro
    
    Attributes:
        similar_files: Lista de ficheiros com código similar
        related_functions: Lista de funções/componentes relacionados
        dependencies: Dict com imports/exports do ficheiro
    """
    similar_files: List[Dict] = field(default_factory=list)
    related_functions: List[Dict] = field(default_factory=list)
    dependencies: Dict = field(default_factory=dict)
    
    @property
    def has_context(self) -> bool:
        """Verifica se tem algum contexto disponível"""
        return (
            len(self.similar_files) > 0 or 
            len(self.related_functions) > 0 or 
            len(self.dependencies) > 0
        )
    
    @property
    def total_items(self) -> int:
        """Total de itens de contexto"""
        return len(self.similar_files) + len(self.related_functions)


# ═══════════════════════════════════════════════════════════
# 📊 STATISTICS MODELS
# ═══════════════════════════════════════════════════════════

@dataclass
class ReviewStatistics:
    """
    Estatísticas de uma review completa
    
    Attributes:
        total_files: Total de ficheiros analisados
        total_comments: Total de comentários gerados
        by_severity: Contagem por severidade
        by_category: Contagem por categoria
        rag_enabled: Se RAG foi usado
    """
    total_files: int = 0
    total_comments: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    rag_enabled: bool = False
    
    def add_comment(self, comment: ReviewComment):
        """Adiciona um comentário às estatísticas"""
        self.total_comments += 1
        
        # Contar por severidade
        severity = comment.severity
        self.by_severity[severity] = self.by_severity.get(severity, 0) + 1
        
        # Contar por categoria
        category = comment.category
        self.by_category[category] = self.by_category.get(category, 0) + 1
    
    def get_summary(self) -> str:
        """Retorna summary formatado"""
        lines = [
            f"📊 Review Statistics",
            f"  Files analyzed: {self.total_files}",
            f"  Comments generated: {self.total_comments}",
            f"  RAG context: {'✅ Enabled' if self.rag_enabled else '⚠️ Disabled'}",
            "",
            "By Severity:"
        ]
        
        severity_emoji = {
            "critical": "🚨",
            "error": "❌",
            "warning": "⚠️",
            "info": "💡"
        }
        
        for severity in ["critical", "error", "warning", "info"]:
            count = self.by_severity.get(severity, 0)
            if count > 0:
                emoji = severity_emoji.get(severity, "")
                lines.append(f"  {emoji} {severity}: {count}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 🔧 HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def create_review_comment(
    file_path: str,
    line_number: int,
    category: str,
    severity: str,
    title: str,
    content: str
) -> ReviewComment:
    """
    Factory function para criar ReviewComment com emoji automático
    
    Args:
        file_path: Caminho do ficheiro
        line_number: Número da linha
        category: Categoria do problema
        severity: Severidade
        title: Título
        content: Conteúdo
    
    Returns:
        ReviewComment com emoji apropriado
    """
    emoji_map = {
        "learning": "🎓",
        "security": "🔒",
        "performance": "🚀",
        "best_practices": "✨",
        "bugs": "🐛",
        "maintainability": "🔧"
    }
    
    emoji = emoji_map.get(category, "💡")
    
    return ReviewComment(
        file_path=file_path,
        line_number=line_number,
        category=category,
        severity=severity,
        title=title,
        content=content,
        emoji=emoji
    )


# ═══════════════════════════════════════════════════════════
# 📦 EXPORTS
# ═══════════════════════════════════════════════════════════

__all__ = [
    # Review models
    "ReviewComment",
    "FileChange",
    "ReviewStatistics",
    
    # RAG models
    "CodeChunk",
    "RetrievalContext",
    
    # Helper functions
    "create_review_comment",
]