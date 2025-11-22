#!/usr/bin/env python3
"""
Template-based Configuration Loader
Provides simple template loading for AI Code Reviewer
"""

import os
from pathlib import Path
from typing import Tuple, Dict, Any

from src.services.template_service import TemplateService

def load_template_config() -> Tuple[Dict[str, Any], str]:
    """
    Load configuration and prompt from template
    
    Checks REVIEWER_TEMPLATE env var:
    - If set: loads that template
    - If not set: loads 'default' template
    
    Returns:
        (config_dict, system_prompt_text)
    
    Example:
        >>> config, prompt = load_template_config()
    """
    template_name = os.getenv("REVIEWER_TEMPLATE", "default").strip()
    
    print(f"📋 Loading reviewer template: {template_name}")
    
    template_service = TemplateService()
    config, system_prompt = template_service.load(template_name)
    
    return config, system_prompt


def get_template_name() -> str:
    """
    Get the name of the template being used
    
    Returns:
        Template name from env var or 'default'
    """
    return os.getenv("REVIEWER_TEMPLATE", "default").strip()
