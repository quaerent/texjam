from pathlib import Path
from typing import Annotated

import typer
from rich import print

from ..exception import TexJamException
from ..render import TexJam
from . import package as pkg
from .source import parse_source

app = typer.Typer()


@app.command()
def list() -> None:
    """List all installed TexJam packages."""
    packages = pkg.list_installed_packages()
    if not packages:
        print('No packages installed.')
        return
    print('Installed TexJam packages:')
    for package in packages:
        print(f'- {package}')


@app.command()
def install(
    *,
    source: Annotated[
        str,
        typer.Argument(
            help='Source of the TexJam package (e.g., Git URL, local path).',
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
    """Install a TexJam package."""
    parsed_source = parse_source(source)
    package_name = pkg.install_package(parsed_source, force)
    print(f'Installed package: {package_name}')


@app.command()
def uninstall(
    *,
    package: Annotated[
        str,
        typer.Argument(
            help='Name of the TexJam package to uninstall.',
        ),
    ],
) -> None:
    """Uninstall a TexJam package."""
    pkg.uninstall_package(package)
    print(f'Uninstalled package: {package}')


@app.command()
def update(
    *,
    package: Annotated[
        str,
        typer.Argument(
            help='Name of the TexJam package to update.',
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
    """Update an installed TexJam package."""
    pkg.update_package(package)
    if revision:
        pkg.checkout_package(package, revision)
    print(f'Updated package: {package}')


@app.command()
def new(
    *,
    package: Annotated[
        str,
        typer.Argument(
            help='Name of the TexJam package to use as a template.',
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
            help='Target directory for the new TexJam project.',
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
    toml_file: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help='Path to a TOML file containing metadata.',
        ),
    ] = None,
) -> None:
    """Create a new TexJam project using the template."""
    if package.startswith(('.', '/')):
        template_dir = Path(package).resolve()
    else:
        template_dir = pkg.get_package_path(package)

    if output is None:
        output = Path.cwd()

    texjam = TexJam(template_dir=template_dir, output_dir=output)
    texjam.load_plugins()
    texjam.prompt()
    texjam.render()


if __name__ == '__main__':
    app()
