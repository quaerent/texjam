from pathlib import Path

import click

from .package import (
    checkout_package,
    get_package_path,
    install_package,
    list_installed_packages,
    uninstall_package,
    update_package,
)
from .scaffold import TexJam
from .source import parse_source


@click.group('texjam')
@click.version_option(None, '--version', '-v')
def cli() -> None:
    pass


@cli.command
def list() -> None:
    """List all installed TexJam packages."""
    packages = list_installed_packages()
    if not packages:
        click.echo('No packages installed.')
        return
    click.echo('Installed TexJam packages:')
    for pkg in packages:
        click.echo(f'- {pkg}')


@cli.command
@click.argument('source', type=str)
def install(source: str) -> None:
    """Install a TexJam package."""
    parsed_source = parse_source(source)
    package_name = install_package(parsed_source)
    click.echo(f'Installed package: {package_name}')


@cli.command
@click.argument('package', type=str)
def uninstall(package: str) -> None:
    """Uninstall a TexJam package."""
    uninstall_package(package)
    click.echo(f'Uninstalled package: {package}')


@cli.command
@click.option('--revision', '-r', type=str, help='Revision to checkout.')
@click.argument('package', type=str)
def update(package: str, revision: str | None) -> None:
    """Update an installed TexJam package."""
    update_package(package)
    if revision:
        checkout_package(package, revision)
    click.echo(f'Updated package: {package}')


@cli.command
@click.argument('package', type=str)
@click.argument(
    'output',
    default='.',
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=Path,
    ),
)
def new(output: Path, package: str) -> None:
    """Create a new TexJam project using the template."""
    if package.startswith(('.', '/')):
        template_dir = Path(package).resolve()
    else:
        template_dir = get_package_path(package)

    texjam = TexJam(template_dir=template_dir, output_dir=output)
    texjam.load_plugins()
    texjam.prompt()
    texjam.render()


if __name__ == '__main__':
    cli()
