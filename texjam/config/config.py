from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .meta import MetaFields


class TemplateConfig(BaseModel):
    """A class representing the configuration for a template."""

    name: str
    authors: list[str] | None = None
    description: str | None = None

    source_dir: Path = Path('src')
    plugin_dir: Path = Path('plugins')


class JinjaConfig(BaseModel):
    """A class representing the Jinja2 configuration for a template."""

    block_start_string: str = '((*'
    block_end_string: str = '*))'
    variable_start_string: str = '((('
    variable_end_string: str = ')))'
    comment_start_string: str = '((='
    comment_end_string: str = '=))'
    line_statement_prefix: str | None = None
    line_comment_prefix: str | None = None
    trim_blocks: bool = True
    lstrip_blocks: bool = True
    newline_sequence: str = '\n'
    keep_trailing_newline: bool = True
    autoescape: bool = False


class TexJamConfig(TemplateConfig):
    meta: MetaFields
    jinja: JinjaConfig = Field(default_factory=JinjaConfig)

    model_config = ConfigDict(extra='ignore')
