#!/usr/bin/env python3
"""
AI Code Mentor - Educational Code Reviewer
Entry Point Principal (Refatorado)

Este script é o entry point da GitHub Action.
A lógica está modularizada em src/services/
"""

import os
import sys
from pathlib import Path

# Adicionar src/ ao Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.models.review_models import ReviewStatistics
from src.services.config_service import ConfigService, ConfigurationError
from src.services.ai_service import AIService, AIServiceError
from src.services.github_service import GitHubService, GitHubServiceError
from src.services.formatter_service import CommentFormatter

# Importar RAG (opcional)
try:
    from codebase_rag import CodebaseRAG
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️ RAG module not available")


def print_banner():
    """Imprime banner de início"""
    print("=" * 60)
    print("🎓 AI Code Mentor - Educational Code Reviewer")
    print("=" * 60)


def validate_environment() -> tuple[str, str]:
    """
    Valida que as env vars necessárias existem
    
    Returns:
        (hf_token, gh_token)
    
    Raises:
        SystemExit: Se tokens não existirem
    """
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    gh_token = os.getenv("GITHUB_TOKEN")
    
    if not hf_token:
        print("❌ HUGGINGFACE_TOKEN not found!")
        sys.exit(1)
    
    if not gh_token:
        print("❌ GITHUB_TOKEN not found!")
        sys.exit(1)
    
    return hf_token, gh_token


def initialize_rag() -> 'CodebaseRAG':
    """
    Tenta inicializar sistema RAG (se enabled e disponível)
    
    Returns:
        CodebaseRAG instance ou None
    """
    enable_rag = os.getenv("ENABLE_RAG", "false").lower() == "true"
    
    if not enable_rag:
        print("ℹ️ RAG disabled (enable_rag=false)")
        return None
    
    if not RAG_AVAILABLE:
        print("⚠️ RAG enabled but module not available")
        return None
    
    rag_db_path = os.getenv("RAG_DB_PATH", "./chroma_db")
    
    # Verificar se BD existe
    if not Path(rag_db_path).exists():
        print(f"⚠️ RAG enabled but database not found at {rag_db_path}")
        print("💡 To enable RAG:")
        print("   1. Run locally: python .rag/build.py")
        print("   2. Commit: git add chroma_db/")
        print("   3. Push: git push")
        print("\n⚡ Continuing WITHOUT RAG context...\n")
        return None
    
    try:
        print(f"🧠 Loading RAG database from {rag_db_path}...")
        rag = CodebaseRAG(persist_directory=rag_db_path)
        stats = rag.get_stats()
        
        if stats['total_items'] == 0:
            print("⚠️ RAG database is empty!")
            return None
        
        print(f"  ✅ RAG loaded successfully!")
        print(f"     📊 {stats['total_files']} files")
        print(f"     ⚙️ {stats['total_functions']} functions")
        print(f"     🔗 {stats['total_dependencies']} dependencies")
        return rag
        
    except Exception as e:
        print(f"  ⚠️ RAG initialization failed: {e}")
        return None


def main():
    """Entry point principal"""
    try:
        # 1. Banner
        print_banner()
        
        # 2. Validar environment
        print("\n🔐 Validating environment...")
        hf_token, gh_token = validate_environment()
        print("  ✅ Tokens found")
        
        # 3. Carregar configuração
        print("\n📋 Loading configuration...")
        config_service = ConfigService()
        config = config_service.load()
        config_service.print_summary()
        
        # 4. Inicializar RAG (opcional)
        print("🧠 Initializing RAG...")
        rag = initialize_rag()
        
        # 5. Inicializar serviços
        print("\n🚀 Initializing services...")
        
        ai_service = AIService(
            token=hf_token,
            config=config,
            rag_system=rag
        )
        
        github_service = GitHubService(
            token=gh_token,
            skip_patterns=config_service.get_skip_patterns()
        )
        
        print("  ✅ All services initialized")
        
        # 6. Verificar se deve skip
        print("\n🔍 Checking if should skip review...")
        if github_service.should_skip_review():
            print("✅ Review skipped")
            return 0
        
        # 7. Obter ficheiros alterados
        print("\n📁 Getting changed files...")
        changed_files = github_service.get_changed_files(
            skip_file_types=config_service.get_skip_file_types()
        )
        
        if not changed_files:
            print("✅ No files to review")
            return 0
        
        print(f"  📝 Found {len(changed_files)} files to review")
        
        # 8. Fazer review de cada ficheiro
        print("\n🤖 Starting code review...")
        all_comments = []
        stats = ReviewStatistics(
            total_files=len(changed_files),
            rag_enabled=(rag is not None)
        )
        
        for file_change in changed_files:
            comments = ai_service.review_code(file_change)
            
            for comment in comments:
                stats.add_comment(comment)
            
            all_comments.extend(comments)
        
        # 9. Aplicar limites
        max_comments = config_service.get_max_comments()
        if len(all_comments) > max_comments:
            print(f"\n⚠️ Limiting comments from {len(all_comments)} to {max_comments}")
            all_comments = CommentFormatter.limit_comments(all_comments, max_comments)
        
        # 10. Postar comentários
        print(f"\n💬 Posting {len(all_comments)} comments...")
        
        if all_comments:
            github_service.post_review_comments(all_comments)
        else:
            print("  ✅ No issues found!")
        
        # 11. Postar estatísticas
        print("\n📊 Posting statistics...")
        github_service.post_statistics_summary(
            total_files=stats.total_files,
            total_comments=stats.total_comments,
            comments=all_comments,
            rag_enabled=stats.rag_enabled
        )
        
        # 12. Resumo final
        print("\n" + "="*60)
        print("✅ Review completed successfully!")
        print("="*60)
        print(stats.get_summary())
        print("="*60)
        
        return 0
        
    except ConfigurationError as e:
        print(f"\n❌ Configuration Error: {e}")
        return 1
    
    except AIServiceError as e:
        print(f"\n❌ AI Service Error: {e}")
        return 1
    
    except GitHubServiceError as e:
        print(f"\n❌ GitHub Service Error: {e}")
        return 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Review interrupted by user")
        return 1
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        print("\n👋 AI Code Mentor finished")


if __name__ == "__main__":
    sys.exit(main())