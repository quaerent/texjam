from pathlib import Path
from typing import overload

from binaryornot.check import is_binary


class TempPath:
    """A class representing a template file or directory path."""

    @overload
    def __init__(self, *, raw: Path, rendered: Path) -> None: ...

    @overload
    def __init__(
        self,
        *,
        rendered: Path,
        is_dir: bool,
        mode: int | None = None,
        content: str | bytes | None = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        raw: Path | None = None,
        rendered: Path,
        is_dir: bool | None = None,
        mode: int | None = None,
        content: str | bytes | None = None,
    ) -> None:
        if raw is None:
            if is_dir is None:
                raise ValueError('is_dir must be provided for virtual paths.')
            if not is_dir and content is None:
                content = b''

        self.raw = raw
        self.rendered = rendered
        self._is_dir = is_dir
        self._mode = mode
        self._content = content

    @property
    def is_dir(self) -> bool:
        """Determine if the path represents a directory."""
        if self._is_dir is not None:
            return self._is_dir
        if self.raw:
            self._is_dir = self.raw.is_dir()
            return self._is_dir
        raise ValueError('is_dir is not available.')

    @is_dir.setter
    def is_dir(self, value: bool) -> None:
        """Set whether the path represents a directory."""
        self._is_dir = value

    @property
    def mode(self) -> int | None:
        """Get the file mode, if applicable."""
        if self._mode is not None:
            return self._mode
        if self.raw and self.raw.exists():
            self._mode = self.raw.stat().st_mode
            return self._mode
        return None

    @mode.setter
    def mode(self, value: int | None) -> None:
        """Set the file mode."""
        self._mode = value

    @property
    def content(self) -> str | bytes:
        """Get the content of the file."""
        if self.is_dir:
            raise ValueError('Directories do not have content.')
        if self._content is not None:
            return self._content
        if self.raw and self.raw.exists():
            if is_binary(str(self.raw)):
                self._content = self.raw.read_bytes()
            else:
                self._content = self.raw.read_text(encoding='utf-8')
            return self._content
        raise ValueError('Content is not available.')

    @content.setter
    def content(self, value: str | bytes) -> None:
        """Set the content of the file."""
        self._content = value
