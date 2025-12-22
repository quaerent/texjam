from pathlib import Path

from texjam import ScaffoldPlugin
from texjam.path import TempPath


class ExamplePlugin(ScaffoldPlugin):
    def initialize(self) -> None:
        self.config.metadata['example'] = True

    def finalize(self) -> None:
        (self.config.project_root / self.config.metadata['slug'] / 'finalize.txt').touch()

    def on_paths(self, paths: list[TempPath]) -> list[TempPath] | None:
        path = Path(self.config.metadata['slug'], 'path.txt')
        paths.append(TempPath(rendered=path, is_dir=False, content=''))
        return paths

    def on_render(self, path: TempPath, rendered: str) -> str | None:
        return rendered + '\n<!-- Rendered by ExamplePlugin -->\n'
