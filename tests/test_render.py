import yaml
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from typer.testing import CliRunner

from texjam.cli import app

runner = CliRunner()


def test_render(tmp_path):
    with create_pipe_input() as inp:
        with create_app_session(input=inp):
            # Mock user inputs
            # Input 8 enter presses to choose default options
            inp.send_text('\r' * 8)

            result = runner.invoke(app, ['new', '-o', str(tmp_path), './example'])

    # Check that the command was successful
    assert result.exit_code == 0, result.output

    # Check that the expected file was created
    yaml_file = tmp_path / 'example-project' / 'test.yaml'
    assert yaml_file.exists() and yaml_file.is_file()

    # Check that the content of the file is as expected
    expected_content = {
        'string': 'default string',
        'number': 42,
        'boolean': True,
        'path': 'default/path',
        'choice': 'option2',
        'select': ['val2'],
    }
    with yaml_file.open('r') as f:
        content = yaml.safe_load(f)
    assert content == expected_content
