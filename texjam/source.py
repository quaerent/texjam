import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import TemporaryDirectory


class Source(ABC):
    @abstractmethod
    def download(self) -> Path:
        """Download or retrieve the source and return the local path."""
        pass


class GitSource(Source):
    def __init__(self, repo_url: str, revision: str | None = None) -> None:
        self.repo_url = repo_url
        self.revision = revision

    def download(self) -> Path:
        with TemporaryDirectory(delete=False) as tmpdir:
            subprocess.run(['git', 'clone', self.repo_url, tmpdir], check=True)
            if self.revision:
                subprocess.run(['git', 'checkout', self.revision], cwd=tmpdir, check=True)
            return Path(tmpdir)


class LocalSource(Source):
    def __init__(self, local_path: Path) -> None:
        self.local_path = local_path

    def download(self) -> Path:
        return self.local_path


class ArchiveSource(Source):
    def __init__(self, archive_path: Path) -> None:
        self.archive_path = archive_path

    def download(self) -> Path:
        with TemporaryDirectory(delete=False) as tmpdir:
            subprocess.run(
                ['tar', '-xf', str(self.archive_path), '-C', tmpdir], check=True
            )
            return Path(tmpdir)


def parse_source(source_str: str) -> Source:
    if source_str.startswith('git+'):
        repo_info = source_str[4:]
        if '@' in repo_info:
            repo_url, revision = repo_info.split('@', 1)
        else:
            repo_url, revision = repo_info, None
        return GitSource(repo_url, revision)
    elif source_str.startswith('gh:'):
        repo_info = source_str[3:]
        if '@' in repo_info:
            repo_path, revision = repo_info.split('@', 1)
        else:
            repo_path, revision = repo_info, None
        repo_url = f'https://github.com/{repo_path}.git'
        return GitSource(repo_url, revision)
    elif source_str.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.zip')):
        archive_path = Path(source_str)
        return ArchiveSource(archive_path)
    else:
        local_path = Path(source_str)
        return LocalSource(local_path)
