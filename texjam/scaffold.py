from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from .path import TempPath

PLUGIN_FOLDER = 'plugins'
TEMP_FOLDER = 'src'


class Scaffold:
    """A class to scaffold LaTeX documents using Jinja2 templates."""

    def __init__(self, template_dir: Path, project_dir: Path) -> None:
        """Initialize the Scaffold with the directory containing templates.

        Args:
            template_dir (str): The directory where LaTeX templates are stored.
            project_dir (str): The directory where the project will be created.
        """

        # initialize Jinja2 environment with custom delimiters for LaTeX
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            variable_start_string='[-',
            variable_end_string='-]',
            block_start_string='[%',
            block_end_string='%]',
            comment_start_string='[#',
            comment_end_string='#]',
            autoescape=False,
        )

        # read configuration file
        json_file = template_dir / 'texjam.json'
        yaml_file = template_dir / 'texjam.yaml'

        if json_file.exists():
            with json_file.open(encoding='utf-8') as f:
                metadata = json.load(f)
        elif yaml_file.exists():
            with yaml_file.open(encoding='utf-8') as f:
                metadata = yaml.safe_load(f)
        else:
            metadata = {}

        if not isinstance(metadata, dict):
            raise ValueError(
                'Configuration file must contain a dictionary at the top level.'
            )
        for key, value in metadata.items():
            if not isinstance(key, str):
                raise ValueError('All keys in the configuration must be strings.')
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise ValueError(
                    'All values in the configuration must be of type '
                    'str, int, float, bool, or None.'
                )

        self.config = ScaffoldConfig(
            template_root=template_dir / TEMP_FOLDER,
            project_root=project_dir,
            metadata=metadata,
        )

    def _load_py_plugins(self) -> list[ScaffoldPlugin]:
        """Load Scaffold plugins.

        Returns:
            list[ScaffoldPlugin]: A list of instantiated ScaffoldPlugin objects.
        """
        script_folder_path = self.config.template_root / PLUGIN_FOLDER
        if not script_folder_path.exists():
            return []

        for script_file in script_folder_path.glob('*.py'):
            module_name = script_file.stem
            spec = spec_from_file_location(module_name, script_file)
            if spec and spec.loader:
                module = module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

        return [plugin(config=self.config) for plugin in ScaffoldPlugin.plugins]

    def render(self) -> None:
        """Render the templates and create the project structure."""

        # initialize plugins
        plugins = self._load_py_plugins()
        for plugin in plugins:
            plugin.initialize()

        # gather template paths
        if not self.config.template_root.exists():
            raise FileNotFoundError('There is no src folder in the template')

        temp_paths = []
        for path in self.config.template_root.rglob('*'):
            if path.is_file() or path.is_dir():
                relative_path = path.relative_to(self.config.template_root)
                rendered_path = Path(
                    *(
                        self.env.from_string(part).render(**self.config.metadata)
                        for part in relative_path.parts
                    )
                )
                temp_path = TempPath(raw=path, rendered=rendered_path)
                temp_paths.append(temp_path)

        for plugin in plugins:
            modified_paths = plugin.on_paths(temp_paths)
            if modified_paths is not None:
                temp_paths = modified_paths

        # create files and directories
        for temp_path in sorted(temp_paths, key=lambda p: p.rendered):
            for plugin in plugins:
                plugin.pre_create(temp_path)

            target_path = self.config.project_root / temp_path.rendered
            if temp_path.is_dir:
                if target_path.exists():
                    if len(temp_path.rendered.parts) == 1:
                        raise FileExistsError(
                            f'Project directory {target_path} already exists.'
                        )
                    else:
                        raise FileExistsError(f'Directory {target_path} already exists.')
                else:
                    target_path.mkdir(parents=True, exist_ok=False)
            else:
                if not target_path.parent.exists():
                    raise FileNotFoundError(
                        f'Parent directory {target_path.parent} does not exist.'
                    )

                # render content
                content = temp_path.content
                if isinstance(content, str):
                    template = self.env.from_string(content)
                    rendered_content = template.render(**self.config.metadata)
                    for plugin in plugins:
                        modified_content = plugin.on_render(temp_path, rendered_content)
                        if modified_content is not None:
                            rendered_content = modified_content
                    target_path.write_text(rendered_content, encoding='utf-8')
                else:
                    target_path.write_bytes(content)

            if temp_path.mode is not None:
                target_path.chmod(temp_path.mode)

            for plugin in plugins:
                plugin.post_create(temp_path)

        # finalize plugins
        for plugin in plugins:
            plugin.finalize()


@dataclass(kw_only=True)
class ScaffoldConfig:
    """Dataclass to hold Scaffold configuration."""

    template_root: Path
    project_root: Path
    metadata: dict[str, Any]


class ScaffoldPlugin:
    """Abstract base class for Scaffold plugins."""

    plugins = []

    def __init_subclass__(cls) -> None:
        cls.plugins.append(cls)
        return super().__init_subclass__()

    def __init__(self, config: ScaffoldConfig) -> None:
        self.config = config

    def initialize(self) -> None:
        """Hook called during Scaffold initialization."""
        pass

    def on_paths(self, paths: list[TempPath]) -> list[TempPath] | None:
        """Hook to modify the list of TempPath objects before rendering.

        Args:
            paths (list[TempPath]): The list of TempPath objects to be processed.

        Returns:
            list[TempPath] | None: The modified list of TempPath objects,
            or None to leave unchanged.
        """
        pass

    def pre_create(self, path: TempPath):
        """Hook to modify a TempPath before it is created.

        Args:
            path (TempPath): The TempPath object to be processed.
        """
        pass

    def on_render(self, path: TempPath, rendered: str) -> str | None:
        """Hook to modify the rendered content of a TempPath.

        Args:
            path (TempPath): The TempPath object being rendered.
            rendered (str): The rendered content.

        Returns:
            str | None: The modified content, or None to leave unchanged.
        """
        pass

    def post_create(self, path: TempPath) -> None:
        """Hook called after a TempPath has been created.

        Args:
            path (TempPath): The TempPath object that was created.
        """
        pass

    def finalize(self) -> None:
        """Hook called after all paths have been created."""
        pass
