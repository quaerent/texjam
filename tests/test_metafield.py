from typing import Any

from jinja2 import Environment
import pytest
from pytest_mock import MockerFixture

from texjam import MetaField


@pytest.mark.parametrize(
    'field_type, default_value',
    [(str, 'default string'), (int, 42), (float, 3.14)],
)
def test_metafield_from_item(field_type: type, default_value: Any) -> None:
    meta_field = MetaField.from_item('key_value', None)
    assert meta_field.key == 'key_value'
    assert meta_field.prompt_str == 'Key value'
    assert meta_field.type is str
    assert meta_field.default is None
    assert meta_field.choices is None
    assert meta_field.required is True

    meta_field = MetaField.from_item('key_value', default_value)
    assert meta_field.key == 'key_value'
    assert meta_field.prompt_str == 'Key value'
    assert meta_field.type is field_type
    assert meta_field.default == default_value
    assert meta_field.choices is None
    assert meta_field.required is False

    meta_field = MetaField.from_item('key_value', {'type': field_type.__name__})
    assert meta_field.key == 'key_value'
    assert meta_field.prompt_str == 'Key value'
    assert meta_field.type is field_type
    assert meta_field.default is None
    assert meta_field.choices is None
    assert meta_field.required is True

    meta_field = MetaField.from_item(
        'key_value',
        {
            'type': field_type.__name__,
            'default': default_value,
        },
    )
    assert meta_field.key == 'key_value'
    assert meta_field.prompt_str == 'Key value'
    assert meta_field.type is field_type
    assert meta_field.default == default_value
    assert meta_field.choices is None
    assert meta_field.required is False

    meta_field = MetaField.from_item(
        'key_value',
        {
            'type': field_type.__name__,
            'choices': [default_value, default_value],
        },
    )
    assert meta_field.key == 'key_value'
    assert meta_field.prompt_str == 'Key value'
    assert meta_field.type is field_type
    assert meta_field.default is None
    assert meta_field.choices == [default_value, default_value]
    assert meta_field.required is True

    meta_field = MetaField.from_item(
        'key_value',
        {
            'type': field_type.__name__,
            'required': False,
        },
    )
    assert meta_field.key == 'key_value'
    assert meta_field.prompt_str == 'Key value'
    assert meta_field.type is field_type
    assert meta_field.default is None
    assert meta_field.choices is None
    assert meta_field.required is False

    meta_field = MetaField.from_item(
        'key_value',
        {
            'type': field_type.__name__,
            'default': default_value,
            'choices': [default_value, default_value],
            'required': False,
        },
    )
    assert meta_field.key == 'key_value'
    assert meta_field.prompt_str == 'Key value'
    assert meta_field.type is field_type
    assert meta_field.default == default_value
    assert meta_field.choices == [default_value, default_value]
    assert meta_field.required is False


def test_metafield_invalid_type() -> None:
    with pytest.raises(AssertionError):
        MetaField.from_item('key_value', {'type': 'unsupported_type'})


def test_metafield_invalid_default() -> None:
    with pytest.raises(AssertionError):
        MetaField.from_item('key_value', {'type': 'str', 'default': True})


def test_metafield_invalid_choices() -> None:
    with pytest.raises(AssertionError):
        MetaField.from_item('key_value', {'type': 'str', 'choices': [True]})
    with pytest.raises(AssertionError):
        MetaField.from_item('key_value', {'type': 'bool', 'choices': [True, False]})
    with pytest.raises(AssertionError):
        MetaField.from_item('key_value', {'type': 'str', 'choices': []})
    with pytest.raises(AssertionError):
        MetaField.from_item('key_value', {'type': 'str', 'choices': [type]})


@pytest.fixture
def jinja_env() -> Environment:
    return Environment(
        variable_start_string='[-',
        variable_end_string='-]',
        block_start_string='[%',
        block_end_string='%]',
        comment_start_string='[#',
        comment_end_string='#]',
        autoescape=False,
    )


def test_metafield_prompt_str(mocker: MockerFixture, jinja_env: Environment) -> None:
    mock_get = mocker.patch('builtins.input', return_value='user input')
    meta_field = MetaField.from_item('sample_key', 'default_value')
    result = meta_field.prompt(jinja_env, {})

    mock_get.assert_called_once_with('Sample key [default_value]: ')
    assert result == 'user input'


def test_metafield_prompt_str_no_default(
    mocker: MockerFixture, jinja_env: Environment
) -> None:
    mock_get = mocker.patch('builtins.input', return_value='user input')
    meta_field = MetaField.from_item('sample_key', None)
    result = meta_field.prompt(jinja_env, {})

    mock_get.assert_called_once_with('Sample key: ')
    assert result == 'user input'


def test_metafield_prompt_with_choices(
    mocker: MockerFixture, jinja_env: Environment
) -> None:
    mock_get = mocker.patch('builtins.input', return_value='2')
    meta_field = MetaField.from_item('sample_key', {'type': 'int', 'choices': [1, 2, 3]})
    result = meta_field.prompt(jinja_env, {})

    mock_get.assert_called_once_with('Sample key (1, 2, 3): ')
    assert result == 2


def test_metafield_prompt_bool(mocker: MockerFixture, jinja_env: Environment) -> None:
    mock_get = mocker.patch('builtins.input', return_value='yes')
    meta_field = MetaField.from_item('sample_key', {'type': 'bool'})
    result = meta_field.prompt(jinja_env, {})

    mock_get.assert_called_once_with('Sample key (y/n): ')
    assert result is True


def test_metafield_prompt_template(mocker: MockerFixture, jinja_env: Environment) -> None:
    mock_get = mocker.patch('builtins.input', return_value='')
    meta_field = MetaField.from_item(
        'sample_key',
        {
            'type': 'str',
            'default': '[- previous_key -] default',
        },
    )
    metadata = {'previous_key': 'rendered'}
    result = meta_field.prompt(jinja_env, metadata)

    mock_get.assert_called_once_with('Sample key [rendered default]: ')
    assert result == 'rendered default'


def test_metafield_prompt_with_invalid_input(
    mocker: MockerFixture, jinja_env: Environment
) -> None:
    mock_get = mocker.patch('builtins.input', side_effect=['invalid', '42'])
    meta_field = MetaField.from_item('sample_key', {'type': 'int'})
    result = meta_field.prompt(jinja_env, {})

    assert mock_get.call_count == 2
    assert result == 42
