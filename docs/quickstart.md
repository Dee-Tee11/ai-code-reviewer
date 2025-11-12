🚀 Quick Start - AI Code Reviewer com RAG
Guia rápido para começar a usar o sistema em 5 minutos!

⚡ Setup Rápido

1. Instalar Dependências (2 min)
   bash
   pip install -r requirements.txt
2. Indexar Codebase (2 min)
   bash

# Opção A: Usando o helper script

chmod +x rag.sh
./rag.sh index-full

# Opção B: Comando direto

python indexer.py --repo /caminho/para/webapp --mode full 3. Testar (1 min)
bash

# Opção A: Helper script

./rag.sh test

# Opção B: Comando direto

python test_rag.py
✅ Pronto! O sistema está funcional.

📖 Uso Básico
Ver Estatísticas
bash
./rag.sh stats
Output esperado:

📊 Database Statistics:
Total files indexed: 83
Total functions/components: 245
Total dependencies tracked: 156
Database size: 8.34 MB
Procurar Contexto para um Ficheiro
bash
./rag.sh search src/components/UserProfile.tsx
Output:

🔍 Search Results for: src/components/UserProfile.tsx

📁 Similar Files (3):

1.  src/components/AdminProfile.tsx
2.  src/components/EmployeeCard.tsx
3.  src/pages/Profile.tsx

⚙️ Related Functions (3):

1.  getUserData in src/api/users.py
2.  useAuth in src/hooks/useAuth.ts
3.  formatUser in src/utils/format.ts

🔗 Dependencies:
Imports: react, axios, ./types/User
Imported by: src/pages/Profile.tsx, src/App.tsx
🔄 Workflow Automático

1. Commitar os Ficheiros
   bash
   git add .
   git commit -m "Add RAG system"
   git push origin main
2. Workflow Automático
   O workflow update-index.yml vai:

✅ Detectar ficheiros modificados
✅ Re-indexar apenas os modificados
✅ Commitar a BD atualizada 3. Fazer um PR de Teste
bash

# Criar branch

git checkout -b test/rag-review

# Modificar um ficheiro

echo "// test" >> src/components/UserProfile.tsx

# Commit e push

git add .
git commit -m "Test RAG review"
git push origin test/rag-review 4. Abrir PR e Ver Review
O AI Code Reviewer vai agora ter contexto completo!

🎯 Comandos Úteis
bash

# Ver ajuda

./rag.sh help

# Indexar ficheiros específicos

./rag.sh index-incremental src/api/users.py src/components/Header.tsx

# Reset completo (cuidado!)

./rag.sh reset
🐛 Troubleshooting Rápido
"chromadb not found"
bash
pip install chromadb sentence-transformers
"No files indexed"
bash
./rag.sh index-full
"RAG context empty"
Verifica se a BD tem dados: ./rag.sh stats
Se não, re-indexa: ./rag.sh index-full
Workflow não está a correr
Verifica .github/workflows/update-index.yml existe
Verifica permissões: Settings → Actions → General → Workflow permissions → Read and write
📊 Arquitetura (Resumida)
Commit novo
↓
reviewer.py detecta ficheiros modificados
↓
RAG busca contexto (3 níveis):
→ Ficheiros similares
→ Funções relacionadas  
 → Dependências diretas
↓
AI recebe: commit + contexto
↓
Review inteligente! 🎉
📚 Próximos Passos
✅ Concluído: Setup básico
📖 Ler: SETUP.md para detalhes avançados
🔧 Customizar: Ajustar top_k, adicionar mais parsers
🚀 Melhorar: Ver seção "Melhorias Futuras" no SETUP.md
💡 Dicas
BD pequena? Perfeito! Menos de 20MB é ideal
BD grande? Considera .gitignore chroma_db/ e usar artifacts
Slow reviews? Reduz top_k de 5 para 3 ou 2
Muitos ficheiros? Filtra por extensão ou diretório
🆘 Precisa de Ajuda?
Corre ./rag.sh test para diagnosticar
Verifica logs do workflow em Actions
Lê SETUP.md para troubleshooting detalhado
🎓 Enjoy your smart code reviews!
