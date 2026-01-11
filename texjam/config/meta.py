from __future__ import annotations

import keyword
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Callable

import questionary
import typer
from pydantic import BaseModel, WrapValidator, model_validator

if TYPE_CHECKING:
    from ..render.executor import TexJam


class MetaBase(BaseModel, ABC):
    prompt: str | None = None
    required: bool = False

    def _question_validate(self, answer: Any) -> None:
        if self.required and answer == '':
            raise questionary.ValidationError(
                message='This field is required.',
            )

    def _extra_prompt(self) -> str | None:
        return None

    @abstractmethod
    def _prompt_dict(
        self,
        prompt: str,
        default: str,
        validate: Callable[[str], bool],
    ) -> dict[str, Any]: ...

    def _convert_answer(self, answer: Any) -> Any:
        return answer


class MetaStr(MetaBase):
    default: str = ''
    min_length: int | None = None
    max_length: int | None = None

    @model_validator(mode='after')
    @staticmethod
    def check_min_max(data: MetaStr) -> MetaStr:
        if (
            data.min_length is not None
            and data.max_length is not None
            and data.min_length > data.max_length
        ):
            raise ValueError('min_length cannot be greater than max_length.')
        if data.min_length is not None and data.min_length < 0:
            raise ValueError('min_length cannot be negative.')
        if data.max_length is not None and data.max_length < 0:
            raise ValueError('max_length cannot be negative.')
        return data

    def _question_validate(self, answer: Any) -> None:
        super()._question_validate(answer)

        if self.min_length is not None and len(answer) < self.min_length:
            raise questionary.ValidationError(
                message=f'Input must be at least {self.min_length} characters long.',
            )
        if self.max_length is not None and len(answer) > self.max_length:
            raise questionary.ValidationError(
                message=f'Input must be at most {self.max_length} characters long.',
            )

    def _extra_prompt(self) -> str | None:
        has_min = self.min_length is not None
        has_max = self.max_length is not None

        if has_min or has_max:
            if has_min and has_max:
                return f'{self.min_length}-{self.max_length} characters'
            elif has_min:
                return f'>= {self.min_length} characters'
            elif has_max:
                return f'<= {self.max_length} characters'
        return None

    def _prompt_dict(
        self,
        prompt: str,
        default: str,
        validate: Callable[[str], bool],
    ) -> dict[str, Any]:
        return {
            'type': 'text',
            'message': prompt,
            'default': default,
            'validate': validate,
        }


class MetaNumber(MetaBase):
    default: float | int | None = None
    min_value: float | int | None = None
    max_value: float | int | None = None
    is_integer: bool = False

    @model_validator(mode='after')
    @staticmethod
    def check_min_max(data: MetaNumber) -> MetaNumber:
        if (
            data.min_value is not None
            and data.max_value is not None
            and data.min_value > data.max_value
        ):
            raise ValueError('min_value cannot be greater than max_value.')

        if data.is_integer:
            if data.min_value is not None:
                try:
                    data.min_value = int(data.min_value)
                except ValueError:
                    raise ValueError('min_value must be an integer.')
            if data.max_value is not None:
                try:
                    data.max_value = int(data.max_value)
                except ValueError:
                    raise ValueError('max_value must be an integer.')
        return data

    def _question_validate(self, answer: Any) -> None:
        super()._question_validate(answer)

        if self.is_integer:
            try:
                val = int(answer)
            except ValueError:
                raise questionary.ValidationError(
                    message='Input must be an integer.',
                )
        else:
            try:
                val = float(answer)
            except ValueError:
                raise questionary.ValidationError(
                    message='Input must be a number.',
                )
        if self.min_value is not None and val < self.min_value:
            raise questionary.ValidationError(
                message=f'Input must be at least {self.min_value}.',
            )
        if self.max_value is not None and val > self.max_value:
            raise questionary.ValidationError(
                message=f'Input must be at most {self.max_value}.',
            )

    def _extra_prompt(self) -> str | None:
        has_min = self.min_value is not None
        has_max = self.max_value is not None

        if has_min or has_max:
            if has_min and has_max:
                return f'{self.min_value}-{self.max_value}'
            elif has_min:
                return f'>={self.min_value}'
            elif has_max:
                return f'<={self.max_value}'
        return None

    def _prompt_dict(
        self,
        prompt: str,
        default: str,
        validate: Callable[[str], bool],
    ) -> dict[str, Any]:
        return {
            'type': 'text',
            'message': prompt,
            'default': default,
            'validate': validate,
        }

    def _convert_answer(self, answer: Any) -> Any:
        if self.is_integer:
            return int(answer)
        else:
            return float(answer)


class MetaBool(MetaBase):
    default: bool = False

    def _prompt_dict(
        self,
        prompt: str,
        default: str,
        validate: Callable[[str], bool],
    ) -> dict[str, Any]:
        return {
            'type': 'confirm',
            'message': prompt,
            'default': self.default,
        }


class MetaPath(MetaBase):
    default: str | None = None
    exists: bool = False
    is_dir: bool = False
    is_file: bool = False

    @model_validator(mode='after')
    @staticmethod
    def check_is_dir_file(data: MetaPath) -> MetaPath:
        if not data.exists:
            if data.is_dir or data.is_file:
                raise ValueError('is_dir and is_file require exists to be True.')
        if data.is_dir and data.is_file:
            raise ValueError('is_dir and is_file cannot both be True.')
        return data

    def _question_validate(self, answer: Any) -> None:
        super()._question_validate(answer)

        path = Path(answer)
        if self.exists and not path.exists():
            raise questionary.ValidationError(
                message='Path does not exist.',
            )
        if self.is_dir and not path.is_dir():
            raise questionary.ValidationError(
                message='Path is not a directory.',
            )
        if self.is_file and not path.is_file():
            raise questionary.ValidationError(
                message='Path is not a file.',
            )

    def _extra_prompt(self) -> str | None:
        if self.is_dir:
            return 'dir'
        if self.is_file:
            return 'file'
        if self.exists:
            return 'exists'
        return None

    def _prompt_dict(
        self,
        prompt: str,
        default: str,
        validate: Callable[[str], bool],
    ) -> dict[str, Any]:
        return {
            'type': 'path',
            'message': prompt,
            'default': default,
            'validate': validate,
            'only_directories': self.is_dir,
        }

    def _convert_answer(self, answer: Any) -> Any:
        return Path(answer)


class MetaChoice(MetaBase):
    default: str | None = None
    choices: list[str]

    @model_validator(mode='after')
    @staticmethod
    def check_choices(data: MetaChoice) -> MetaChoice:
        if len(data.choices) == 0:
            raise ValueError('choices cannot be empty.')
        return data

    def _prompt_dict(
        self,
        prompt: str,
        default: str,
        validate: Callable[[str], bool],
    ) -> dict[str, Any]:
        return {
            'type': 'select',
            'message': prompt,
            'choices': self.choices,
            'default': default,
        }


class MetaSelect(MetaBase):
    items: list[MetaSelectItem]

    @model_validator(mode='after')
    @staticmethod
    def check_items(data: MetaSelect) -> MetaSelect:
        if len(data.items) == 0:
            raise ValueError('items cannot be empty.')
        return data

    def _prompt_dict(
        self,
        prompt: str,
        default: str,
        validate: Callable[[str], bool],
    ) -> dict[str, Any]:
        return {
            'type': 'checkbox',
            'message': prompt,
            'choices': [
                questionary.Choice(
                    item.title,
                    value=item.value or item.title,
                    checked=item.default,
                )
                for item in self.items
            ],
        }


class MetaSelectItem(BaseModel):
    title: str
    value: str | None = None
    default: bool = False

    @model_validator(mode='before')
    @classmethod
    def parse_string(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {'title': data}
        return data


def parse_meta_field(field: Any, handler) -> MetaField:
    if isinstance(field, dict):
        field_type = field.get('type')
        if field_type == 'str':
            return MetaStr(**field)
        elif field_type == 'number':
            return MetaNumber(**field)
        elif field_type == 'bool':
            return MetaBool(**field)
        elif field_type == 'path':
            return MetaPath(**field)
        elif field_type == 'choice':
            return MetaChoice(**field)
        elif field_type == 'select':
            return MetaSelect(**field)
        else:
            raise ValueError(f'Unknown meta field type: {field}')

    if isinstance(field, str):
        return MetaStr(default=field)
    elif isinstance(field, int):
        return MetaNumber(default=field, is_integer=True)
    elif isinstance(field, float):
        return MetaNumber(default=field, is_integer=False)
    elif isinstance(field, bool):
        return MetaBool(default=field)
    elif isinstance(field, list):
        return MetaChoice(choices=field)
    else:
        raise ValueError(f'Unknown meta field type: {field}')


def validate_meta_fields(fields: Any, handler) -> MetaFields:
    if not isinstance(fields, dict):
        raise ValueError('Meta fields must be a dictionary.')
    validated_fields: MetaFields = {}
    for name, field in fields.items():
        if not isinstance(name, str):
            raise ValueError(f'Meta field name must be a string: {name}')
        if not name.isidentifier() or keyword.iskeyword(name):
            raise ValueError(f'Invalid meta field name: {name}')
        validated_fields[name] = parse_meta_field(field, None)
    return validated_fields


type MetaField = Annotated[
    MetaStr | MetaNumber | MetaBool | MetaPath | MetaChoice | MetaSelect,
    WrapValidator(parse_meta_field),
]

type MetaFields = Annotated[
    dict[str, MetaField],
    WrapValidator(validate_meta_fields),
]


class Prompter:
    def __init__(self, texjam: TexJam) -> None:
        self.texjam = texjam

    def _render_value(self, value: str | None) -> str | None:
        if value is None:
            return None
        template = self.texjam.env.from_string(value)
        rendered = template.render(self.texjam.metadata)
        return rendered

    def prompt_meta_field(self, name: str, field: MetaField) -> Any:
        prompt = field.prompt or name.replace('_', ' ').capitalize()
        extra = field._extra_prompt()
        if extra:
            prompt += f' ({extra})'

        if hasattr(field, 'default'):
            _default = field.default  # type: ignore
            if isinstance(_default, str):
                default_value = self._render_value(_default) or ''
            else:
                default_value = str(_default)
        else:
            default_value = ''

        prompt_dict = field._prompt_dict(
            prompt=prompt,
            default=default_value,
            validate=lambda ans: field._question_validate(ans) or True,
        )
        if prompt_dict['default'] is None:
            # some types of questionary prompts do not accept None as default,
            # so we remove it from the dict
            del prompt_dict['default']
        prompt_dict['name'] = 'response'
        answer = questionary.prompt([prompt_dict])
        if answer is None or len(answer) == 0:
            # aborted by Ctrl+C
            raise typer.Abort()
        return field._convert_answer(answer['response'])
