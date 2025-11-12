🚀 AI Code Reviewer com RAG - Setup
Este guia explica como configurar o sistema RAG para o AI Code Reviewer.

📋 Pré-requisitos
Python 3.11+
GitHub Actions habilitado no repositório
Tokens necessários configurados
🔧 Setup Inicial

1. Instalar Dependências
   bash
   pip install -r requirements.txt
2. Criar Indexação Inicial
   Localmente (para testar):

bash

# Indexação completa da webapp

python indexer.py --repo /caminho/para/webapp --mode full

# Ver estatísticas

python -c "
from codebase_rag import CodebaseRAG
rag = CodebaseRAG()
print(rag.get_stats())
"
No GitHub Actions:

Faz push do código para main
Workflow update-index.yml corre automaticamente
Base de dados é commitada no repo 3. Testar RAG
python
from codebase_rag import CodebaseRAG

# Inicializar

rag = CodebaseRAG(persist_directory="./chroma_db")

# Buscar contexto para um ficheiro

context = rag.get_context(
filepath="src/components/UserProfile.tsx",
patch="... código modificado ...",
top_k=5
)

# Ver resultados

print(f"Ficheiros similares: {len(context.similar_files)}")
print(f"Funções relacionadas: {len(context.related_functions)}")
print(f"Dependências: {context.dependencies}")
⚙️ Configuração do Workflow
Variáveis de Ambiente
Adiciona no workflow de code review (.github/workflows/code-review.yml):

yaml
env:
ENABLE_RAG: "true" # Ativar RAG
RAG_DB_PATH: "./chroma_db" # Caminho da BD
Desativar RAG (temporariamente)
yaml
env:
ENABLE_RAG: "false"
🔄 Modos de Atualização

1. Automático (Incremental)
   Corre em cada push para main
   Só re-indexa ficheiros modificados
   Rápido (~30 segundos)
2. Manual (Full)
   Vai a Actions → Update RAG Index → Run workflow
   Escolhe "full" como modo
   Re-indexa tudo do zero
3. Agendado (Full)
   Corre toda segunda-feira às 3h UTC
   Garante que índice está sincronizado
   📊 Estrutura da Base de Dados
   chroma_db/
   ├── chroma.sqlite3 # Base de dados SQLite
   ├── dependencies.json # Grafo de dependências
   └── [UUID folders] # Embeddings e metadados
   Tamanho esperado: ~5-10MB para 83 ficheiros

🎯 Como Funciona
Quando há um PR/Commit:
Reviewer detecta ficheiros modificados
RAG busca contexto:
Ficheiros similares (top 3)
Funções relacionadas (top 3)
Dependências diretas (imports/exports)
AI recebe:
Diff do commit
Contexto relevante do RAG
Review é mais inteligente!
Exemplo de Contexto:
📁 Ficheiros Similares:

- src/components/AdminProfile.tsx (padrão similar)
- src/components/EmployeeCard.tsx (usa mesmo hook)

⚙️ Funções Relacionadas:

- getUserData() em src/api/users.py
- useAuth() em src/hooks/useAuth.ts

🔗 Dependências:
Importa: react, axios, ./types/User
Importado por: src/pages/Profile.tsx, src/App.tsx
🐛 Troubleshooting
RAG não está a funcionar
Verificar se BD existe:
bash
ls -lh chroma_db/
Verificar logs do workflow:
Actions → Update RAG Index → Ver logs
Forçar re-indexação:
bash
python indexer.py --repo . --mode full --reset
BD muito grande
Se a BD ultrapassar 50MB:

Considerar .gitignore chroma_db/
Usar GitHub Releases para armazenar
Ou usar Pinecone (cloud, mas pago)
Performance lenta
Reduzir top_k em reviewer.py:
python
context = rag.get_context(filepath, patch, top_k=2) # Era 3
Limitar tamanho dos chunks em indexer.py
📈 Melhorias Futuras
Suporte para mais linguagens (Java, Go, Rust)
Cache de contexto para ficheiros frequentes
Análise de impacto de mudanças
Sugestões de refactoring baseadas em padrões
Integração com CI/CD metrics
🤝 Contribuir
Para melhorar o sistema RAG:

Fork o repo
Cria branch: git checkout -b feature/melhoria-rag
Commit: git commit -m 'Adiciona feature X'
Push: git push origin feature/melhoria-rag
Abre PR
📚 Recursos
ChromaDB Docs
Sentence Transformers
RAG Overview
🎓 Happy Reviewing with Context!
