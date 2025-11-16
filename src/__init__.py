"""
AI Code Reviewer - Source Package
"""

__version__ = "1.0.0"
__author__ = "Dee-Tee11"

# Re-export models para facilitar imports
from .models import (
    ReviewComment,
    FileChange,
    ReviewStatistics,
    CodeChunk,
    RetrievalContext,
    create_review_comment,
)

__all__ = [
    "ReviewComment",
    "FileChange",
    "ReviewStatistics",
    "CodeChunk",
    "RetrievalContext",
    "create_review_comment",
]