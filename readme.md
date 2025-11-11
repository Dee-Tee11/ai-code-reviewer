2# 🎓 AI Code Mentor

> **Educational AI code reviewer that teaches through questions, not answers**

Um GitHub Action que usa **Inteligência Artificial** para fazer reviews educativas do teu código. Em vez de dar soluções prontas, usa o **Método Socrático** para te ensinar a pensar como um programador profissional.

---

## 🌟 Features

### 🎯 Modo Educativo
- ❓ **Perguntas Socráticas** - Faz perguntas que te levam à resposta
- 💡 **Pistas Progressivas** - Guia-te sem dar a solução completa
- 📚 **Conceitos, não código** - Ensina o "porquê", não só o "como"
- 🎓 **Aprendizagem ativa** - Tu pensas, não copias

### 🔍 Análise Inteligente
- ✅ Code quality & best practices
- 🐛 Bug detection
- 🔒 Security vulnerabilities
- 🚀 Performance optimization
- 🧹 Code smells & duplications

### ⚙️ Altamente Configurável
- 📊 **4 níveis de severidade** (Info → Warning → Error → Critical)
- 🎨 **Múltiplas linguagens** (TypeScript, JavaScript, Python, React)
- 🔧 **Override completo** - Adapta às tuas regras
- 🎭 **Tons diferentes** (Mentor, Teacher, Coach)

---

## 🚀 Quick Start

### 1️⃣ Adiciona o Action ao teu projeto

Cria `.github/workflows/code-review.yml`:

```yaml
name: AI Code Review

on:
  push:
    branches: ["**"]  # Todos os branches
  pull_request:
    branches: [main, develop]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      issues: write

    steps:
      - name: 🎓 AI Code Mentor Review
        uses: your-org/ai-code-mentor@v1
        with:
          huggingface_token: ${{ secrets.HUGGINGFACE_TOKEN }}
          severity_threshold: info  # info, warning, error, critical
          tone: mentor  # mentor, teacher, coach
```

### 2️⃣ Configura os Secrets

Vai a **Settings → Secrets → Actions** e adiciona:

```bash
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxx
```

> 🔑 Get your token: https://huggingface.co/settings/tokens

### 3️⃣ (Opcional) Personaliza as regras

Cria `.github/code-review-config.yaml`:

```yaml
educational_mode:
  teaching_style:
    use_socratic_method: true
    provide_hints: true
    
  tone:
    style: "mentor"
    encouraging: true
    language: "pt-PT"

code_quality:
  max_function_length: 50
  max_nested_depth: 4
  detect_duplicated_code: true

security:
  check_sql_injection: true
  check_xss: true
  check_hardcoded_secrets: true
```

### 4️⃣ Faz commit e vê a magia! ✨

```bash
git add .
git commit -m "feat: add new feature"
git push
```

O AI Code Mentor vai:
1. ✅ Analisar as tuas alterações
2. 🤔 Fazer perguntas educativas
3. 💡 Dar pistas progressivas
4. 💬 Comentar diretamente no commit/PR

---

## 📚 Como Funciona

### Método Socrático em Ação

Em vez de:
```diff
❌ "Muda `let` para `const` aqui"
```

Vais receber:
```markdown
🤔 **Pergunta:**
Por que usar `let` aqui se esta variável nunca é reatribuída?

💡 **Pistas:**
1. Pensa em mutabilidade vs imutabilidade
2. O que garante `const` que `let` não garante?
3. Que tipo de erros podes prevenir?

🔍 **Investiga:**
Diferença entre `let`, `const` e `var` em JavaScript
```

### 📊 Níveis de Severidade

| Nível | Quando usar | O que recebes |
|-------|-------------|---------------|
| **ℹ️ Info** | Sugestões de melhoria | Só pergunta reflexiva |
| **⚠️ Warning** | Problemas de qualidade | Pergunta + pistas |
| **❌ Error** | Bugs potenciais | Pergunta + explicação conceptual |
| **🚨 Critical** | Segurança/Estabilidade | Resposta completa + explicação |

---

## ⚙️ Configuration Options

### Inputs do Action

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `huggingface_token` | HuggingFace API token | - | ✅ Yes |
| `config_file` | Path para config custom | `.github/code-review-config.yaml` | ❌ No |
| `severity_threshold` | Severidade mínima | `info` | ❌ No |
| `tone` | Tom do mentor | `mentor` | ❌ No |
| `skip_patterns` | Patterns para skip | `[skip-review]` | ❌ No |

### Severity Thresholds

```yaml
# Mostra TUDO (learning mode)
severity_threshold: info

# Só problemas importantes
severity_threshold: warning

# Só bugs e segurança
severity_threshold: error

# Apenas segurança crítica
severity_threshold: critical
```

### Tones Disponíveis

```yaml
# 🎓 Mentor (padrão) - Paciente, usa analogias
tone: mentor

# 👨‍🏫 Teacher - Mais formal, estruturado
tone: teacher

# 💪 Coach - Motivacional, desafiante
tone: coach

# 🤝 Friendly - Casual, coloquial
tone: friendly
```

---

## 🔧 Advanced Configuration

### Configuração Completa (exemplo)

```yaml
# .github/code-review-config.yaml

educational_mode:
  enabled: true
  
  help_levels:
    info: 1      # Só pergunta
    warning: 2   # Pergunta + pistas
    error: 3     # Pergunta + explicação
    critical: 4  # Resposta completa
  
  teaching_style:
    use_socratic_method: true
    provide_hints: true
    include_resources: true
    encourage_research: true
  
  tone:
    style: "mentor"
    encouraging: true
    patient: true
    use_emojis: true
    language: "pt-PT"

code_quality:
  max_function_length: 50
  max_function_complexity: 10
  max_nested_depth: 4
  
  detect_duplicated_code: true
  detect_dead_code: true
  detect_unused_variables: true
  detect_magic_numbers: true

security:
  check_sql_injection: true
  check_xss: true
  check_hardcoded_secrets: true
  check_unsafe_eval: true

performance:
  check_n_plus_one: true
  check_unnecessary_loops: true
  check_memory_leaks: true
  suggest_memoization: true

react:
  check_hooks_rules: true
  require_key_prop: true
  check_useEffect_dependencies: true

typescript:
  enforce_types: true
  check_null_safety: true

behavior:
  max_files_per_commit: 20
  max_comments_per_commit: 10
  group_similar_issues: true
  
  skip_commit_messages:
    - "[skip-review]"
    - "[no-review]"
    - "WIP:"
    - "Merge"
```

### Skip Patterns

```bash
# Skip específico
git commit -m "[skip-review] Quick fix"

# Work in progress
git commit -m "WIP: Still working on this"

# Merge commits (skip automático)
git merge feature/branch
```

---

## 🎯 Use Cases

### 🎓 Para Estudantes
```yaml
severity_threshold: info  # Mostra tudo
tone: mentor             # Paciente e encorajador
```

### 👨‍💼 Para Teams Profissionais
```yaml
severity_threshold: warning  # Só problemas relevantes
tone: coach                  # Direto mas motivacional
```

### 🔒 Para Security-First Projects
```yaml
severity_threshold: error   # Bugs e segurança
check_sql_injection: true
check_xss: true
```

---

## 📖 Examples

### Exemplo 1: Security Issue (Critical)

**Código:**
```python
query = f"SELECT * FROM users WHERE id = {user_input}"
cursor.execute(query)
```

**Review:**
```markdown
🚨 **SEGURANÇA CRÍTICA: SQL Injection Vulnerability**

⚠️ **GRAVIDADE:**
Este código permite que um atacante execute comandos SQL arbitrários.
Pode ler, modificar ou apagar TODA a base de dados.

📖 **Explicação:**
Quando concatenas input do utilizador diretamente numa query...
[explicação completa]

❌ **Problema no teu código:**
[código problemático]

✅ **Solução correta:**
[código corrigido]

📚 **Por que isto é importante:**
[conceito de segurança]

🔍 **Aprende mais:**
- OWASP SQL Injection
- Parameterized Queries
```

### Exemplo 2: Performance (Warning)

**Código:**
```javascript
users.map(u => u.id).filter(id => id > 100)
```

**Review:**
```markdown
🚀 **PERFORMANCE: Loop desnecessário**
**Severidade:** ⚠️ WARNING

🤔 **Pergunta:**
Consegues otimizar isto para fazer apenas um loop em vez de dois?

💡 **Pistas:**
1. O `map` percorre TODOS os users
2. Depois o `filter` percorre TODOS os IDs
3. Existe uma função que faz ambos ao mesmo tempo?

🔍 **Investiga:**
Diferença entre `map().filter()` e `reduce()` ou `flatMap()`
```

---

## 🛠️ Development

### Setup Local

```bash
# Clone
git clone https://github.com/your-org/ai-code-mentor
cd ai-code-mentor

# Install dependencies
pip install -r requirements.txt

# Set env vars
export HUGGINGFACE_TOKEN=hf_xxxxx
export GITHUB_TOKEN=ghp_xxxxx
export GITHUB_REPOSITORY=owner/repo
export GITHUB_SHA=abc123

# Test
python reviewer.py
```

### Estrutura do Projeto

```
ai-code-mentor/
├── action.yml                    # GitHub Action config
├── reviewer.py                   # Main script
├── config.yaml                   # Default configuration
├── requirements.txt              # Python dependencies
├── prompts/
│   ├── system_prompt.txt        # AI mentor instructions
│   └── review_template.txt      # Comment template
├── .github/
│   └── workflows/
│       └── test.yml             # Self-test workflow
└── README.md                     # Documentation
```

---

## 🤝 Contributing

Contribuições são bem-vindas! 🎉

### Como contribuir:
1. 🍴 Fork o projeto
2. 🌱 Cria uma branch (`git checkout -b feature/amazing`)
3. 💻 Faz as alterações
4. ✅ Testa localmente
5. 📝 Commit (`git commit -m 'feat: add amazing feature'`)
6. 🚀 Push (`git push origin feature/amazing`)
7. 🎯 Abre um Pull Request

---

## 📝 License

MIT License - vê [LICENSE](LICENSE) para detalhes.

---

## 🙏 Credits

Criado com ❤️ usando:
- 🤖 [HuggingFace](https://huggingface.co) - AI models
- 🐙 [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API
- 🎓 Socratic Method - Ensino por perguntas

---

## 💬 Support

Tens dúvidas? Problemas? Sugestões?

- 📖 Lê a [documentação completa](docs/)
- 🐛 Reporta [issues](https://github.com/your-org/ai-code-mentor/issues)
- 💬 Discussões no [Discussions](https://github.com/your-org/ai-code-mentor/discussions)

---

<div align="center">

**🎓 Aprende codificando. Codifica aprendendo. 💻**

[Get Started](#-quick-start) • [Documentation](docs/) • [Examples](#-examples)

</div>