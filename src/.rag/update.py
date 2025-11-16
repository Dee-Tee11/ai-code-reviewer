#!/usr/bin/env python3
"""
Update RAG Database - Pure Python version
Atualiza apenas ficheiros modificados
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path


def print_banner(text):
    """Imprime banner bonito"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


def print_step(emoji, text):
    """Imprime passo com emoji"""
    print(f"{emoji} {text}")


def run_command(cmd, cwd=None, capture=True):
    """Executa comando e retorna output"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=capture,
            text=True,
            shell=True
        )
        return result.stdout if capture else None
    except subprocess.CalledProcessError as e:
        if capture:
            print(f"❌ Error: {e}")
            if e.stderr:
                print(e.stderr)
        return None


def get_changed_files(project_root):
    """Detecta ficheiros modificados usando git"""
    
    # Git diff (staged + unstaged)
    cmd = "git diff --name-only HEAD"
    output = run_command(cmd, cwd=project_root)
    
    changed_files = []
    
    if output:
        changed_files.extend([f.strip() for f in output.split('\n') if f.strip()])
    
    # Untracked files
    cmd = "git ls-files --others --exclude-standard"
    output = run_command(cmd, cwd=project_root)
    
    if output:
        changed_files.extend([f.strip() for f in output.split('\n') if f.strip()])
    
    return changed_files


def main():
    """Main update process"""
    
    print_banner("🔄 Updating RAG Database for CinemaWebApp")
    
    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "chroma_db"
    venv_path = script_dir / "venv"
    
    # ─────────────────────────────────────────────────────────────
    # ✅ Check Database Exists
    # ─────────────────────────────────────────────────────────────
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        print()
        print("💡 Run 'python build.py' first to create the database")
        return False
    
    # ─────────────────────────────────────────────────────────────
    # 🔍 Detect Changes
    # ─────────────────────────────────────────────────────────────
    print_step("🔍", "Detecting changes...")
    
    changed_files = get_changed_files(project_root)
    
    if not changed_files:
        print("✅ No changes detected")
        print()
        print("💡 Your RAG database is up to date!")
        return True
    
    # Filter for relevant extensions
    relevant_files = [
        f for f in changed_files
        if any(f.endswith(ext) for ext in ['.py', '.ts', '.tsx', '.jsx', '.js'])
    ]
    
    if not relevant_files:
        print("✅ No relevant code files changed")
        print()
        print("💡 Your RAG database is up to date!")
        return True
    
    print()
    print("📝 Changed files:")
    for file in relevant_files:
        print(f"   • {file}")
    
    # ─────────────────────────────────────────────────────────────
    # 🐍 Python Environment
    # ─────────────────────────────────────────────────────────────
    print()
    print_step("🐍", "Activating Python environment...")
    
    if not venv_path.exists():
        print("⚠️ Virtual environment not found")
        print("💡 Run 'python build.py' first")
        return False
    
    # Determine python path based on OS
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"
    
    if not python_path.exists():
        print(f"❌ Python not found at {python_path}")
        return False
    
    print("   ✅ Environment ready")
    
    # ─────────────────────────────────────────────────────────────
    # 🔄 Update Database
    # ─────────────────────────────────────────────────────────────
    print()
    print_step("🔄", "Updating database...\n")
    
    indexer_path = script_dir / "indexer.py"
    
    if not indexer_path.exists():
        print(f"❌ indexer.py not found at {indexer_path}")
        return False
    
    # Create temp file with changed files
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('\n'.join(relevant_files))
        temp_file = f.name
    
    try:
        # Run indexer in update mode
        cmd = f'"{python_path}" "{indexer_path}" --root "{project_root}" --db "{db_path}" --update --files "{temp_file}" --verbose'
        
        if not run_command(cmd, capture=False):
            print("\n❌ Failed to update database")
            return False
    finally:
        # Cleanup temp file
        try:
            os.unlink(temp_file)
        except:
            pass
    
    # ─────────────────────────────────────────────────────────────
    # ✅ Success
    # ─────────────────────────────────────────────────────────────
    print_banner("✅ RAG Database updated successfully!")
    
    print("💡 Next steps:")
    print("   1. git add chroma_db/")
    print("   2. git commit -m '🧠 Update RAG database'")
    print("   3. git push")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Update cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)