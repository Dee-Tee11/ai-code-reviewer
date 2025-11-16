#!/usr/bin/env python3
"""
Configuration Service
Gere carregamento e merge de configurações (default + custom + env vars)
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigurationError(Exception):
    """Exceção para erros de configuração"""
    pass


class ConfigService:
    """
    Serviço de configuração com suporte a:
    - Config padrão (config.yaml)
    - Config custom do projeto (.github/code-review-config.yaml)
    - Override via environment variables
    """
    
    DEFAULT_CONFIG_FILENAME = "config.yaml"
    CUSTOM_CONFIG_DEFAULT_PATH = ".github/code-review-config.yaml"
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Inicializa o serviço de configuração
        
        Args:
            base_path: Caminho base para localizar config.yaml (default: diretório do script)
        """
        self.base_path = base_path or Path(__file__).parent.parent.parent
        self.config: Dict[str, Any] = {}
        self._loaded = False
    
    def load(self) -> Dict[str, Any]:
        """
        Carrega configuração completa com precedência:
        1. Config padrão (config.yaml)
        2. Config custom do projeto
        3. Environment variables
        
        Returns:
            Dicionário com configuração final
        
        Raises:
            ConfigurationError: Se config padrão não for encontrado
        """
        if self._loaded:
            return self.config
        
        # 1. Carregar config padrão
        self.config = self._load_default_config()
        
        # 2. Merge com config custom (se existir)
        custom_config = self._load_custom_config()
        if custom_config:
            self.config = self._deep_merge(self.config, custom_config)
            print("  ✅ Custom config loaded and merged")
        
        # 3. Override com environment variables
        self._apply_env_overrides()
        
        self._loaded = True
        return self.config
    
    def _load_default_config(self) -> Dict[str, Any]:
        """
        Carrega configuração padrão
        
        Returns:
            Dict com config padrão
        
        Raises:
            ConfigurationError: Se ficheiro não existir
        """
        config_path = self.base_path / self.DEFAULT_CONFIG_FILENAME
        
        if not config_path.exists():
            raise ConfigurationError(
                f"Default config not found at {config_path}"
            )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print(f"  ✅ Default config loaded from {config_path}")
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config: {e}")
    
    def _load_custom_config(self) -> Optional[Dict[str, Any]]:
        """
        Carrega configuração custom do projeto (opcional)
        
        Returns:
            Dict com config custom ou None se não existir
        """
        # Tentar ler path do env var primeiro
        custom_path_str = os.getenv("CONFIG_FILE", self.CUSTOM_CONFIG_DEFAULT_PATH)
        custom_path = Path(custom_path_str)
        
        if not custom_path.exists():
            print(f"  ℹ️ No custom config found at {custom_path} (using defaults)")
            return None
        
        try:
            with open(custom_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print(f"  📝 Custom config found at {custom_path}")
            return config
            
        except yaml.YAMLError as e:
            print(f"  ⚠️ Invalid YAML in custom config: {e}")
            return None
        except Exception as e:
            print(f"  ⚠️ Error loading custom config: {e}")
            return None
    
    def _apply_env_overrides(self):
        """
        Aplica overrides via environment variables
        
        Supported env vars:
        - SEVERITY_THRESHOLD: Altera behavior.severity_threshold
        - TONE: Altera educational_mode.tone.style
        - MAX_COMMENTS: Altera behavior.max_comments_per_commit
        """
        overrides = []
        
        # Override: Severity threshold
        if os.getenv("SEVERITY_THRESHOLD"):
            severity = os.getenv("SEVERITY_THRESHOLD")
            if "behavior" not in self.config:
                self.config["behavior"] = {}
            self.config["behavior"]["severity_threshold"] = severity
            overrides.append(f"severity_threshold={severity}")
        
        # Override: Tone
        if os.getenv("TONE"):
            tone = os.getenv("TONE")
            if "educational_mode" not in self.config:
                self.config["educational_mode"] = {}
            if "tone" not in self.config["educational_mode"]:
                self.config["educational_mode"]["tone"] = {}
            self.config["educational_mode"]["tone"]["style"] = tone
            overrides.append(f"tone={tone}")
        
        # Override: Max comments
        if os.getenv("MAX_COMMENTS"):
            try:
                max_comments = int(os.getenv("MAX_COMMENTS"))
                if "behavior" not in self.config:
                    self.config["behavior"] = {}
                self.config["behavior"]["max_comments_per_commit"] = max_comments
                overrides.append(f"max_comments={max_comments}")
            except ValueError:
                print("  ⚠️ Invalid MAX_COMMENTS value (must be integer)")
        
        if overrides:
            print(f"  🔧 Applied env overrides: {', '.join(overrides)}")
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge recursivo de dicionários
        
        Args:
            base: Dict base
            override: Dict com overrides
        
        Returns:
            Novo dict com merge completo
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Merge recursivo para nested dicts
                result[key] = ConfigService._deep_merge(result[key], value)
            else:
                # Override direto
                result[key] = value
        
        return result
    
    # ═══════════════════════════════════════════════════════════
    # 🔍 GETTERS UTILITÁRIOS
    # ═══════════════════════════════════════════════════════════
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtém valor da config usando dot notation
        
        Args:
            key_path: Caminho com dots (ex: "educational_mode.tone.style")
            default: Valor padrão se não encontrado
        
        Returns:
            Valor da config ou default
        
        Example:
            >>> config.get("behavior.max_comments_per_commit", 10)
            10
        """
        if not self._loaded:
            self.load()
        
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_educational_mode(self) -> Dict[str, Any]:
        """Retorna config do educational mode"""
        return self.get("educational_mode", {})
    
    def get_naming_conventions(self, language: str) -> Dict[str, str]:
        """
        Retorna naming conventions para uma linguagem
        
        Args:
            language: Nome da linguagem (python, typescript, etc)
        
        Returns:
            Dict com convenções ou dict vazio
        """
        return self.get(f"naming_conventions.{language}", {})
    
    def get_code_quality_rules(self) -> Dict[str, Any]:
        """Retorna regras de code quality"""
        return self.get("code_quality", {})
    
    def get_security_rules(self) -> Dict[str, Any]:
        """Retorna regras de segurança"""
        return self.get("security", {})
    
    def get_skip_patterns(self) -> list:
        """Retorna padrões de commit para skip"""
        return self.get("behavior.skip_commit_messages", [
            "[skip-review]",
            "[no-review]",
            "WIP:",
            "Merge",
            "Revert"
        ])
    
    def get_max_comments(self) -> int:
        """Retorna limite de comentários por commit"""
        return self.get("behavior.max_comments_per_commit", 10)
    
    def get_skip_file_types(self) -> list:
        """Retorna extensões de ficheiros a ignorar"""
        return self.get("behavior.skip_file_types", [
            ".json", ".md", ".lock", ".min.js", ".bundle.js", ".map"
        ])
    
    def is_educational_mode_enabled(self) -> bool:
        """Verifica se modo educativo está ativo"""
        return self.get("educational_mode.enabled", True)
    
    def get_tone(self) -> str:
        """Retorna estilo de tom do mentor"""
        return self.get("educational_mode.tone.style", "mentor")
    
    def get_language(self) -> str:
        """Retorna idioma das reviews"""
        return self.get("educational_mode.tone.language", "pt-PT")
    
    def should_use_emojis(self) -> bool:
        """Verifica se deve usar emojis"""
        return self.get("educational_mode.tone.use_emojis", True)
    
    # ═══════════════════════════════════════════════════════════
    # 📊 DEBUG / INFO
    # ═══════════════════════════════════════════════════════════
    
    def print_summary(self):
        """Imprime resumo da configuração carregada"""
        if not self._loaded:
            self.load()
        
        print("\n" + "="*50)
        print("📋 Configuration Summary")
        print("="*50)
        print(f"Educational Mode: {'✅ Enabled' if self.is_educational_mode_enabled() else '❌ Disabled'}")
        print(f"Tone: {self.get_tone()}")
        print(f"Language: {self.get_language()}")
        print(f"Max Comments: {self.get_max_comments()}")
        print(f"Use Emojis: {'✅ Yes' if self.should_use_emojis() else '❌ No'}")
        print("="*50 + "\n")
    
    def to_dict(self) -> Dict[str, Any]:
        """Retorna config completo como dict"""
        if not self._loaded:
            self.load()
        return self.config.copy()


# ═══════════════════════════════════════════════════════════
# 🔧 SINGLETON PATTERN (opcional)
# ═══════════════════════════════════════════════════════════

_config_instance: Optional[ConfigService] = None


def get_config() -> ConfigService:
    """
    Retorna instância singleton do ConfigService
    
    Returns:
        ConfigService instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigService()
        _config_instance.load()
    
    return _config_instance


def reset_config():
    """Reset da instância singleton (útil para testes)"""
    global _config_instance
    _config_instance = None