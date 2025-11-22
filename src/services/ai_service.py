#!/usr/bin/env python3
"""
AI Service
Interface com modelo AI (Groq) + RAG opcional para code review educativo
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Dict

from groq import Groq

from src.models.review_models import FileChange, ReviewComment, create_review_comment


class AIServiceError(Exception):
    """Exceção para erros do AI Service"""
    pass


class AIService:
    """
    Serviço de AI para code review educativo
    
    Responsabilidades:
    - Comunicar com modelo AI (Groq)
    - Construir prompts educativos
    - Integrar contexto RAG (se disponível)
    - Parsear respostas do AI
    """
    
    # Modelos Groq disponíveis (TODOS GRATUITOS):
    # - llama-3.3-70b-versatile (Melhor qualidade)
    # - llama-3.1-8b-instant (Mais rápido)
    # - mixtral-8x7b-32768 (Bom para código)
    # - gemma2-9b-it (Alternativa Google)
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    DEFAULT_MAX_TOKENS = 5000
    DEFAULT_TEMPERATURE = 0.7
    
    def __init__(self, 
                 token: str, 
                 config: Dict,
                 rag_system = None,  # ChromaDB Client ou None
                 model: str = None,
                 system_prompt: str = None):  # NEW: optional prompt from template
        """
        Inicializa o serviço AI
        
        Args:
            token: Groq API token
            config: Configuração completa (do ConfigService)
            rag_system: ChromaDB client opcional
            model: Nome do modelo (default: llama-3.3-70b-versatile)
        
        Raises:
            AIServiceError: Se token inválido ou erro na inicialização
        """
        if not token:
            raise AIServiceError("Groq API token is required")
        
        self.config = config
        self.rag = rag_system
        self.model = model or self.DEFAULT_MODEL
        
        try:
            self.client = Groq(api_key=token)
        except Exception as e:
            raise AIServiceError(f"Failed to initialize Groq client: {e}")
        
        # System prompt is REQUIRED (from template)
        if not system_prompt:
            raise AIServiceError("System prompt is required. Use templates to provide it.")
        
        self.system_prompt = system_prompt
        
        print(f"  🤖 AI Service initialized with model: {self.model}")
        print(f"  ⚡ Using Groq (ultra-fast inference)")
        if self.rag:
            print("  🧠 RAG context available")
    

    
    def review_code(self, file_change: FileChange) -> List[ReviewComment]:
        """
        Pede ao AI para fazer review educativo de um ficheiro
        
        Args:
            file_change: FileChange object com o código a review
        
        Returns:
            Lista de ReviewComment objects
        """
        print(f"  🔍 Reviewing {file_change.filename}...")
        
        # Construir prompt específico
        prompt = self._build_review_prompt(file_change)
        
        try:
            print(f"    🔄 Calling Groq API...")
            print(f"    📋 Model: {self.model}")
            
            # Chamar API do Groq
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.DEFAULT_MAX_TOKENS,
                temperature=self.DEFAULT_TEMPERATURE,
                response_format={"type": "json_object"}  # Força resposta JSON
            )
            
            print(f"    ✅ API responded successfully")
            
            # Parse da resposta
            response_text = response.choices[0].message.content
            print(f"    📝 Response length: {len(response_text)} chars")
            
            comments = self._parse_ai_response(response_text, file_change)
            
            print(f"    ✅ Found {len(comments)} issues")
            return comments
            
        except Exception as e:
            # Log detalhado do erro
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "(empty error message)"
            
            print(f"    ❌ AI error ({error_type}): {error_msg}")
            
            # Debug completo
            import traceback
            print(f"    🔍 Full error details:")
            traceback.print_exc()
            
            return []
    
    def _build_review_prompt(self, file_change: FileChange) -> str:
        """
        Constrói prompt específico para o ficheiro
        
        Args:
            file_change: FileChange object
        
        Returns:
            String com prompt completo
        """
        # Detectar linguagem
        language = self._detect_language(file_change.filename)
        
        # BASE DO PROMPT
        prompt = f"""# 📝 TAREFA: Review Educativo de Código

**Ficheiro:** `{file_change.filename}`
**Linguagem:** {language}
**Alterações:** +{file_change.additions} -{file_change.deletions}

## 🎯 TEU OBJETIVO
Fazer uma review **educativa** deste código. Usa o Socratic Method:
- Faz **perguntas** que levem o aluno à resposta
- Dá **pistas progressivas**, não soluções completas
- Ensina **conceitos**, não apenas corriges erros

## 📊 NÍVEIS DE SEVERIDADE
- **info**: Sugestões (só pergunta)
- **warning**: Problemas (pergunta + pistas)
- **error**: Bugs (pergunta + explicação)
- **critical**: Segurança (resposta completa)
"""
        
        # ADICIONAR CONTEXTO RAG (SE DISPONÍVEL)
        if self.rag:
            rag_context = self._get_rag_context(file_change)
            if rag_context:
                prompt += f"\n{rag_context}\n"
                print(f"    🧠 RAG context added")
        
        # CÓDIGO ALTERADO
        code = file_change.patch or file_change.content or "Sem alterações visíveis"
        prompt += f"""
## 💻 CÓDIGO ALTERADO
```{language.lower()}
{code}
```

## 📋 FORMATO DA RESPOSTA
Retorna **APENAS JSON válido** com este formato EXATO:

{{
  "reviews": [
    {{
      "line": 10,
      "severity": "warning",
      "category": "best_practices",
      "title": "Usar const em vez de let",
      "content": "🤔 **Pergunta:**\\nPor que usar `let` aqui se esta variável nunca é reatribuída?\\n\\n💡 **Pistas:**\\n1. Pensa em mutabilidade\\n2. O que significa `const`?\\n\\n🔍 **Investiga:**\\nDiferença entre let e const"
    }}
  ]
}}

**REGRAS IMPORTANTES:**
- Retorna APENAS JSON válido, sem markdown ou texto extra
- Máximo 5 reviews por ficheiro
- Prioriza: critical > error > warning > info
- Usa português de Portugal (pt-PT)
- Inclui emojis relevantes (🤔💡📚🔍✅❌🚀🔒)
"""
        
        if self.rag:
            prompt += "- **USA O CONTEXTO fornecido acima** para fazer reviews mais inteligentes e consistentes com o resto da aplicação\n"
        
        prompt += "\nAnalisa o código agora e retorna APENAS o JSON! 🎓\n"
        
        return prompt
    
    def _get_rag_context(self, file_change: FileChange) -> str:
        """
        Obtém contexto do RAG usando ChromaDB diretamente
        
        Args:
            file_change: FileChange object
        
        Returns:
            String formatada com contexto ou string vazia
        """
        try:
            # Extrair nome do ficheiro
            filename = Path(file_change.filename).name
            
            # Tentar obter coleção principal
            collections = self.rag.list_collections()
            
            if not collections:
                return ""
            
            # Prioridade: codebase > files > functions
            main_collection = None
            for col in collections:
                if col.name in ["codebase", "files", "functions"]:
                    count = col.count()
                    if count > 0:
                        main_collection = col
                        break
            
            if not main_collection:
                return ""
            
            # Query 1: Buscar por nome do ficheiro
            query_text = f"file:{filename} {file_change.filename}"
            
            results = main_collection.query(
                query_texts=[query_text],
                n_results=5,
                include=["documents", "metadatas", "distances"]
            )
            
            # Se não encontrou nada relevante, tentar query genérica
            if not results["documents"][0] or results["distances"][0][0] > 1.5:
                query_text = f"code similar to {filename}"
                results = main_collection.query(
                    query_texts=[query_text],
                    n_results=3,
                    include=["documents", "metadatas", "distances"]
                )
            
            # Formatar contexto
            if not results["documents"][0]:
                return ""
            
            sections = []
            
            # Processar resultados
            for doc, meta, dist in zip(
                results["documents"][0][:3],  # Max 3 resultados
                results["metadatas"][0][:3],
                results["distances"][0][:3]
            ):
                # Só adicionar se relevante (distância < 1.5)
                if dist > 1.5:
                    continue
                
                # Extrair info do metadata
                file_path = meta.get("file", meta.get("path", "unknown"))
                content_preview = doc[:200] if len(doc) > 200 else doc
                
                sections.append(f"- `{file_path}`:\n  ```\n  {content_preview}...\n  ```")
            
            if sections:
                context_text = "\n".join(sections)
                return f"""
## 🗂️ CONTEXTO DA APLICAÇÃO

### 📁 Código Relacionado
{context_text}

**⚠️ IMPORTANTE:** Usa este contexto para:
- Verificar consistência com código existente
- Sugerir padrões já usados na aplicação
- Identificar duplicação ou inconsistências
"""
            
            return ""
            
        except Exception as e:
            print(f"    ⚠️ RAG context error: {e}")
            return ""
    
    def _parse_ai_response(self, response: str, file_change: FileChange) -> List[ReviewComment]:
        """
        Parse da resposta JSON do AI
        
        Args:
            response: String retornada pelo AI
            file_change: FileChange original
        
        Returns:
            Lista de ReviewComment objects
        """
        try:
            # Limpar markdown se existir
            response = response.strip()
            if response.startswith("```json"):
                response = response.split("```json")[1]
            if response.startswith("```"):
                response = response.split("```")[1]
            response = response.replace("```", "").strip()
            
            # Parse JSON
            data = json.loads(response)
            
            # Converter para ReviewComment objects
            comments = []
            for review in data.get("reviews", []):
                comment = create_review_comment(
                    file_path=file_change.filename,
                    line_number=review.get("line", 1),
                    category=review.get("category", "learning"),
                    severity=review.get("severity", "info"),
                    title=review.get("title", "Review Comment"),
                    content=review.get("content", "")
                )
                comments.append(comment)
            
            return comments
            
        except json.JSONDecodeError as e:
            print(f"    ⚠️ JSON parse error: {e}")
            print(f"    Response preview: {response[:200]}...")
            return []
        except Exception as e:
            print(f"    ⚠️ Parse error: {e}")
            return []
    
    @staticmethod
    def _detect_language(filename: str) -> str:
        """
        Detecta linguagem baseada na extensão
        
        Args:
            filename: Nome do ficheiro
        
        Returns:
            Nome da linguagem
        """
        ext = Path(filename).suffix
        
        lang_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "React/JavaScript",
            ".ts": "TypeScript",
            ".tsx": "React/TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP"
        }
        
        return lang_map.get(ext, "código")