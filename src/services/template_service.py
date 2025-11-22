#!/usr/bin/env python3
"""
Template Service
Loads and parses personality templates (config + prompts in one file)
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional


class TemplateServiceError(Exception):
    """Exception for template service errors"""
    pass


class TemplateService:
    """
    Service to load personality templates
    
    Responsibilities:
    - Load template files
    - Parse config section (YAML)
    - Extract system prompt section
    - Validate template structure
    - Support built-in and custom templates
    """
    
    # Built-in template names
    BUILTIN_TEMPLATES = ["default", "custom_example"]
    DEFAULT_TEMPLATE = "default"
    
    def __init__(self, templates_dir: str = None):
        """
        Initialize template service
        
        Args:
            templates_dir: Path to templates directory (default: ./templates)
        """
        if templates_dir is None:
            # Default to templates/ next to this file's parent
            templates_dir = Path(__file__).parent.parent.parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        
        if not self.templates_dir.exists():
            raise TemplateServiceError(f"Templates directory not found: {self.templates_dir}")
    
    def load(self, template_name: str) -> Tuple[Dict, str]:
        """
        Load a template and return (config, system_prompt)
        
        Args:
            template_name: Name of template (e.g., 'educational') or path to custom template
        
        Returns:
            (config_dict, system_prompt_text)
        
        Raises:
            TemplateServiceError: If template not found or invalid
        """
        print(f"📋 Loading template: {template_name}")
        
        # Determine template path
        template_path = self._resolve_template_path(template_name)
        
        if not template_path.exists():
            raise TemplateServiceError(f"Template not found: {template_path}")
        
        # Read template file
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise TemplateServiceError(f"Failed to read template: {e}")
        
        # Parse template
        config, system_prompt = self._parse_template(content)
        
        print(f"  ✅ Template loaded: {template_name}")
        return config, system_prompt
    
    def _resolve_template_path(self, template_name: str) -> Path:
        """
        Resolve template name to path
        
        Args:
            template_name: Name or path
        
        Returns:
            Path to template file
        """
        # If it's a path (contains / or \), use as-is
        if '/' in template_name or '\\' in template_name:
            return Path(template_name)
        
        # Otherwise treat as built-in template name
        # Remove .txt extension if provided
        if template_name.endswith('.txt'):
            template_name = template_name[:-4]
        
        return self.templates_dir / f"{template_name}.txt"
    
    def _parse_template(self, content: str) -> Tuple[Dict, str]:
        """
        Parse template file into config and prompt
        
        Template format:
        ```
        # Comments and metadata
        config:
          key: value
          ...
        
        ---SYSTEM_PROMPT---
        Prompt text...
        ---END_SYSTEM_PROMPT---
        ```
        
        Args:
            content: Template file content
        
        Returns:
            (config_dict, system_prompt)
        
        Raises:
            TemplateServiceError: If parsing fails
        """
        # Extract system prompt section
        prompt_pattern = r'---SYSTEM_PROMPT---(.*?)---END_SYSTEM_PROMPT---'
        prompt_match = re.search(prompt_pattern, content, re.DOTALL)
        
        if not prompt_match:
            raise TemplateServiceError("Template missing SYSTEM_PROMPT section")
        
        system_prompt = prompt_match.group(1).strip()
        
        # Extract config section (everything before ---SYSTEM_PROMPT---)
        config_text = content.split('---SYSTEM_PROMPT---')[0]
        
        # Remove comment lines and metadata header
        config_lines = []
        in_config = False
        
        for line in config_text.split('\n'):
            line = line.rstrip()
            
            # Skip empty lines and full-line comments
            if not line or line.startswith('#'):
                continue
            
            # Look for 'config:' to start
            if line.strip().startswith('config:'):
                in_config = True
                config_lines.append(line)
                continue
            
            # If we're in config section, add line
            if in_config:
                config_lines.append(line)
        
        if not config_lines:
            raise TemplateServiceError("Template missing config section")
        
        # Parse YAML
        try:
            config_yaml = '\n'.join(config_lines)
            parsed = yaml.safe_load(config_yaml)
            
            if not isinstance(parsed, dict) or 'config' not in parsed:
                raise TemplateServiceError("Invalid config format")
            
            config = parsed['config']
            
        except yaml.YAMLError as e:
            raise TemplateServiceError(f"Failed to parse config YAML: {e}")
        
        return config, system_prompt
    
    def list_builtin_templates(self) -> list:
        """
        List available built-in templates
        
        Returns:
            List of template names
        """
        return self.BUILTIN_TEMPLATES.copy()
    
    def get_default_template(self) -> str:
        """
        Get default template name
        
        Returns:
            Default template name
        """
        return self.DEFAULT_TEMPLATE
