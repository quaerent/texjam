import json
import sys
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich import print

from ..render import TexJam
from . import package as pkg
from .source import parse_source

app = typer.Typer()


def alias(*names: str):
    def decorator(func):
        func.__doc__ += f' (also {", ".join(repr(name) for name in names)})'
        for name in names:
            app.command(
                name=name,
                hidden=True,
                help=f'Alias for `{func.__name__}`.',
            )(func)
        return func

    return decorator


@app.callback()
def callback():
    """TeXJam CLI - A tool for managing LaTeX project templates."""
    pass


@app.command()
@alias('ls')
def list() -> None:
    """List all installed TeXJam packages."""
    packages = pkg.list_installed_packages()
    if not packages:
        print('No packages installed.')
        return
    print('Installed TeXJam packages:')
    for package in packages:
        print(f'- {package}')


@app.command()
@alias('add', 'i')
def install(
    *,
    source: Annotated[
        str,
        typer.Argument(
            help='Source of the TeXJam package (e.g., Git URL, local path).',
        ),
    ],
    force: Annotated[
        bool,
        typer.Option(
            '--force',
            '-f',
            help='Force reinstallation if already installed.',
        ),
    ] = False,
) -> None:
    """Install a TeXJam package."""
    parsed_source = parse_source(source)
    package_name = pkg.install_package(parsed_source, force)
    print(f'Installed package: {package_name}')


@app.command()
@alias('remove', 'rm', 'un')
def uninstall(
    *,
    package: Annotated[
        str,
        typer.Argument(
            help='Name of the TeXJam package to uninstall.',
        ),
    ],
) -> None:
    """Uninstall a TeXJam package."""
    pkg.uninstall_package(package)
    print(f'Uninstalled package: {package}')


@app.command()
@alias('up')
def update(
    *,
    package: Annotated[
        str,
        typer.Argument(
            help='Name of the TeXJam package to update.',
        ),
    ],
    revision: Annotated[
        str | None,
        typer.Option(
            '--revision',
            '-r',
            help='Revision to checkout.',
        ),
    ] = None,
) -> None:
    """Update an installed TeXJam package."""
    pkg.update_package(package)
    if revision:
        pkg.checkout_package(package, revision)
    print(f'Updated package: {package}')


@app.command()
@alias('new', 'init')
def create(
    *,
    package: Annotated[
        str,
        typer.Argument(
            help='Name of the TeXJam package to use as a template.',
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            '--output',
            '-o',
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=True,
            help='Target directory for the new TeXJam project.',
        ),
    ] = None,
    data: Annotated[
        str | None,
        typer.Option(
            help='JSON string representing metadata.',
        ),
    ] = None,
    json_file: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help='Path to a JSON file containing metadata.',
        ),
    ] = None,
    yaml_file: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help='Path to a YAML file containing metadata.',
        ),
    ] = None,
) -> None:
    """Create a new TeXJam project using the template."""
    if package.startswith(('.', '/')):
        template_dir = Path(package).resolve()
    else:
        template_dir = pkg.get_package_path(package)

    if output is None:
        output = Path.cwd()

    # load metadata if provided
    if data:
        metadata = json.loads(data)
    elif json_file:
        with json_file.open('r') as f:
            metadata = json.load(f)
    elif yaml_file:
        with yaml_file.open('r') as f:
            metadata = yaml.safe_load(f)
    else:
        metadata = None

    if metadata is not None and not isinstance(metadata, dict):
        print('[red]Error:[/red] Metadata must be an object.', file=sys.stderr)
        raise typer.Exit(code=1)

    texjam = TexJam(template_dir=template_dir, output_dir=output)
    texjam.load_plugins()
    texjam.prompt(data=metadata)
    texjam.render()


if __name__ == '__main__':
    app()
