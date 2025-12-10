import click

from .scaffold import Scaffold


@click.group('texjam')
def cli() -> None:
    pass


@cli.command
@click.option(
    '--output-dir',
    '-o',
    type=click.Path(
        file_okay=False,
        dir_okay=True,
        path_type=str,
    ),
    default='.',
)
@click.argument(
    'template_path',
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        path_type=str,
    ),
)
def new(output_dir: str, template_path: str) -> None:
    """Create a new TexJam project using the template."""
    scaffold = Scaffold(template_dir=template_path, project_dir=output_dir)
    scaffold.render()
