from pathlib import Path

from texjam import TempPath, TexJamPlugin


class ExamplePlugin(TexJamPlugin):
    def initialize(self) -> None:
        self.metadata['example'] = True

    def finalize(self) -> None:
        (self.texjam.output_dir / self.metadata['slug'] / 'finalize.txt').touch()

    def on_paths(self, paths: list[TempPath]) -> list[TempPath] | None:
        path = Path(self.metadata['slug'], 'path.txt')
        paths.append(TempPath(rendered=path, is_dir=False, content=''))
        return paths

    def on_render(self, path: TempPath, rendered: str) -> str | None:
        return rendered + '\n<!-- Rendered by ExamplePlugin -->\n'


class _IgnoredPlugin(TexJamPlugin):
    def on_paths(self, paths: list[TempPath]) -> list[TempPath] | None:
        raise NotImplementedError('This plugin should be ignored.')
