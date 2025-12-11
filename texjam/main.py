from pathlib import Path

import click

from .scaffold import Scaffold
from .source import parse_source


@click.group('texjam')
def cli() -> None:
    pass


@cli.command
@click.option(
    '--output-dir',
    '-o',
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        path_type=Path,
    ),
    default='.',
)
@click.argument('source')
def new(output_dir: Path, source: str) -> None:
    """Create a new TexJam project using the template."""
    parsed_source = parse_source(source)
    template_dir = parsed_source.download()

    scaffold = Scaffold(template_dir=template_dir, project_dir=output_dir)

    user_input = {}
    for key, value in scaffold.config.metadata.items():
        ty = type(value) if value is not None else str
        user_input[key] = click.prompt(key, default=value, type=ty)
    scaffold.config.metadata.update(user_input)

    scaffold.render()
