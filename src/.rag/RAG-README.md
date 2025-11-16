# 🧠 RAG Database Builder

This folder contains everything needed to build a **RAG (Retrieval-Augmented Generation)** database for your codebase, enabling AI Code Review with context awareness.

---

## 📦 What's Inside

- **`build.py`** - Builds the complete RAG database from scratch
- **`update.py`** - Updates only changed files (incremental)
- **`codebase_rag.py`** - RAG system core (ChromaDB + embeddings)
- **`indexer.py`** - Code parsers (Python, TypeScript, TSX, JSX)
- **`requirements.txt`** - Python dependencies

---

## 🚀 Quick Start

### 1️⃣ **First Time Setup**

```bash
# Install dependencies
cd .rag
pip install -r requirements.txt

# Build the database (indexes entire codebase)
python build.py
```

This will:
- ✅ Create a virtual environment
- ✅ Install dependencies
- ✅ Index all `.py`, `.ts`, `.tsx`, `.js`, `.jsx` files
- ✅ Generate `chroma_db/` folder

### 2️⃣ **Commit to Git**

```bash
# Add the database to your repo
git add chroma_db/
git commit -m "🧠 Initialize RAG database"
git push
```

### 3️⃣ **Update After Changes**

```bash
# Automatically detects and updates only changed files
python .rag/update.py
```

Then commit again:
```bash
git add chroma_db/
git commit -m "🧠 Update RAG database"
git push
```

---

## 🔧 Advanced Usage

### **Full Rebuild**

To completely reset and rebuild:

```bash
python build.py --reset
```

### **View Statistics**

```bash
python build.py --stats
```

### **Manual File Update**

```bash
python update.py src/file1.py src/file2.ts
```

---

## 📊 What Gets Indexed

The RAG system indexes:

- **Files**: Complete file contents
- **Functions**: Individual functions/methods
- **Classes**: Class definitions
- **Components**: React/Vue components
- **Imports/Exports**: Dependency tracking

**Supported Languages:**
- 🐍 Python (`.py`)
- 📘 TypeScript (`.ts`, `.tsx`)
- 🟨 JavaScript (`.js`, `.jsx`)

---

## 🚫 What Gets Ignored

These folders/files are automatically skipped:

```
node_modules/
dist/
build/
.git/
__pycache__/
.next/
.nuxt/
venv/
coverage/
chroma_db/
.rag/
```

---

## 🔍 How It Works

1. **Parsing**: Extracts functions, classes, imports from code
2. **Embedding**: Converts code to vector representations
3. **Storage**: Saves in ChromaDB for fast retrieval
4. **Retrieval**: AI Code Reviewer queries relevant context during review

---

## 💾 Database Size

Typical sizes:
- Small project (10-50 files): ~5-10 MB
- Medium project (50-200 files): ~20-50 MB
- Large project (200+ files): ~50-200 MB

---

## ⚠️ Important Notes

### **Windows Users**
The scripts work on Windows! Encoding is handled automatically.

### **Git LFS** (Optional)
If your database exceeds 100MB, consider using Git LFS:

```bash
git lfs track "chroma_db/**"
git add .gitattributes
```

### **GitHub Actions**
The AI Code Reviewer action will automatically use the `chroma_db/` from your repo - no need to rebuild in CI!

---

## 🐛 Troubleshooting

### "Failed to load embedding model"
```bash
# Reinstall dependencies
pip install --force-reinstall sentence-transformers
```

### "Database not found"
```bash
# Build it first
python .rag/build.py
```

### "Virtual environment not found"
```bash
# Remove and rebuild
rm -rf .rag/venv
python .rag/build.py
```

---

## 📚 More Info

For details on how AI Code Review uses the RAG database, see the main [README.md](../README.md).

---

**Built with ❤️ for better code reviews**