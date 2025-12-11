import subprocess
from pathlib import Path

from .source import Source

PACKAGE_DIR = Path.home() / '.texjam' / 'packages'


def ensure_install_dir() -> None:
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)


def install_package(source: Source) -> str:
    """Install a package from the given source.

    Args:
        source (Source): The source of the package to install.
    """
    ensure_install_dir()
    package_path = PACKAGE_DIR / source.name
    if package_path.exists():
        raise FileExistsError(f'Package {source.name} is already installed.')
    source.download(package_path)
    return source.name


def update_package(package_name: str) -> None:
    """Update an installed package.

    Args:
        package_name (str): The name of the package to update.
    """
    package_path = PACKAGE_DIR / package_name
    if not package_path.exists():
        raise FileNotFoundError(f'Package {package_name} is not installed.')
    subprocess.run(['git', 'checkout', 'main'], cwd=str(package_path))
    subprocess.run(['git', 'pull'], cwd=str(package_path))


def checkout_package(package_name: str, revision: str) -> None:
    """Checkout a specific revision of an installed package.

    Args:
        package_name (str): The name of the package to checkout.
        revision (str): The revision (branch, tag, or commit hash) to checkout.
    """
    package_path = PACKAGE_DIR / package_name
    if not package_path.exists():
        raise FileNotFoundError(f'Package {package_name} is not installed.')
    subprocess.run(['git', 'checkout', revision], cwd=str(package_path))


def uninstall_package(package_name: str) -> None:
    """Uninstall an installed package.

    Args:
        package_name (str): The name of the package to uninstall.
    """
    package_path = PACKAGE_DIR / package_name
    if not package_path.exists():
        raise FileNotFoundError(f'Package {package_name} is not installed.')
    subprocess.run(['rm', '-rf', str(package_path)])


def list_installed_packages() -> list[str]:
    """List all installed packages.

    Returns:
        list[str]: A list of installed package names.
    """
    ensure_install_dir()
    return [p.name for p in PACKAGE_DIR.iterdir() if p.is_dir()]


def get_package_path(package_name: str) -> Path:
    """Get the path of an installed package.

    Args:
        package_name (str): The name of the package.
    Returns:
        Path: The path to the installed package.
    """
    path = PACKAGE_DIR / package_name
    if not path.exists():
        raise FileNotFoundError(f'Package {package_name} is not installed.')
    return path
