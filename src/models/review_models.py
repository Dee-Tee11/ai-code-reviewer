#!/usr/bin/env python3
"""
Review Models - Dataclasses centralizadas
Contém todos os modelos de dados usados no AI Code Reviewer
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


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
    
    # Helper functions
    "create_review_comment",
]