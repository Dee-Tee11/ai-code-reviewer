#!/usr/bin/env python3
"""
AI Service
Interface com modelo AI (HuggingFace) + RAG opcional para code review educativo
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Dict

from huggingface_hub import InferenceClient

from src.models.review_models import FileChange, ReviewComment, create_review_comment


class AIServiceError(Exception):
    """Exceção para erros do AI Service"""
    pass


class AIService:
    """
    Serviço de AI para code review educativo
    
    Responsabilidades:
    - Comunicar com modelo AI (HuggingFace)
    - Construir prompts educativos
    - Integrar contexto RAG (se disponível)
    - Parsear respostas do AI
    """
    
    DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
    DEFAULT_MAX_TOKENS = 2000
    DEFAULT_TEMPERATURE = 0.7
    
    def __init__(self, 
                 token: str, 
                 config: Dict,
                 rag_system = None,  # Optional[CodebaseRAG]
                 model: str = None):
        """
        Inicializa o serviço AI
        
        Args:
            token: HuggingFace API token
            config: Configuração completa (do ConfigService)
            rag_system: Sistema RAG opcional
            model: Nome do modelo (default: Llama-3.3-70B)
        
        Raises:
            AIServiceError: Se token inválido ou erro na inicialização
        """
        if not token:
            raise AIServiceError("HuggingFace token is required")
        
        self.config = config
        self.rag = rag_system
        self.model = model or self.DEFAULT_MODEL
        
        try:
            self.client = InferenceClient(token=token)
        except Exception as e:
            raise AIServiceError(f"Failed to initialize HuggingFace client: {e}")
        
        # Carregar system prompt
        self.system_prompt = self._load_system_prompt()
        
        print(f"  🤖 AI Service initialized with model: {self.model}")
        if self.rag:
            print("  🧠 RAG context available")
    
    def _load_system_prompt(self) -> str:
        """
        Carrega o system prompt do ficheiro
        
        Returns:
            String com system prompt
        
        Raises:
            AIServiceError: Se ficheiro não existir
        """
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "system_prompt.txt"
        
        if not prompt_path.exists():
            raise AIServiceError(f"System prompt not found at {prompt_path}")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise AIServiceError(f"Failed to load system prompt: {e}")
    
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
            # Chamar API do HuggingFace
            response = self.client.chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.DEFAULT_MAX_TOKENS,
                temperature=self.DEFAULT_TEMPERATURE
            )
            
            # Parse da resposta
            response_text = response.choices[0].message.content
            comments = self._parse_ai_response(response_text, file_change)
            
            print(f"    ✅ Found {len(comments)} issues")
            return comments
            
        except Exception as e:
            print(f"    ⚠️ AI error: {e}")
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
Retorna **JSON** com este formato EXATO:

```json
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
```

**IMPORTANTE:**
- Retorna APENAS o JSON, sem explicações extra
- Máximo 5 reviews por ficheiro
- Prioriza: critical > error > warning > info
- Usa português de Portugal (pt-PT)
- Inclui emojis relevantes (🤔💡📚🔍✅❌🚀🔒)
"""
        
        if self.rag:
            prompt += "- **USA O CONTEXTO fornecido acima** para fazer reviews mais inteligentes e consistentes com o resto da aplicação\n"
        
        prompt += "\nAnalisa o código agora! 🎓\n"
        
        return prompt
    
    def _get_rag_context(self, file_change: FileChange) -> str:
        """
        Obtém contexto do RAG e formata para o prompt
        
        Args:
            file_change: FileChange object
        
        Returns:
            String formatada com contexto ou string vazia
        """
        try:
            context = self.rag.get_context(
                filepath=file_change.filename,
                patch=file_change.patch,
                top_k=3
            )
            
            if not context.has_context:
                return ""
            
            sections = []
            
            # Ficheiros similares
            if context.similar_files:
                files_str = "\n".join([
                    f"- `{f['path']}`: {f['content'][:150]}..."
                    for f in context.similar_files[:2]
                ])
                sections.append(f"### 📁 Ficheiros Similares\n{files_str}")
            
            # Funções relacionadas
            if context.related_functions:
                funcs_str = "\n".join([
                    f"- `{f['name']}` em `{f['path']}`:\n  ```\n  {f['content'][:200]}...\n  ```"
                    for f in context.related_functions[:2]
                ])
                sections.append(f"### ⚙️ Funções Relacionadas\n{funcs_str}")
            
            # Dependências
            if context.dependencies:
                imports = context.dependencies.get('imports', [])
                imported_by = context.dependencies.get('imported_by', [])
                
                deps_info = []
                if imports:
                    deps_info.append(f"**Importa:** {', '.join([f'`{i}`' for i in imports[:5]])}")
                if imported_by:
                    deps_info.append(f"**Importado por:** {', '.join([f'`{i}`' for i in imported_by[:5]])}")
                
                if deps_info:
                    sections.append(f"### 🔗 Dependências\n{chr(10).join(deps_info)}")
            
            if sections:
                return f"""
## 🗂️ CONTEXTO DA APLICAÇÃO

{chr(10).join(sections)}

**⚠️ IMPORTANTE:** Usa este contexto para:
- Verificar se o código está consistente com ficheiros similares
- Ver se usa corretamente as dependências
- Sugerir padrões já usados noutros locais da app
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