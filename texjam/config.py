from __future__ import annotations

import keyword
from pathlib import Path
from typing import Any

from jinja2 import Environment
from pydantic import BaseModel, Field, field_validator, model_validator


class MetaField(BaseModel):
    """A class representing a metadata field for user input."""

    key: str
    prompt_str: str
    type: type[int] | type[float] | type[bool] | type[str]
    default: int | float | bool | str | None = None
    choices: list[int | float | bool | str] | None = None
    required: bool = True

    @model_validator(mode='wrap')
    @classmethod
    def parse_input(cls, data: tuple[str, Any], handler: Any) -> MetaField:
        key, obj = data

        if not key.isidentifier() or keyword.iskeyword(key):
            raise ValueError(f'Invalid metadata key: {key}')

        meta_field = cls.model_construct(
            key=key,
            prompt_str=key.replace('_', ' ').capitalize(),
            type=str,
        )

        if isinstance(obj, dict):
            for key in obj.keys():
                if key not in ('prompt', 'type', 'default', 'choices', 'required'):
                    raise ValueError(f'Unknown field "{key}" in meta field: {key}')

            prompt = obj.get('prompt')
            type_str = obj.get('type')
            default = obj.get('default')
            choices = obj.get('choices')
            required = obj.get('required')

            if prompt is not None:
                assert isinstance(prompt, str)
                meta_field.prompt_str = prompt

            assert type_str is not None
            assert isinstance(type_str, str)
            supported_types: dict[str, type] = {
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
            }
            assert type_str in supported_types
            meta_field.type = supported_types[type_str]

            if default is not None:
                assert isinstance(default, (str, meta_field.type))
                meta_field.default = default
                meta_field.required = False

            if choices is not None:
                assert isinstance(choices, list)
                assert len(choices) > 0
                assert meta_field.type is not bool
                for choice in choices:
                    assert isinstance(choice, (str, meta_field.type))
                meta_field.choices = choices

            if required is not None:
                assert isinstance(required, bool)
                if required:
                    assert default is None
                meta_field.required = required

        elif obj is None:
            pass

        else:
            assert isinstance(obj, (str, int, float, bool))
            meta_field.default = obj
            meta_field.type = type(obj)
            meta_field.required = False

        return meta_field

    def prompt(self, env: Environment, metadata: dict[str, Any]) -> Any:
        """Prompt the user for input based on the MetaField configuration.

        Args:
            env (Environment): Jinja2 environment for rendering templates.
            metadata (dict[str, Any]): Current metadata dictionary for rendering.

        Returns:
            Any: The user input converted to the appropriate type.
        """

        # render default
        default = None
        if self.default is not None:
            if isinstance(self.default, str):
                template = env.from_string(self.default)
                default = template.render(metadata)
                default = self.type(default)
            else:
                default = self.default

        # render choices
        choices = None
        if self.choices is not None:
            choices = []
            for choice in self.choices:
                if isinstance(choice, str):
                    template = env.from_string(choice)
                    rendered_choice = template.render(metadata)
                    rendered_choice = self.type(rendered_choice)
                    choices.append(rendered_choice)
                else:
                    choices.append(choice)

        while True:
            # build prompt string
            prompt_str = f'{self.prompt_str}'

            if self.type is bool:
                if default is not None:
                    prompt_str += ' (Y/n)' if default else ' (y/N)'
                else:
                    prompt_str += ' (y/n)'
            else:
                if choices is not None:
                    prompt_str += f' ({str.join(", ", map(repr, choices))})'
                if default is not None:
                    prompt_str += f' [{default}]'
            prompt_str += ': '

            # process input
            user_input = input(prompt_str).strip()
            if user_input == '':
                if self.required:
                    print('This field is required.')
                    continue
                input_value = default
            else:
                try:
                    if self.type is bool:
                        if user_input.lower() in ('yes', 'y', 'true', 't', '1'):
                            input_value = True
                        elif user_input.lower() in ('no', 'n', 'false', 'f', '0'):
                            input_value = False
                        else:
                            raise ValueError('Invalid boolean value.')
                    else:
                        input_value = self.type(user_input)
                except ValueError:
                    print(f'Invalid input. Expected type: {self.type.__name__}.')
                    continue

            # validate choices
            if choices is not None and input_value not in choices:
                print('Input not in allowed choices.')
                continue

            return input_value


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


class TexJamConfig(BaseModel):
    template: TemplateConfig
    jinja: JinjaConfig = Field(default_factory=JinjaConfig)
    meta: list[MetaField] = Field(default_factory=list)

    @field_validator('meta', mode='before')
    @classmethod
    def parse_meta(cls, v: Any) -> list[tuple[str, Any]]:
        if not isinstance(v, dict):
            raise ValueError('Meta field must be a dictionary.')
        return [(key, obj) for key, obj in v.items()]
