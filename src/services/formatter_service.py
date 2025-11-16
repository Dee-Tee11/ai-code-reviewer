#!/usr/bin/env python3
"""
Comment Formatter Service
Formata comentários de review para GitHub (Markdown)
"""

from typing import List, Dict
from src.models import ReviewComment


class CommentFormatter:
    """
    Formata comentários de review em diferentes estilos:
    - Review summary (todos os comentários agrupados)
    - Single inline comment
    - Statistics summary
    """
    
    # Emoji map para severidades
    SEVERITY_EMOJI = {
        "critical": "🚨",
        "error": "❌",
        "warning": "⚠️",
        "info": "💡"
    }
    
    # Ordem de severidade (para sorting)
    SEVERITY_ORDER = ["critical", "error", "warning", "info"]
    
    @staticmethod
    def format_review_summary(comments_by_file: Dict[str, List[ReviewComment]], 
                             total_issues: int) -> str:
        """
        Formata todos os comentários num único review summary
        
        Args:
            comments_by_file: Dict com comentários agrupados por ficheiro
            total_issues: Total de issues encontradas
        
        Returns:
            String formatada em Markdown para GitHub
        """
        # Header
        summary = f"""## 🎓 AI Code Review

**Total de issues encontradas:** {total_issues}

---

"""
        
        # Para cada ficheiro
        for file_path, file_comments in sorted(comments_by_file.items()):
            summary += f"### 📁 `{file_path}`\n\n"
            
            # Ordenar comentários por severidade e linha
            sorted_comments = sorted(
                file_comments, 
                key=lambda c: (
                    CommentFormatter.SEVERITY_ORDER.index(c.severity), 
                    c.line_number
                )
            )
            
            # Adicionar cada comentário
            for comment in sorted_comments:
                emoji = CommentFormatter.SEVERITY_EMOJI.get(comment.severity, "💡")
                
                summary += f"""#### {emoji} **{comment.title}** (linha {comment.line_number})
**Severidade:** `{comment.severity}` | **Categoria:** `{comment.category}`

{comment.content}

---

"""
        
        # Footer com estatísticas
        summary += CommentFormatter._format_statistics_section(comments_by_file)
        summary += "\n_Review gerado por AI Code Mentor 🤖_"
        
        return summary
    
    @staticmethod
    def _format_statistics_section(comments_by_file: Dict[str, List[ReviewComment]]) -> str:
        """Formata seção de estatísticas (collapsible)"""
        section = """
<details>
<summary>📊 Estatísticas desta Review</summary>

"""
        
        # Contar por severidade
        severity_counts = {}
        for severity in CommentFormatter.SEVERITY_ORDER:
            count = sum(
                1 for comments in comments_by_file.values() 
                for c in comments 
                if c.severity == severity
            )
            if count > 0:
                emoji = CommentFormatter.SEVERITY_EMOJI[severity]
                severity_counts[severity] = count
                section += f"- {emoji} **{severity.capitalize()}:** {count}\n"
        
        section += "\n</details>\n\n"
        
        return section
    
    @staticmethod
    def format_single_comment(comment: ReviewComment) -> str:
        """
        Formata um único comentário inline
        
        Args:
            comment: ReviewComment a formatar
        
        Returns:
            String formatada para GitHub inline comment
        """
        emoji = CommentFormatter.SEVERITY_EMOJI.get(comment.severity, "💡")
        
        return f"""{emoji} **{comment.title}**

**Severidade:** `{comment.severity}` | **Categoria:** `{comment.category}`

{comment.content}

---
_AI Code Mentor 🤖_"""
    
    @staticmethod
    def format_statistics_summary(total_files: int,
                                  total_comments: int,
                                  comments: List[ReviewComment],
                                  rag_enabled: bool = False) -> str:
        """
        Formata summary de estatísticas para GitHub Actions step summary
        
        Args:
            total_files: Total de ficheiros analisados
            total_comments: Total de comentários gerados
            comments: Lista de todos os comentários
            rag_enabled: Se RAG foi usado
        
        Returns:
            String formatada para $GITHUB_STEP_SUMMARY
        """
        summary = f"""## 📊 AI Code Review Statistics

**Files Analyzed:** {total_files}
**Comments Generated:** {total_comments}
**RAG Context:** {'✅ Enabled' if rag_enabled else '⚠️ Disabled'}

### By Severity
"""
        
        # Contar por severidade
        for severity in CommentFormatter.SEVERITY_ORDER:
            count = sum(1 for c in comments if c.severity == severity)
            if count > 0:
                emoji = CommentFormatter.SEVERITY_EMOJI[severity]
                percentage = (count / total_comments * 100) if total_comments > 0 else 0
                summary += f"- {emoji} **{severity.capitalize()}:** {count} ({percentage:.1f}%)\n"
        
        # Contar por categoria
        summary += "\n### By Category\n"
        categories = {}
        for comment in comments:
            categories[comment.category] = categories.get(comment.category, 0) + 1
        
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_comments * 100) if total_comments > 0 else 0
            summary += f"- **{category}:** {count} ({percentage:.1f}%)\n"
        
        return summary
    
    @staticmethod
    def format_no_issues_message() -> str:
        """
        Mensagem quando não há issues encontradas
        
        Returns:
            Mensagem formatada
        """
        return """## 🎓 AI Code Review

✅ **Nenhuma issue encontrada!**

O código analisado parece estar em boa forma. Continue com o bom trabalho! 🚀

---
_Review gerado por AI Code Mentor 🤖_"""
    
    @staticmethod
    def format_error_message(error: str, file_path: str = None) -> str:
        """
        Formata mensagem de erro
        
        Args:
            error: Mensagem de erro
            file_path: Ficheiro onde ocorreu o erro (opcional)
        
        Returns:
            Mensagem formatada
        """
        msg = "## ⚠️ AI Code Review - Error\n\n"
        
        if file_path:
            msg += f"**File:** `{file_path}`\n\n"
        
        msg += f"**Error:** {error}\n\n"
        msg += "_Please check the logs for more details._"
        
        return msg
    
    @staticmethod
    def group_comments_by_file(comments: List[ReviewComment]) -> Dict[str, List[ReviewComment]]:
        """
        Agrupa comentários por ficheiro
        
        Args:
            comments: Lista de comentários
        
        Returns:
            Dict com comentários agrupados por file_path
        """
        grouped = {}
        
        for comment in comments:
            if comment.file_path not in grouped:
                grouped[comment.file_path] = []
            grouped[comment.file_path].append(comment)
        
        return grouped
    
    @staticmethod
    def filter_by_severity(comments: List[ReviewComment], 
                          min_severity: str = "info") -> List[ReviewComment]:
        """
        Filtra comentários por severidade mínima
        
        Args:
            comments: Lista de comentários
            min_severity: Severidade mínima (info, warning, error, critical)
        
        Returns:
            Lista filtrada
        """
        severity_levels = {
            "info": 0,
            "warning": 1,
            "error": 2,
            "critical": 3
        }
        
        min_level = severity_levels.get(min_severity, 0)
        
        return [
            c for c in comments 
            if severity_levels.get(c.severity, 0) >= min_level
        ]
    
    @staticmethod
    def limit_comments(comments: List[ReviewComment], 
                      max_comments: int = 10) -> List[ReviewComment]:
        """
        Limita número de comentários (prioriza por severidade)
        
        Args:
            comments: Lista de comentários
            max_comments: Máximo de comentários
        
        Returns:
            Lista limitada e ordenada por prioridade
        """
        if len(comments) <= max_comments:
            return comments
        
        # Ordenar por severidade (critical primeiro) e depois por linha
        sorted_comments = sorted(
            comments,
            key=lambda c: (
                CommentFormatter.SEVERITY_ORDER.index(c.severity),
                c.line_number
            )
        )
        
        return sorted_comments[:max_comments]