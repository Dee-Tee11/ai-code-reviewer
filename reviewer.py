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


def print_banner():
    """Imprime banner de início"""
    print("=" * 60)
    print("🎓 AI Code Mentor - Educational Code Reviewer")
    print("=" * 60)


def validate_environment() -> tuple[str, str]:
    """
    Valida que as env vars necessárias existem
    
    Returns:
        (groq_token, gh_token)
    
    Raises:
        SystemExit: Se tokens não existirem
    """
    groq_token = os.getenv("GROQ_API_KEY")
    gh_token = os.getenv("GITHUB_TOKEN")
    
    if not groq_token:
        print("❌ GROQ_API_KEY not found!")
        sys.exit(1)
    
    if not gh_token:
        print("❌ GITHUB_TOKEN not found!")
        sys.exit(1)
    
    return groq_token, gh_token


def check_rag_availability() -> tuple[bool, str]:
    """
    Verifica se RAG está disponível (baseado apenas na existência da ChromaDB)
    
    Returns:
        (is_available, db_path)
    """
    enable_rag = os.getenv("ENABLE_RAG", "false").lower() == "true"
    rag_db_path = os.getenv("RAG_DB_PATH", "./chroma_db")
    
    if not enable_rag:
        print("ℹ️ RAG disabled (ENABLE_RAG=false)")
        return False, rag_db_path
    
    # Verificar se ChromaDB existe e não está vazia
    db_path = Path(rag_db_path)
    
    if not db_path.exists():
        print(f"⚠️ RAG enabled but database not found at {rag_db_path}")
        print("💡 To enable RAG:")
        print("   1. Run locally: python .rag/build.py")
        print("   2. Commit: git add chroma_db/")
        print("   3. Push: git push")
        return False, rag_db_path
    
    # Verificar se tem conteúdo
    if not any(db_path.iterdir()):
        print(f"⚠️ RAG database at {rag_db_path} is empty")
        return False, rag_db_path
    
    # Verificar se tem o ficheiro principal do ChromaDB
    chroma_sqlite = db_path / "chroma.sqlite3"
    if not chroma_sqlite.exists():
        print(f"⚠️ ChromaDB file not found at {chroma_sqlite}")
        return False, rag_db_path
    
    # Tudo OK!
    print(f"✅ RAG database found at {rag_db_path}")
    
    # Mostrar estatísticas se possível
    try:
        db_size = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file())
        db_size_mb = db_size / (1024 * 1024)
        print(f"   📊 Database size: {db_size_mb:.2f} MB")
    except Exception:
        pass
    
    return True, rag_db_path


def initialize_rag(rag_db_path: str):
    """
    Inicializa sistema RAG (só é chamado se ChromaDB existe)
    
    Returns:
        ChromaRAG instance ou None
    """
    try:
        # Import do wrapper
        from chroma_rag import ChromaRAG
        
        print(f"🧠 Loading RAG database from {rag_db_path}...")
        print(f"   📍 Absolute path: {Path(rag_db_path).absolute()}")
        
        # Verificar conteúdo da pasta
        db_path = Path(rag_db_path)
        print(f"   📂 Contents:")
        for item in db_path.iterdir():
            if item.is_file():
                size = item.stat().st_size / 1024
                print(f"      - {item.name} ({size:.1f} KB)")
            else:
                print(f"      - {item.name}/ (directory)")
        
        # Criar ChromaRAG wrapper
        rag = ChromaRAG(persist_directory=rag_db_path)
        
        print(f"   ✅ RAG initialized successfully")
        
        # Obter estatísticas
        stats = rag.get_stats()
        
        if stats["total_items"] == 0:
            print("  ⚠️ RAG database is empty")
            print("     💡 Try running: python .rag/build.py")
            return None
        
        print(f"  ✅ RAG loaded successfully!")
        print(f"     📊 Total items: {stats['total_items']}")
        
        for name, count in stats["collections"].items():
            if count > 0:
                print(f"     📦 {name}: {count} items")
        
        return rag
        
    except ImportError as e:
        print(f"  ⚠️ ChromaRAG wrapper not found: {e}")
        print("     💡 Make sure chroma_rag.py is in the action directory")
        return None
    except Exception as e:
        print(f"  ⚠️ RAG initialization failed: {type(e).__name__}: {e}")
        import traceback
        print("     Full traceback:")
        traceback.print_exc()
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
        
        # 4. Verificar disponibilidade do RAG
        print("\n🧠 Checking RAG availability...")
        rag_available, rag_db_path = check_rag_availability()
        
        # 5. Inicializar RAG se disponível
        rag = None
        if rag_available:
            rag = initialize_rag(rag_db_path)
        else:
            print("⚡ Continuing WITHOUT RAG context\n")
        
        # 6. Inicializar serviços
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
        
        # 7. Verificar se deve skip
        print("\n🔍 Checking if should skip review...")
        if github_service.should_skip_review():
            print("✅ Review skipped")
            return 0
        
        # 8. Obter ficheiros alterados
        print("\n📁 Getting changed files...")
        changed_files = github_service.get_changed_files(
            skip_file_types=config_service.get_skip_file_types()
        )
        
        if not changed_files:
            print("✅ No files to review")
            return 0
        
        print(f"  📝 Found {len(changed_files)} files to review")
        
        # 9. Fazer review de cada ficheiro
        print("\n🤖 Starting code review...")
        all_comments = []
        stats = ReviewStatistics(
            total_files=len(changed_files),
            rag_enabled=rag_available  # Usa o flag, não o objeto
        )
        
        for file_change in changed_files:
            comments = ai_service.review_code(file_change)
            
            for comment in comments:
                stats.add_comment(comment)
            
            all_comments.extend(comments)
        
        # 10. Aplicar limites
        max_comments = config_service.get_max_comments()
        if len(all_comments) > max_comments:
            print(f"\n⚠️ Limiting comments from {len(all_comments)} to {max_comments}")
            all_comments = CommentFormatter.limit_comments(all_comments, max_comments)
        
        # 11. Postar comentários
        print(f"\n💬 Posting {len(all_comments)} comments...")
        
        if all_comments:
            github_service.post_review_comments(all_comments)
        else:
            print("  ✅ No issues found!")
        
        # 12. Postar estatísticas
        print("\n📊 Posting statistics...")
        github_service.post_statistics_summary(
            total_files=stats.total_files,
            total_comments=stats.total_comments,
            comments=all_comments,
            rag_enabled=stats.rag_enabled
        )
        
        # 13. Resumo final
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