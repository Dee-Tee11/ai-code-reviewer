#!/usr/bin/env python3
"""
AI Code Mentor - Educational Code Reviewer
Usa Socratic Method para ensinar, não dar respostas prontas
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
# 🤖 AI MENTOR
# ═══════════════════════════════════════════════════════════

class AIMentor:
    """Interface com o modelo AI (HuggingFace)"""
    
    def __init__(self, token: str, config: Dict):
        self.client = InferenceClient(token=token)
        self.config = config
        self.system_prompt = self._load_system_prompt()
        
        # Modelo: usar o melhor disponível no HF
        self.model = "meta-llama/Llama-3.3-70B-Instruct"  # ou "mistralai/Mixtral-8x7B-Instruct-v0.1"
    
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
        """Constrói o prompt específico para este ficheiro"""
        
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

Analisa o código agora! 🎓
"""
        return prompt
    
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
# 🐙 GITHUB HANDLER
# ═══════════════════════════════════════════════════════════

class GitHubHandler:
    """Gere interação com GitHub (commits, comments)"""
    
    def __init__(self, token: str):
        self.github = Github(auth=Auth.Token(token))
        self.repo = self._get_repo()
        token = os.environ.get('GITHUB_TOKEN')
        if not token:
            print("❌ GITHUB_TOKEN não encontrado!")
            exit(1)
        self.github = Github(auth=Auth.Token(token))
    
    def _get_repo(self):
        """Obtém o repositório atual"""
        repo_name = os.getenv("GITHUB_REPOSITORY")
        return self.github.get_repo(repo_name)
    
    def should_skip_review(self) -> bool:
        """Verifica se deve skip o review deste commit"""
        skip_patterns = os.getenv("SKIP_PATTERNS", "[skip-review],[no-review],WIP:").split(",")
        
        commit = self.repo.get_commit(self.commit_sha)
        message = commit.commit.message
        
        for pattern in skip_patterns:
            if pattern.strip() in message:
                print(f"⏭️ Skipping review (pattern: {pattern})")
                return True
        
        return False
    
    def get_changed_files(self) -> List[FileChange]:
        """Obtém ficheiros alterados no commit"""
        commit = self.repo.get_commit(self.commit_sha)
        
        changes = []
        for file in commit.files:
            # Skip ficheiros não relevantes
            if self._should_skip_file(file.filename):
                continue
            
            # Obter conteúdo completo se disponível
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
        """Verifica se deve skip este ficheiro"""
        skip_extensions = [".json", ".md", ".lock", ".min.js", ".bundle.js", ".map"]
        skip_dirs = ["node_modules", "dist", "build", ".git"]
        
        # Check extension
        if any(filename.endswith(ext) for ext in skip_extensions):
            return True
        
        # Check directory
        if any(dir in filename for dir in skip_dirs):
            return True
        
        return False
    
    def post_review_comments(self, comments: List[ReviewComment]):
        """Posta comentários no commit"""
        if not comments:
            print("✅ Nenhum comentário para postar")
            return
        
        commit = self.repo.get_commit(self.commit_sha)
        
        # Agrupar por severidade
        by_severity = {
            "critical": [],
            "error": [],
            "warning": [],
            "info": []
        }
        
        for comment in comments:
            by_severity[comment.severity].append(comment)
        
        # Postar comentários (prioridade: critical > error > warning > info)
        posted_count = 0
        max_comments = 10  # Limitar para não overwhelm
        
        for severity in ["critical", "error", "warning", "info"]:
            for comment in by_severity[severity]:
                if posted_count >= max_comments:
                    break
                
                try:
                    # Criar comentário no commit
                    commit.create_comment(
                        body=self._format_comment(comment),
                        path=comment.file_path,
                        position=comment.line_number
                    )
                    posted_count += 1
                    print(f"💬 Comentário postado: {comment.title}")
                    
                except Exception as e:
                    print(f"⚠️ Erro ao postar comentário: {e}")
        
        # Resumo final
        if posted_count < len(comments):
            remaining = len(comments) - posted_count
            summary = self._create_summary(comments, remaining)
            commit.create_comment(body=summary)
    
    def _format_comment(self, comment: ReviewComment) -> str:
        """Formata o comentário para GitHub"""
        severity_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨"
        }
        
        return f"""### {comment.emoji} {comment.title}
**Severidade:** {severity_emoji.get(comment.severity, "💡")} {comment.severity.upper()}

{comment.content}

---
*🤖 AI Code Mentor - Review Educativo*
"""
    
    def _create_summary(self, all_comments: List[ReviewComment], remaining: int) -> str:
        """Cria resumo quando há muitos comentários"""
        return f"""## 📊 Resumo da Review

Foram encontrados **{len(all_comments)} pontos** para melhorar:

- 🚨 **Critical:** {len([c for c in all_comments if c.severity == 'critical'])}
- ❌ **Errors:** {len([c for c in all_comments if c.severity == 'error'])}
- ⚠️ **Warnings:** {len([c for c in all_comments if c.severity == 'warning'])}
- ℹ️ **Info:** {len([c for c in all_comments if c.severity == 'info'])}

Os {remaining} comentários restantes não foram mostrados para não overwhelm.
Prioriza os problemas críticos e erros primeiro! 🎯

---
*🤖 AI Code Mentor - Foca nos problemas mais importantes primeiro!*
"""

# ═══════════════════════════════════════════════════════════
# 🚀 MAIN
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
    
    # 3. Inicializar handlers
    print("🤖 Initializing AI Mentor...")
    mentor = AIMentor(hf_token, config)
    
    print("🐙 Connecting to GitHub...")
    github = GitHubHandler(gh_token)
    
    # 4. Verificar se deve skip
    if github.should_skip_review():
        print("✅ Review skipped")
        sys.exit(0)
    
    # 5. Obter ficheiros alterados
    print("📁 Getting changed files...")
    changed_files = github.get_changed_files()
    
    if not changed_files:
        print("✅ No files to review")
        sys.exit(0)
    
    print(f"📝 Found {len(changed_files)} files to review")
    
    # 6. Fazer review de cada ficheiro
    all_comments = []
    
    for file_change in changed_files:
        print(f"🔍 Reviewing {file_change.filename}...")
        
        comments = mentor.review_code(file_change)
        all_comments.extend(comments)
        
        print(f"  └─ Found {len(comments)} issues")
    
    # 7. Postar comentários
    print(f"\n💬 Posting {len(all_comments)} comments...")
    github.post_review_comments(all_comments)
    
    print("\n✅ Review completed!")
    print(f"📊 Total issues found: {len(all_comments)}")

if __name__ == "__main__":
    main()