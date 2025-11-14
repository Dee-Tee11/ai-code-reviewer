#!/usr/bin/env python3
"""
AI Code Mentor - Educational Code Reviewer
Usa Socratic Method para ensinar, não dar respostas prontas
COM RAG OPCIONAL: Contexto completo da aplicação (se disponível)
"""

import os
import sys
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from github import Github, Auth
from huggingface_hub import InferenceClient

# Importar sistema RAG
from codebase_rag import CodebaseRAG, RetrievalContext

# Pegar token do ambiente ou input
github_token = os.environ.get('INPUT_GITHUB_TOKEN') or os.environ.get('GITHUB_TOKEN')

# ═══════════════════════════════════════════════════════════
# 📋 DATA CLASSES
# ═══════════════════════════════════════════════════════════

@dataclass
class ReviewComment:
    """Representa um comentário de review"""
    file_path: str
    line_number: int
    category: str
    severity: str  # info, warning, error, critical
    title: str
    content: str
    emoji: str

@dataclass
class FileChange:
    """Representa uma alteração num ficheiro"""
    filename: str
    status: str  # added, modified, deleted
    additions: int
    deletions: int
    changes: int
    patch: Optional[str]
    content: Optional[str]

# ═══════════════════════════════════════════════════════════
# 🔧 CONFIGURATION LOADER
# ═══════════════════════════════════════════════════════════

class ConfigLoader:
    """Carrega e faz merge da configuração padrão + custom"""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
    
    @staticmethod
    def load() -> Dict:
        """Carrega configuração com fallback para defaults"""
        # 1. Carregar config padrão
        with open(ConfigLoader.DEFAULT_CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        
        # 2. Tentar carregar config custom do projeto
        custom_config_path = os.getenv("CONFIG_FILE", ".github/code-review-config.yaml")
        if os.path.exists(custom_config_path):
            with open(custom_config_path) as f:
                custom_config = yaml.safe_load(f)
                config = ConfigLoader._deep_merge(config, custom_config)
        
        # 3. Override com env vars
        if os.getenv("SEVERITY_THRESHOLD"):
            config["behavior"]["severity_threshold"] = os.getenv("SEVERITY_THRESHOLD")
        
        if os.getenv("TONE"):
            config["educational_mode"]["tone"]["style"] = os.getenv("TONE")
        
        return config
    
    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """Merge recursivo de dicts"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

# ═══════════════════════════════════════════════════════════
# 🤖 AI MENTOR (COM RAG OPCIONAL!)
# ═══════════════════════════════════════════════════════════

class AIMentor:
    """Interface com o modelo AI (HuggingFace) + RAG opcional"""
    
    def __init__(self, token: str, config: Dict, rag: Optional[CodebaseRAG] = None):
        self.client = InferenceClient(token=token)
        self.config = config
        self.system_prompt = self._load_system_prompt()
        self.rag = rag  # Sistema RAG (opcional)
        
        # Modelo: usar o melhor disponível no HF
        self.model = "meta-llama/Llama-3.3-70B-Instruct"
    
    def _load_system_prompt(self) -> str:
        """Carrega o system prompt do ficheiro"""
        prompt_path = Path(__file__).parent / "prompts" / "system_prompt.txt"
        with open(prompt_path) as f:
            return f.read()
    
    def review_code(self, file_change: FileChange) -> List[ReviewComment]:
        """Pede ao AI para fazer review educativo do código"""
        
        # Criar prompt específico para este ficheiro
        prompt = self._build_review_prompt(file_change)
        
        try:
            # Chamar API do HuggingFace
            response = self.client.chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            # Parse da resposta
            response_text = response.choices[0].message.content
            comments = self._parse_ai_response(response_text, file_change)
            
            return comments
            
        except Exception as e:
            print(f"⚠️ Erro ao chamar AI: {e}")
            return []
    
    def _build_review_prompt(self, file_change: FileChange) -> str:
        """Constrói o prompt específico para este ficheiro (COM RAG SE DISPONÍVEL!)"""
        
        # Detectar linguagem
        ext = Path(file_change.filename).suffix
        lang_map = {
            ".py": "Python",
            ".js": "JavaScript", 
            ".jsx": "React/JavaScript",
            ".ts": "TypeScript",
            ".tsx": "React/TypeScript"
        }
        language = lang_map.get(ext, "código")
        
        # BASE DO PROMPT
        prompt = f"""
# 📝 TAREFA: Review Educativo de Código

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

        # ═══════════════════════════════════════════════════════
        # 🆕 ADICIONAR CONTEXTO DO RAG (SE DISPONÍVEL)
        # ═══════════════════════════════════════════════════════
        
        if self.rag:
            try:
                print(f"  🧠 Fetching RAG context for {file_change.filename}...")
                context = self.rag.get_context(
                    filepath=file_change.filename,
                    patch=file_change.patch,
                    top_k=3  # Top 3 resultados por categoria
                )
                
                # Adicionar contexto ao prompt
                rag_context = self._format_rag_context(context)
                if rag_context:
                    prompt += f"\n{rag_context}\n"
                    print(f"  ✅ RAG context added ({len(context.similar_files)} similar files, {len(context.related_functions)} functions)")
                else:
                    print(f"  ℹ️ No relevant context found in RAG")
                    
            except Exception as e:
                print(f"  ⚠️ Error fetching RAG context: {e}")
        
        # CONTINUAR COM O PROMPT NORMAL
        prompt += f"""
## 💻 CÓDIGO ALTERADO
```{language.lower()}
{file_change.patch or file_change.content or "Sem alterações visíveis"}
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
        
        # Adicionar nota sobre RAG se estiver ativo
        if self.rag:
            prompt += "- **USA O CONTEXTO fornecido acima** para fazer reviews mais inteligentes e consistentes com o resto da aplicação\n"
        
        prompt += "\nAnalisa o código agora! 🎓\n"
        
        return prompt
    
    def _format_rag_context(self, context: RetrievalContext) -> str:
        """Formata o contexto do RAG para incluir no prompt"""
        sections = []
        
        # 1. Ficheiros similares
        if context.similar_files:
            files_str = "\n".join([
                f"- `{f['path']}`: {f['content'][:150]}..."
                for f in context.similar_files[:2]  # Só os top 2
            ])
            sections.append(f"""
### 📁 Ficheiros Similares na Aplicação
{files_str}
""")
        
        # 2. Funções relacionadas
        if context.related_functions:
            funcs_str = "\n".join([
                f"- `{f['name']}` em `{f['path']}`:\n  ```\n  {f['content'][:200]}...\n  ```"
                for f in context.related_functions[:2]  # Só os top 2
            ])
            sections.append(f"""
### ⚙️ Funções/Componentes Relacionados
{funcs_str}
""")
        
        # 3. Dependências
        if context.dependencies:
            imports = context.dependencies.get('imports', [])
            imported_by = context.dependencies.get('imported_by', [])
            
            deps_info = []
            if imports:
                deps_info.append(f"**Importa:** {', '.join([f'`{i}`' for i in imports[:5]])}")
            if imported_by:
                deps_info.append(f"**Importado por:** {', '.join([f'`{i}`' for i in imported_by[:5]])}")
            
            if deps_info:
                sections.append(f"""
### 🔗 Dependências
{chr(10).join(deps_info)}
""")
        
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
    
    def _parse_ai_response(self, response: str, file_change: FileChange) -> List[ReviewComment]:
        """Parse da resposta JSON do AI"""
        try:
            # Remover markdown se existir
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
                comment = ReviewComment(
                    file_path=file_change.filename,
                    line_number=review.get("line", 1),
                    category=review.get("category", "learning"),
                    severity=review.get("severity", "info"),
                    title=review.get("title", "Review Comment"),
                    content=review.get("content", ""),
                    emoji=self._get_emoji(review.get("category", "learning"))
                )
                comments.append(comment)
            
            return comments
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Erro ao fazer parse da resposta AI: {e}")
            print(f"Resposta recebida: {response[:200]}...")
            return []
    
    def _get_emoji(self, category: str) -> str:
        """Retorna emoji para a categoria"""
        emoji_map = {
            "learning": "🎓",
            "security": "🔒",
            "performance": "🚀",
            "best_practices": "✨",
            "bugs": "🐛",
            "maintainability": "🔧"
        }
        return emoji_map.get(category, "💡")

# ═══════════════════════════════════════════════════════════
# 🐙 GITHUB HANDLER (SEM MUDANÇAS)
# ═══════════════════════════════════════════════════════════
# [... código do GitHubHandler permanece igual ...]

class GitHubHandler:
    """Gere interação com GitHub (commits, comments)"""
    
    def __init__(self, token: str):
        if not token:
            print("❌ GITHUB_TOKEN não encontrado!")
            sys.exit(1)
        
        self.github = Github(auth=Auth.Token(token))
        self.repo = self._get_repo()
        self.commit_sha = os.getenv("GITHUB_SHA")
        if not self.commit_sha:
            print("❌ GITHUB_SHA não encontrado!")
            sys.exit(1)
        
        self.pr_number = self._get_pr_number()
        self.pull_request = None
        if self.pr_number:
            self.pull_request = self.repo.get_pull(self.pr_number)
    
    def _get_repo(self):
        repo_name = os.getenv("GITHUB_REPOSITORY")
        if not repo_name:
            print("❌ GITHUB_REPOSITORY não encontrado!")
            sys.exit(1)
        return self.github.get_repo(repo_name)
    
    def _get_pr_number(self) -> Optional[int]:
        github_ref = os.getenv("GITHUB_REF", "")
        if "pull" in github_ref:
            try:
                pr_num = int(github_ref.split("/")[2])
                print(f"📌 Detected PR #{pr_num}")
                return pr_num
            except (IndexError, ValueError):
                pass
        
        event_path = os.getenv("GITHUB_EVENT_PATH")
        if event_path and os.path.exists(event_path):
            try:
                with open(event_path) as f:
                    event = json.load(f)
                    if "pull_request" in event:
                        pr_num = event["pull_request"]["number"]
                        print(f"📌 Detected PR #{pr_num} from event")
                        return pr_num
            except:
                pass
        
        print("ℹ️ No PR detected, will use commit comments")
        return None
    
    def should_skip_review(self) -> bool:
        skip_patterns = os.getenv("SKIP_PATTERNS", "[skip-review],[no-review],WIP:").split(",")
        commit = self.repo.get_commit(self.commit_sha)
        message = commit.commit.message
        
        for pattern in skip_patterns:
            if pattern.strip() in message:
                print(f"⏭️ Skipping review (pattern: {pattern})")
                return True
        
        return False
    
    def get_changed_files(self) -> List[FileChange]:
        if self.pull_request:
            files = self.pull_request.get_files()
        else:
            commit = self.repo.get_commit(self.commit_sha)
            files = commit.files
        
        changes = []
        for file in files:
            if self._should_skip_file(file.filename):
                continue
            
            content = None
            if file.status != "deleted":
                try:
                    file_content = self.repo.get_contents(file.filename, ref=self.commit_sha)
                    content = file_content.decoded_content.decode('utf-8')
                except:
                    content = None
            
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
    
    def _should_skip_file(self, filename: str) -> bool:
        skip_extensions = [".json", ".md", ".lock", ".min.js", ".bundle.js", ".map"]
        skip_dirs = ["node_modules", "dist", "build", ".git"]
        
        if any(filename.endswith(ext) for ext in skip_extensions):
            return True
        
        if any(dir in filename for dir in skip_dirs):
            return True
        
        return False
    
    def post_review_comments(self, comments: List[ReviewComment]):
        if not comments:
            print("✅ Nenhum comentário para postar")
            return
        
        if self.pull_request:
            self._post_pr_review(comments)
        else:
            self._post_commit_comments(comments)
    
    # [... métodos de posting permanecem iguais ...]
    def _post_pr_review(self, comments):
        # Implementação existente
        pass
    
    def _post_commit_comments(self, comments):
        # Implementação existente
        pass
    
    def _format_comment(self, comment):
        # Implementação existente
        pass

# ═══════════════════════════════════════════════════════════
# 🚀 MAIN (ATUALIZADO - NÃO CONSTRÓI RAG!)
# ═══════════════════════════════════════════════════════════

def main():
    """Entry point do script"""
    print("🎓 AI Code Mentor - Starting review...")
    
    # 1. Carregar configuração
    print("📋 Loading configuration...")
    config = ConfigLoader.load()
    
    # 2. Verificar tokens
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    gh_token = os.getenv("GITHUB_TOKEN")
    
    if not hf_token:
        print("❌ HUGGINGFACE_TOKEN not found!")
        sys.exit(1)
    
    if not gh_token:
        print("❌ GITHUB_TOKEN not found!")
        sys.exit(1)
    
    # ═══════════════════════════════════════════════════════
    # 3. TENTAR CARREGAR RAG EXISTENTE (NÃO CONSTRÓI!)
    # ═══════════════════════════════════════════════════════
    rag = None
    enable_rag = os.getenv("ENABLE_RAG", "false").lower() == "true"
    
    if enable_rag:
        rag_db_path = os.getenv("RAG_DB_PATH", "./chroma_db")
        
        # Verificar se a BD existe
        if not Path(rag_db_path).exists():
            print(f"⚠️ RAG enabled but database not found at {rag_db_path}")
            print("💡 RAG will NOT be built automatically by this action.")
            print("📝 To enable RAG:")
            print("   1. Run locally: python .rag/build.py")
            print("   2. Commit: git add chroma_db/ && git commit -m '🧠 Add RAG database'")
            print("   3. Push: git push")
            print("\n⚡ Continuing review WITHOUT RAG context...\n")
        else:
            try:
                print(f"🧠 Loading existing RAG database from {rag_db_path}...")
                rag = CodebaseRAG(persist_directory=rag_db_path)
                stats = rag.get_stats()
                
                if stats['total_items'] == 0:
                    print("⚠️ RAG database is empty!")
                    print("💡 Run 'python .rag/build.py' locally to populate it")
                    rag = None
                else:
                    print(f"  ✅ RAG loaded successfully!")
                    print(f"     📊 {stats['total_files']} files")
                    print(f"     ⚙️ {stats['total_functions']} functions")
                    print(f"     🔗 {stats['total_dependencies']} dependencies")
                    
            except Exception as e:
                print(f"  ⚠️ RAG initialization failed: {e}")
                print("  ℹ️ Continuing without RAG context...")
                rag = None
    else:
        print("ℹ️ RAG disabled (enable_rag=false)")
    
    # 4. Inicializar AI Mentor (com ou sem RAG)
    print("🤖 Initializing AI Mentor...")
    mentor = AIMentor(hf_token, config, rag=rag)
    
    print("🐙 Connecting to GitHub...")
    github = GitHubHandler(gh_token)
    
    # 5. Verificar se deve skip
    if github.should_skip_review():
        print("✅ Review skipped")
        sys.exit(0)
    
    # 6. Obter ficheiros alterados
    print("📁 Getting changed files...")
    changed_files = github.get_changed_files()
    
    if not changed_files:
        print("✅ No files to review")
        sys.exit(0)
    
    print(f"📝 Found {len(changed_files)} files to review")
    
    # 7. Fazer review de cada ficheiro
    all_comments = []
    
    for file_change in changed_files:
        print(f"🔍 Reviewing {file_change.filename}...")
        
        comments = mentor.review_code(file_change)
        all_comments.extend(comments)
        
        print(f"  └─ Found {len(comments)} issues")
    
    # 8. Postar comentários
    print(f"\n💬 Posting {len(all_comments)} comments...")
    github.post_review_comments(all_comments)
    
    # 9. Resumo final
    print("\n" + "="*50)
    print("✅ Review completed!")
    print(f"📊 Total issues found: {len(all_comments)}")
    if rag:
        print("🧠 RAG context was used")
    else:
        print("ℹ️ Review done without RAG context")
    print("="*50)

if __name__ == "__main__":
    main()