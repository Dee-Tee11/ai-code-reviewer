#!/usr/bin/env python3
"""
ChromaDB storage layer
"""

import os
from typing import Dict, List
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

from .models import CodeChunk


class ChromaStorage:
    """Gestão de persistência com ChromaDB"""
    
    def __init__(self, persist_directory: str = "./chroma_db", model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa o storage
        
        Args:
            persist_directory: Caminho para a base de dados ChromaDB
            model_name: Nome do modelo de embeddings
        """
        self.persist_directory = persist_directory
        self.model_name = model_name
        
        print(f"🧠 Loading embedding model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            raise
        
        print(f"💾 Initializing ChromaDB at {persist_directory}")
        
        # Criar diretório se não existir
        os.makedirs(persist_directory, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        except Exception as e:
            print(f"❌ Failed to initialize ChromaDB: {e}")
            raise
        
        # Tentar carregar coleção existente
        try:
            self.collection = self.client.get_collection("codebase")
            count = self.collection.count()
            print(f"  ✅ Connected to existing collection with {count} items")
        except Exception as e:
            print(f"  ℹ️ Collection 'codebase' not found, creating new...")
            try:
                self.collection = self.client.create_collection("codebase")
                print(f"  ✅ Empty collection created")
            except Exception as create_error:
                print(f"❌ Failed to create collection: {create_error}")
                raise
    
    def index_file(self, chunk: CodeChunk) -> bool:
        """
        Indexa um ficheiro completo
        
        Args:
            chunk: CodeChunk representando o ficheiro
        
        Returns:
            True se sucesso
        """
        try:
            # Criar documento para embedding
            doc = f"File: {chunk.name}\nPath: {chunk.path}\n{chunk.content}"
            
            # Criar embedding
            embedding = self.model.encode(doc).tolist()
            
            # Metadata
            metadata = {
                'type': chunk.type,
                'file': chunk.path,
                'name': chunk.name,
                'language': chunk.language,
                'line_start': chunk.line_start,
                'line_end': chunk.line_end,
                'imports': ','.join(chunk.imports),
                'exports': ','.join(chunk.exports),
                'last_modified': chunk.last_modified
            }
            
            # Adicionar à coleção
            self.collection.upsert(
                documents=[doc],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[chunk.id]
            )
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error indexing file {chunk.path}: {e}")
            return False
    
    def index_function(self, chunk: CodeChunk) -> bool:
        """
        Indexa uma função ou classe
        
        Args:
            chunk: CodeChunk representando a função/classe
        
        Returns:
            True se sucesso
        """
        try:
            # Criar documento para embedding
            doc = f"{chunk.type}: {chunk.name}\nFile: {chunk.path}\n{chunk.content}"
            
            # Criar embedding
            embedding = self.model.encode(doc).tolist()
            
            # Metadata
            metadata = {
                'type': chunk.type,
                'file': chunk.path,
                'name': chunk.name,
                'language': chunk.language,
                'line_start': chunk.line_start,
                'line_end': chunk.line_end,
                'parent_file': chunk.parent_file or '',
                'last_modified': chunk.last_modified
            }
            
            # Adicionar à coleção
            self.collection.upsert(
                documents=[doc],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[chunk.id]
            )
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error indexing function {chunk.name}: {e}")
            return False
    
    def update_dependencies(self, filepath: str, imports: List[str], exports: List[str]):
        """
        Atualiza as dependências de um ficheiro
        
        Args:
            filepath: Caminho do ficheiro
            imports: Lista de imports
            exports: Lista de exports
        """
        try:
            # Buscar o ficheiro na coleção
            results = self.collection.get(
                where={"file": filepath, "type": "file"}
            )
            
            if results and results['ids']:
                file_id = results['ids'][0]
                
                # Atualizar metadata
                self.collection.update(
                    ids=[file_id],
                    metadatas=[{
                        'imports': ','.join(imports),
                        'exports': ','.join(exports)
                    }]
                )
                
        except Exception as e:
            print(f"  ⚠️ Error updating dependencies for {filepath}: {e}")
    
    def delete_file_chunks(self, filepath: str):
        """
        Remove todos os chunks de um ficheiro
        
        Args:
            filepath: Caminho do ficheiro
        """
        try:
            results = self.collection.get(
                where={"file": filepath}
            )
            
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"  🗑️ Deleted {len(results['ids'])} chunks from {filepath}")
                
        except Exception as e:
            print(f"  ⚠️ Error deleting chunks for {filepath}: {e}")
    
    def query(self, query_embedding: List[float], n_results: int):
        """
        Busca na coleção usando embedding
        
        Args:
            query_embedding: Embedding da query
            n_results: Número de resultados
            
        Returns:
            Resultados da query
        """
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
    
    def get(self, where: Dict = None, limit: int = None):
        """
        Busca na coleção usando filtros
        
        Args:
            where: Filtros
            limit: Limite de resultados
            
        Returns:
            Resultados
        """
        if limit:
            return self.collection.get(where=where, limit=limit)
        return self.collection.get(where=where)
    
    def count(self) -> int:
        """Retorna o número de items na coleção"""
        return self.collection.count()
    
    def encode(self, text: str) -> List[float]:
        """
        Cria embedding de texto
        
        Args:
            text: Texto para embedding
            
        Returns:
            Embedding como lista
        """
        return self.model.encode(text).tolist()
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas da base de dados"""
        try:
            count = self.collection.count()
            
            if count > 0:
                results = self.collection.get(limit=count)
                metadatas = results['metadatas']
                
                files = set()
                functions = 0
                dependencies_count = 0
                
                for meta in metadatas:
                    if meta.get('file'):
                        files.add(meta['file'])
                    if meta.get('type') in ['function', 'class', 'component']:
                        functions += 1
                    
                    # Contar imports e exports como dependências
                    imports = meta.get('imports', '')
                    exports = meta.get('exports', '')
                    if imports:
                        dependencies_count += len(imports.split(','))
                    if exports:
                        dependencies_count += len(exports.split(','))
                
                return {
                    'total_items': count,
                    'total_files': len(files),
                    'total_functions': functions,
                    'total_dependencies': dependencies_count
                }
            
            return {
                'total_items': 0,
                'total_files': 0,
                'total_functions': 0,
                'total_dependencies': 0
            }
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
            return {
                'total_items': 0,
                'total_files': 0,
                'total_functions': 0,
                'total_dependencies': 0
            }
    
    def reset(self):
        """Remove toda a coleção e recria vazia"""
        try:
            self.client.delete_collection("codebase")
            print("  🗑️ Collection deleted")
        except:
            pass