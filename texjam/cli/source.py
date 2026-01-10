import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class Source(ABC):
    """Abstract base class for different types of package sources."""

    @abstractmethod
    def download(self, path: Path) -> None:
        """Download the package to the specified path.

        Args:
            path (Path): The path where the package should be downloaded.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the source."""
        pass


class LocalSource(Source):
    """Source representing a local file system path."""

    def __init__(self, path: Path) -> None:
        self._path = path.resolve()

    def download(self, path: Path) -> None:
        shutil.copytree(self._path, path)

    @property
    def name(self) -> str:
        return self._path.name


class ArchiveSource(Source):
    """Source representing an archive."""

    def __init__(self, archive_path: Path) -> None:
        self._archive_path = archive_path

    def download(self, path: Path) -> None:
        subprocess.run(['tar', '-xzf', str(self._archive_path), '-C', str(path)])

    @property
    def name(self) -> str:
        return self._archive_path.stem


class RemoteSource(Source):
    """Source representing a remote archive."""

    def __init__(self, url: str) -> None:
        self._url = url

    def download(self, path: Path) -> None:
        subprocess.run([
            'curl',
            '-L',
            self._url,
            '|',
            'tar',
            '-xzf',
            '-',
            '-C',
            str(path),
        ])

    @property
    def name(self) -> str:
        return self._url.split('/')[-1].split('.')[0]


class RepositorySource(Source):
    """Source representing a git repository."""

    def __init__(self, repo_url: str) -> None:
        self._repo_url = repo_url

    def download(self, path: Path) -> None:
        subprocess.run(['git', 'clone', self._repo_url, str(path)])

    @property
    def name(self) -> str:
        return self._repo_url.split('/')[-1].replace('.git', '')


def parse_source(source: str) -> Source:
    """Parse a source string and return the appropriate Source object.

    Args:
        source (str): The source string to parse.
    Returns:
        Source: The corresponding Source object.
    """
    if source.startswith('git+'):
        repo_url = source[len('git+') :]
        return RepositorySource(repo_url)
    elif source.startswith('gh:'):
        repo_url = f'git@github.com:{source[len("gh:") :]}.git'
        return RepositorySource(repo_url)
    elif source.startswith('gl:'):
        repo_url = f'git@gitlab.com:{source[len("gl:") :]}.git'
        return RepositorySource(repo_url)
    elif source.startswith('http://') or source.startswith('https://'):
        return RemoteSource(source)
    elif source.endswith(('.tar.gz', '.tgz', '.zip')):
        return ArchiveSource(Path(source))
    else:
        return LocalSource(Path(source))
