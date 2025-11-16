#!/usr/bin/env python3
"""
Indexer - Entry Point Principal (Refatorado)
A lógica está modularizada em src/parsers/
"""

import sys
import argparse
from pathlib import Path

# Adicionar src/ ao Python path
sys.path.insert(0, str(Path(__file__).parent))

from codebase_rag import CodebaseRAG
from src.parsers.codebase_indexer import CodebaseIndexer


def main():
    """Entry point do script"""
    parser = argparse.ArgumentParser(
        description="Index codebase for AI Code Reviewer RAG"
    )
    
    parser.add_argument(
        '--repo',
        type=str,
        required=True,
        help='Path to repository root'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'incremental'],
        default='full',
        help='Indexation mode: full or incremental'
    )
    
    parser.add_argument(
        '--files',
        type=str,
        nargs='+',
        help='List of files for incremental mode (space-separated)'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default='./chroma_db',
        help='Path to ChromaDB storage'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database before indexing'
    )
    
    args = parser.parse_args()
    
    # Inicializar RAG
    print("🧠 Initializing RAG system...")
    rag = CodebaseRAG(persist_directory=args.db_path)
    
    # Reset se solicitado
    if args.reset:
        print("🗑️ Resetting database...")
        rag.reset()
        rag = CodebaseRAG(persist_directory=args.db_path)
    
    # Inicializar indexer
    indexer = CodebaseIndexer(args.repo, rag)
    
    # Executar indexação
    if args.mode == 'full':
        stats = indexer.index_all()
    else:
        if not args.files:
            print("❌ --files required for incremental mode")
            sys.exit(1)
        stats = indexer.index_files(args.files)
    
    # Mostrar estatísticas finais
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
    
    return 0


if __name__ == "__main__":
    sys.exit(main())