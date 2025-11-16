#!/usr/bin/env python3
"""
Build RAG Database - Pure Python version
Funciona em Windows, Linux e Mac
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def print_banner(text):
    """Imprime banner bonito"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


def print_step(emoji, text):
    """Imprime passo com emoji"""
    print(f"{emoji} {text}")


def run_command(cmd, cwd=None):
    """Executa comando e mostra output"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            shell=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def main():
    """Main build process"""
    
    print_banner("🏗️ Building RAG Database for CinemaWebApp")
    
    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "chroma_db"
    venv_path = script_dir / "venv"
    
    print(f"📁 Project root: {project_root}")
    print(f"📁 Database path: {db_path}")
    
    # ─────────────────────────────────────────────────────────────
    # 🧹 Cleanup
    # ─────────────────────────────────────────────────────────────
    if db_path.exists():
        print_step("🗑️", "Removing existing database...")
        shutil.rmtree(db_path)
        print("   ✅ Removed")
    
    # ─────────────────────────────────────────────────────────────
    # 🐍 Python Environment
    # ─────────────────────────────────────────────────────────────
    print_step("🐍", "Setting up Python environment...")
    
    # Check if venv exists
    if not venv_path.exists():
        print("   📦 Creating virtual environment...")
        if not run_command(f"python -m venv {venv_path}"):
            print("❌ Failed to create virtual environment")
            return False
        print("   ✅ Virtual environment created")
    else:
        print("   ✅ Virtual environment already exists")
    
    # Determine pip path based on OS
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # Install dependencies
    print("\n   📦 Installing dependencies...")
    requirements_file = script_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        return False
    
    print("   (This may take a few minutes on first run...)")
    if not run_command(f'"{pip_path}" install -q --upgrade pip'):
        print("⚠️ Warning: Failed to upgrade pip, continuing anyway...")
    
    if not run_command(f'"{pip_path}" install -r "{requirements_file}"'):
        print("❌ Failed to install dependencies")
        return False
    
    print("   ✅ Dependencies installed")
    
    # ─────────────────────────────────────────────────────────────
    # 🔨 Build Database
    # ─────────────────────────────────────────────────────────────
    print_step("🔨", "Building database...\n")
    
    indexer_path = script_dir / "indexer.py"
    
    if not indexer_path.exists():
        print(f"❌ indexer.py not found at {indexer_path}")
        return False
    
    # Run indexer
    cmd = f'"{python_path}" "{indexer_path}" --root "{project_root}" --db "{db_path}" --verbose'
    
    if not run_command(cmd):
        print("\n❌ Failed to build database")
        return False
    
    # ─────────────────────────────────────────────────────────────
    # ✅ Success
    # ─────────────────────────────────────────────────────────────
    print_banner("✅ RAG Database built successfully!")
    
    print(f"📊 Database location: {db_path}")
    print()
    print("💡 Next steps:")
    print("   1. git add chroma_db/")
    print("   2. git commit -m '🧠 Initialize RAG database'")
    print("   3. git push")
    print()
    print("🔄 To update: python update.py")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)