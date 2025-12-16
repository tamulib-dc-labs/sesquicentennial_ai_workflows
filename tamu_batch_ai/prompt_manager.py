"""Prompt template management for TAMU Batch AI."""

from pathlib import Path
from typing import Optional

from .config import path_config


class PromptManager:
    """Manages loading and rendering prompt templates."""

    def __init__(self, prompts_dir: Optional[str] = None):
        """Initialize the prompt manager.

        Args:
            prompts_dir: Directory containing prompt templates.
                        Defaults to config.path_config.prompts_dir
        """
        self.prompts_dir = Path(prompts_dir or path_config.prompts_dir)
        if not self.prompts_dir.is_absolute():
            # Make relative to current working directory
            self.prompts_dir = Path.cwd() / self.prompts_dir

    def load_template(self, prompt_name: str) -> str:
        """Load a prompt template from file.

        Args:
            prompt_name: Name of the prompt file (e.g., "metadata.md", "htr", "amc")

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        # Add .md extension if not present
        if not prompt_name.endswith('.md'):
            prompt_name = f"{prompt_name}.md"

        prompt_path = self.prompts_dir / prompt_name

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def render(self, template: str, **kwargs) -> str:
        """Render a template by replacing placeholders with values.

        Supports both bracket and brace placeholders:
        - [INSERT TEXT HERE]
        - {variable_name}

        Args:
            template: Template string with placeholders
            **kwargs: Key-value pairs to replace in template

        Returns:
            Rendered template string
        """
        rendered = template

        # Replace bracket-style placeholders: [INSERT FOO HERE]
        for key, value in kwargs.items():
            # Convert underscores to spaces for placeholder matching
            key_formatted = key.upper().replace('_', ' ')
            bracket_placeholder = f"[INSERT {key_formatted} HERE]"
            rendered = rendered.replace(bracket_placeholder, str(value))

            # Also support alternative formats
            alt_placeholder = f"[{key_formatted}]"
            rendered = rendered.replace(alt_placeholder, str(value))

        # Replace brace-style placeholders: {foo}
        for key, value in kwargs.items():
            brace_placeholder = f"{{{key}}}"
            rendered = rendered.replace(brace_placeholder, str(value))

        return rendered

    def load_and_render(self, prompt_name: str, **kwargs) -> str:
        """Load a template and render it with values.

        Args:
            prompt_name: Name of the prompt file
            **kwargs: Key-value pairs to replace in template

        Returns:
            Rendered prompt string
        """
        template = self.load_template(prompt_name)
        return self.render(template, **kwargs)

    def list_prompts(self) -> list[str]:
        """List all available prompt templates.

        Returns:
            List of prompt template names (without .md extension)
        """
        if not self.prompts_dir.exists():
            return []

        prompts = []
        for file in self.prompts_dir.glob("*.md"):
            prompts.append(file.stem)  # filename without extension

        return sorted(prompts)

prompt_manager = PromptManager()
