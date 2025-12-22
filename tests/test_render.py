from pathlib import Path

from click.testing import CliRunner

from texjam.main import cli


def test_render(tmp_path: Path) -> None:
    inputs = [
        'Foo Bar',
        '',
        '30',
        '',
        'yes',
        'Alice',
    ]

    runner = CliRunner()
    runner.invoke(
        cli,
        ['new', './example', str(tmp_path)],
        input='\n'.join(inputs) + '\n',
    )

    expected_root = Path('./example/output')
    for path in expected_root.rglob('*'):
        target_path = tmp_path / path.relative_to(expected_root)
        assert target_path.exists()

        if path.is_dir():
            assert target_path.is_dir()
            continue

        assert target_path.is_file()
        assert target_path.read_text() == path.read_text()
