from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, TemplateError
from rich import print

from .. import exception as exc
from ..config import MetaField, Prompter, TexJamConfig
from .path import TempPath


class TexJam:
    """A class to scaffold LaTeX documents using Jinja2 templates."""

    def __init__(self, template_dir: Path, output_dir: Path) -> None:
        """Initialize TeXJam.

        Args:
            template_dir (str): The directory where LaTeX templates are stored.
            output_dir (str): The directory where the project will be created.
        """

        # initialize paths
        self.template_dir = template_dir.resolve()
        self.output_dir = output_dir.resolve()

        # load config
        config_candidates = [
            self.template_dir / 'texjam.json',
            self.template_dir / '.texjam.json',
            self.template_dir / 'texjam.yaml',
            self.template_dir / '.texjam.yaml',
            self.template_dir / 'texjam.yml',
            self.template_dir / '.texjam.yml',
        ]
        config_file = None
        for candidate in config_candidates:
            if candidate.exists():
                config_file = candidate
                break
        if config_file is None:
            raise exc.TexJamScaffoldConfigNotFoundException()

        with config_file.open('r', encoding='utf-8') as f:
            if config_file.suffix in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)

        self.config = TexJamConfig.model_validate(config_data)

    @property
    def template_source_dir(self) -> Path:
        """The source directory of the template."""
        return self.template_dir / self.config.source_dir

    @property
    def template_plugin_dir(self) -> Path:
        """The plugins directory of the template."""
        return self.template_dir / self.config.plugin_dir

    def jinja_render(self, content: str) -> str:
        """Render content using the Jinja2 environment.

        Args:
            content (str): The content to be rendered.

        Returns:
            str: The rendered content.
        """
        try:
            template = self.env.from_string(content)
            return template.render(self.metadata)
        except TemplateError as e:
            raise exc.TexJamTemplateStringException(template_string=content, cause=e)

    def load_plugins(self) -> None:
        """Load plugins."""
        if not self.template_plugin_dir.exists():
            self.plugins = []

        else:
            for script_file in self.template_plugin_dir.glob('*.py'):
                module_name = script_file.stem
                spec = spec_from_file_location(module_name, script_file)
                if spec and spec.loader:
                    module = module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

            self.plugins: list[TexJamPlugin] = []
            for plugin_cls in TexJamPlugin.plugins:
                plugin_instance = plugin_cls(texjam=self)
                plugin_instance.on_load()
                self.plugins.append(plugin_instance)

        self.env = Environment(**self.config.jinja.model_dump())

    def prompt(self, data: dict | None = None) -> None:
        """Prompt the user for metadata values."""
        # print welcome message
        print(
            f'[bold green]TeXJam[/bold green] - Scaffolding project: '
            f'[bold]{self.config.name}[/bold]'
        )

        # prompt for metadata
        self.metadata: dict[str, Any] = {}
        prompter = Prompter(self)
        for name, field in self.config.meta.items():
            # pre-prompt hook
            skip_prompt = False
            for plugin in self.plugins:
                result = plugin.pre_prompt(name, field)
                if result is True:
                    skip_prompt = True
                    break
            if skip_prompt:
                continue

            # prompt user
            if data is not None and name in data:
                value = data[name]
            else:
                value = prompter.prompt_meta_field(name, field)

            # post-prompt hook
            intercept_store = False
            for plugin in self.plugins:
                result = plugin.post_prompt(name, field, value)
                if result is True:
                    intercept_store = True
                    break
            if intercept_store:
                continue

            self.metadata[name] = value

    def render(self) -> None:
        """Render the templates and create the project structure."""

        # initialize output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # initialize plugins
        for plugin in self.plugins:
            plugin.initialize()

        # gather template paths
        if not self.template_source_dir.exists():
            raise exc.TexJamScaffoldSourceDirNotFoundException(
                source_dir=self.template_source_dir.as_posix()
            )

        temp_paths = []
        for path in self.template_source_dir.rglob('*'):
            if path.is_file() or path.is_dir():
                relative_path = path.relative_to(self.template_source_dir)
                parts = [
                    self.env.from_string(part).render(self.metadata)
                    for part in relative_path.parts
                ]
                if any(part == '' for part in parts):
                    continue  # skip paths with empty parts
                rendered_path = Path(*parts)
                temp_path = TempPath(raw=path, rendered=rendered_path)
                temp_paths.append(temp_path)

        for plugin in self.plugins:
            modified_paths = plugin.on_paths(temp_paths)
            if modified_paths is not None:
                temp_paths = modified_paths

        # create files and directories
        for temp_path in sorted(temp_paths, key=lambda p: p.rendered):
            for plugin in self.plugins:
                plugin.pre_create(temp_path)

            target_path = self.output_dir / temp_path.rendered
            if temp_path.is_dir:
                if target_path.exists():
                    raise exc.TexJamScaffoldPathAlreadyExistsException(path=temp_path)
                else:
                    target_path.mkdir(parents=True, exist_ok=False)
            else:
                if not target_path.parent.exists():
                    # Parent directory does not exist.
                    # This should not happen because paths are sorted
                    # so that parent directories are created first.
                    raise RuntimeError(
                        f'Parent directory {target_path.parent} does not exist.'
                    )

                # render content
                content = temp_path.content
                if isinstance(content, str):
                    template = self.env.from_string(content)
                    rendered_content = template.render(self.metadata)
                    for plugin in self.plugins:
                        modified_content = plugin.on_render(temp_path, rendered_content)
                        if modified_content is not None:
                            rendered_content = modified_content
                    target_path.write_text(rendered_content, encoding='utf-8')
                else:
                    target_path.write_bytes(content)

            if temp_path.mode is not None:
                target_path.chmod(temp_path.mode)

            for plugin in self.plugins:
                plugin.post_create(temp_path)

        # finalize plugins
        for plugin in self.plugins:
            plugin.finalize()


class TexJamPlugin:
    """Abstract base class for TeXJam plugins."""

    plugins = []

    def __init_subclass__(cls) -> None:
        if not cls.__name__.startswith('_'):
            cls.plugins.append(cls)
        return super().__init_subclass__()

    def __init__(self, *, texjam: TexJam) -> None:
        self.texjam = texjam

    @property
    def env(self) -> Environment:
        """The Jinja2 environment from TeXJam."""
        return self.texjam.env

    @property
    def config(self) -> TexJamConfig:
        """The TeXJam configuration."""
        return self.texjam.config

    @property
    def metadata(self) -> dict[str, Any]:
        """The TeXJam metadata."""
        return self.texjam.metadata

    def render(self, content: str) -> str:
        """Render content using the plugin's Jinja2 environment.

        Args:
            content (str): The content to be rendered.

        Returns:
            str: The rendered content.
        """
        template = self.texjam.env.from_string(content)
        return template.render(self.metadata)

    def on_load(self) -> None:
        """Hook called when the plugin is loaded."""
        pass

    def pre_prompt(self, name: str, field: MetaField) -> bool | None:
        """Hook called before prompting for a metadata field.

        Args:
            name (str): The name of the metadata field.
            field (MetaField): The metadata field.
        Returns:
            bool | None: Return True to skip prompting for this field,
        """
        pass

    def post_prompt(self, name: str, field: MetaField, value: Any) -> bool | None:
        """Hook called after prompting for a metadata field.

        Args:
            name (str): The name of the metadata field.
            field (MetaField): The metadata field.
            value (Any): The value entered by the user.
        Returns:
            bool | None: Return True to intercept and not store the value.
        """
        pass

    def initialize(self) -> None:
        """Hook called during initialization."""
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
