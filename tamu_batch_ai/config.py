"""Centralized configuration for TAMU Batch AI."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ModelConfig:
    """Configuration for Claude API model settings."""

    # Default model to use
    default_model: str = "claude-3-5-haiku-20241022"

    # Max tokens for different task types
    max_tokens: Dict[str, int] = field(default_factory=lambda: {
        "htr": 1000,           # Handwritten text recognition
        "metadata": 2000,      # Metadata generation for works
        "av": 4000,            # Audio/video metadata
        "image": 3000,         # Image/map analysis
        "article": 3000,       # Article analysis
        "analyze_only": 2000,  # Image analysis without metadata
    })

    # Temperature setting (0-1, lower = more deterministic)
    temperature: float = 0.0

    def get_max_tokens(self, task_type: str) -> int:
        """Get max tokens for a specific task type."""
        return self.max_tokens.get(task_type, 2000)


@dataclass
class PathConfig:
    """Configuration for file paths and directories."""

    # Directory containing prompt templates
    prompts_dir: str = "prompts"

    # Default output directory for batch processing
    default_output_dir: str = ".tmp"

    # Output file extensions
    json_ext: str = ".json"


# Global config instances
model_config = ModelConfig()
path_config = PathConfig()
