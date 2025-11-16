#!/usr/bin/env python3
"""
GitHub Service
Gere interação com GitHub API (commits, PRs, comments)
"""

import os
import sys
import json
from typing import List, Optional
from pathlib import Path

from github import Github, Auth
from github.GithubException import GithubException

from src.models import FileChange, ReviewComment
from .formatter_service import CommentFormatter


class GitHubServiceError(Exception):
    """Exceção para erros do GitHub Service"""
    pass


class GitHubService:
    """
    Serviço para interagir com GitHub API
    
    Responsabilidades:
    - Obter ficheiros alterados (commit ou PR)
    - Postar comentários de review
    - Verificar se deve skip review
    - Detectar contexto (PR vs commit)
    """
    
    def __init__(self, token: str, skip_patterns: List[str] = None):
        """
        Inicializa o serviço GitHub
        
        Args:
            token: GitHub Personal Access Token
            skip_patterns: Padrões de mensagem de commit para skip
        
        Raises:
            GitHubServiceError: Se token ou env vars não existirem
        """
        if not token:
            raise GitHubServiceError("GitHub token is required")
        
        self.github = Github(auth=Auth.Token(token))
        self.skip_patterns = skip_patterns or [
            "[skip-review]", "[no-review]", "WIP:", "Merge", "Revert"
        ]
        
        # Obter informação do contexto GitHub Actions
        self.repo_name = os.getenv("GITHUB_REPOSITORY")
        self.commit_sha = os.getenv("GITHUB_SHA")
        
        if not self.repo_name:
            raise GitHubServiceError("GITHUB_REPOSITORY not found in environment")
        
        if not self.commit_sha:
            raise GitHubServiceError("GITHUB_SHA not found in environment")
        
        # Conectar ao repo
        try:
            self.repo = self.github.get_repo(self.repo_name)
        except GithubException as e:
            raise GitHubServiceError(f"Failed to connect to repository: {e}")
        
        # Detectar PR (se existir)
        self.pr_number = self._detect_pr_number()
        self.pull_request = None
        
        if self.pr_number:
            try:
                self.pull_request = self.repo.get_pull(self.pr_number)
                print(f"  📌 Detected PR #{self.pr_number}")
            except GithubException as e:
                print(f"  ⚠️ Failed to get PR: {e}")
                self.pr_number = None
        else:
            print("  ℹ️ No PR detected, will review commit")
    
    def _detect_pr_number(self) -> Optional[int]:
        """
        Detecta número do PR (se existir)
        
        Returns:
            Número do PR ou None
        """
        # Método 1: GITHUB_REF (refs/pull/123/merge)
        github_ref = os.getenv("GITHUB_REF", "")
        if "pull" in github_ref:
            try:
                pr_num = int(github_ref.split("/")[2])
                return pr_num
            except (IndexError, ValueError):
                pass
        
        # Método 2: Event file (pull_request event)
        event_path = os.getenv("GITHUB_EVENT_PATH")
        if event_path and os.path.exists(event_path):
            try:
                with open(event_path) as f:
                    event = json.load(f)
                    if "pull_request" in event:
                        return event["pull_request"]["number"]
            except Exception:
                pass
        
        return None
    
    def should_skip_review(self) -> bool:
        """
        Verifica se deve skip review baseado na mensagem do commit
        
        Returns:
            True se deve skip
        """
        try:
            commit = self.repo.get_commit(self.commit_sha)
            message = commit.commit.message
            
            for pattern in self.skip_patterns:
                if pattern.strip() in message:
                    print(f"  ⏭️ Skipping review (pattern: {pattern})")
                    return True
            
            return False
            
        except GithubException as e:
            print(f"  ⚠️ Failed to get commit message: {e}")
            return False
    
    def get_changed_files(self, skip_file_types: List[str] = None) -> List[FileChange]:
        """
        Obtém lista de ficheiros alterados
        
        Args:
            skip_file_types: Extensões de ficheiros a ignorar
        
        Returns:
            Lista de FileChange objects
        """
        skip_file_types = skip_file_types or [
            ".json", ".md", ".lock", ".min.js", ".bundle.js", ".map"
        ]
        
        try:
            # Obter ficheiros do PR ou commit
            if self.pull_request:
                files = self.pull_request.get_files()
            else:
                commit = self.repo.get_commit(self.commit_sha)
                files = commit.files
            
            changes = []
            
            for file in files:
                # Skip se for tipo ignorado
                if self._should_skip_file(file.filename, skip_file_types):
                    print(f"  ⏭️ Skipping {file.filename}")
                    continue
                
                # Obter conteúdo do ficheiro (se não foi apagado)
                content = None
                if file.status != "deleted":
                    content = self._get_file_content(file.filename)
                
                # Criar FileChange object
                change = FileChange(
                    filename=file.filename,
                    status=file.status,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    patch=file.patch,
                    content=content
                )
                
                changes.append(change)
            
            return changes
            
        except GithubException as e:
            raise GitHubServiceError(f"Failed to get changed files: {e}")
    
    def _get_file_content(self, filepath: str) -> Optional[str]:
        """
        Obtém conteúdo de um ficheiro
        
        Args:
            filepath: Caminho do ficheiro
        
        Returns:
            Conteúdo do ficheiro ou None
        """
        try:
            file_content = self.repo.get_contents(filepath, ref=self.commit_sha)
            return file_content.decoded_content.decode('utf-8')
        except GithubException:
            return None
        except UnicodeDecodeError:
            return None
    
    def _should_skip_file(self, filename: str, skip_extensions: List[str]) -> bool:
        """
        Verifica se deve skip um ficheiro
        
        Args:
            filename: Nome do ficheiro
            skip_extensions: Lista de extensões a ignorar
        
        Returns:
            True se deve skip
        """
        # Skip por extensão
        if any(filename.endswith(ext) for ext in skip_extensions):
            return True
        
        # Skip por diretório
        skip_dirs = ["node_modules", "dist", "build", ".git", "__pycache__"]
        if any(dir_name in filename for dir_name in skip_dirs):
            return True
        
        return False
    
    def post_review_comments(self, comments: List[ReviewComment], 
                           use_inline: bool = False):
        """
        Posta comentários de review no GitHub
        
        Args:
            comments: Lista de ReviewComment objects
            use_inline: Se True, tenta postar inline; senão posta como summary geral
        """
        if not comments:
            print("  ✅ No comments to post")
            return
        
        try:
            # Agrupar por ficheiro
            comments_by_file = CommentFormatter.group_comments_by_file(comments)
            
            # Formatar como summary geral
            formatted_comment = CommentFormatter.format_review_summary(
                comments_by_file, 
                len(comments)
            )
            
            # Postar como comentário geral no commit
            commit = self.repo.get_commit(self.commit_sha)
            commit.create_comment(body=formatted_comment)
            
            print(f"  ✅ Posted general review comment with {len(comments)} issues")
            
        except GithubException as e:
            print(f"  ❌ Failed to post comment: {e}")
            
            # Fallback: tentar postar inline
            if use_inline:
                print("  ⚠️ Trying fallback: inline comments...")
                self._post_inline_comments_fallback(comments)
    
    def _post_inline_comments_fallback(self, comments: List[ReviewComment]):
        """
        Fallback: tenta postar comentários inline individuais
        
        Args:
            comments: Lista de ReviewComment objects
        """
        try:
            commit = self.repo.get_commit(self.commit_sha)
            
            for comment in comments:
                try:
                    formatted = CommentFormatter.format_single_comment(comment)
                    
                    commit.create_comment(
                        body=formatted,
                        path=comment.file_path,
                        position=comment.line_number
                    )
                    
                    print(f"    ✅ Posted inline: {comment.file_path}:{comment.line_number}")
                    
                except GithubException as e:
                    print(f"    ⚠️ Failed inline comment: {e}")
                    
        except GithubException as e:
            print(f"  ❌ Fallback also failed: {e}")
    
    def post_statistics_summary(self, total_files: int,
                               total_comments: int,
                               comments: List[ReviewComment],
                               rag_enabled: bool = False):
        """
        Posta summary de estatísticas no GitHub Actions step summary
        
        Args:
            total_files: Total de ficheiros analisados
            total_comments: Total de comentários
            comments: Lista de todos os comentários
            rag_enabled: Se RAG foi usado
        """
        summary = CommentFormatter.format_statistics_summary(
            total_files,
            total_comments,
            comments,
            rag_enabled
        )
        
        # Adicionar ao $GITHUB_STEP_SUMMARY
        step_summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if step_summary_file:
            try:
                with open(step_summary_file, "a") as f:
                    f.write(summary)
                print("  ✅ Statistics added to step summary")
            except Exception as e:
                print(f"  ⚠️ Failed to write step summary: {e}")
    
    def close(self):
        """Fecha conexão com GitHub"""
        self.github.close()