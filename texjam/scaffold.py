from __future__ import annotations

import sys
import tomllib
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

from jinja2 import Environment, TemplateError

from .config import MetaField, TexJamConfig
from .exception import (
    TexJamScaffoldConfigNotFoundException,
    TexJamScaffoldPathAlreadyExistsException,
    TexJamScaffoldSourceDirNotFoundException,
    TexJamTemplateStringException,
)
from .path import TempPath


class TexJam:
    """A class to scaffold LaTeX documents using Jinja2 templates."""

    def __init__(self, template_dir: Path, output_dir: Path) -> None:
        """Initialize TexJam.

        Args:
            template_dir (str): The directory where LaTeX templates are stored.
            output_dir (str): The directory where the project will be created.
        """

        # initialize paths
        self.template_dir = template_dir.resolve()
        self.output_dir = output_dir.resolve()

        # load config
        config_candidates = [
            template_dir / 'texjam.toml',
            template_dir / '.texjam.toml',
        ]
        config_file = None
        for candidate in config_candidates:
            if candidate.exists():
                config_file = candidate
                break
        if config_file is None:
            raise TexJamScaffoldConfigNotFoundException()

        with config_file.open('rb') as f:
            data = tomllib.load(f)
        self.config = TexJamConfig.model_validate(data)

    @property
    def template_source_dir(self) -> Path:
        """The source directory of the template."""
        return self.template_dir / self.config.template.source_dir

    @property
    def template_plugin_dir(self) -> Path:
        """The plugins directory of the template."""
        return self.template_dir / self.config.template.plugin_dir

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
            raise TexJamTemplateStringException(template_string=content, cause=e)

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

    def prompt(self) -> None:
        """Prompt the user for metadata values."""
        # print welcome message
        welcome_msg = f'Initializing project with template "{self.config.template.name}"'
        if self.config.template.authors:
            authors_str = ', '.join(self.config.template.authors)
            welcome_msg += f' by {authors_str}'
        print(welcome_msg)

        # prompt for metadata
        self.metadata: dict[str, Any] = {}
        for field in self.config.meta:
            skip_prompt = False
            for plugin in self.plugins:
                result = plugin.pre_prompt(field)
                if result is True:
                    skip_prompt = True
                    break
            if skip_prompt:
                continue

            value = field.prompt(self.env, self.metadata)
            for plugin in self.plugins:
                value = plugin.post_prompt(field, value)
            self.metadata[field.key] = value

    def render(self) -> None:
        """Render the templates and create the project structure."""

        # initialize output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # initialize plugins
        for plugin in self.plugins:
            plugin.initialize()

        # gather template paths
        if not self.template_source_dir.exists():
            raise TexJamScaffoldSourceDirNotFoundException(
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
                    raise TexJamScaffoldPathAlreadyExistsException(path=temp_path)
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
    """Abstract base class for TexJam plugins."""

    plugins = []

    def __init_subclass__(cls) -> None:
        if not cls.__name__.startswith('_'):
            cls.plugins.append(cls)
        return super().__init_subclass__()

    def __init__(self, *, texjam: TexJam) -> None:
        self.texjam = texjam

    @property
    def env(self) -> Environment:
        """The Jinja2 environment from TexJam."""
        return self.texjam.env

    @property
    def config(self) -> TexJamConfig:
        """The TexJam configuration."""
        return self.texjam.config

    @property
    def metadata(self) -> dict[str, Any]:
        """The TexJam metadata."""
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

    def pre_prompt(self, field: MetaField) -> bool | None:
        """Hook to modify a MetaField before prompting.

        Args:
            field (MetaField): The MetaField object to be processed.

        Returns:
            bool | None: If True, skip prompting for this field.
            If False or None, proceed with prompting.
        """
        pass

    def post_prompt(self, field: MetaField, value: Any) -> Any:
        """Hook called after a MetaField has been prompted.

        Args:
            field (MetaField): The MetaField object that was prompted.
            value (Any): The value that was obtained from prompting.

        Returns:
            Any: The (possibly modified) value.
        """
        return value

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
