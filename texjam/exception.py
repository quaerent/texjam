from typing import Literal

from jinja2 import TemplateError

from .path import TempPath


class TexJamException(Exception):
    """Base exception for TexJam."""

    pass


class TexJamPluginException(TexJamException):
    """Exception for TexJam plugin execution errors."""

    def __init__(
        self,
        *,
        plugin_name: str,
        stage: Literal[
            'on_load',
            'pre_prompt',
            'post_prompt',
            'initialize',
            'on_paths',
            'pre_create',
            'post_create',
            'on_render',
            'finalize',
        ],
        message: str,
    ):
        self.plugin_name = plugin_name
        self.stage = stage
        super().__init__(
            f"Error in plugin '{plugin_name}' during stage '{stage}': {message}"
        )


class TexJamScaffoldException(TexJamException):
    """Exception for TexJam scaffolds."""

    pass


class TexJamScaffoldConfigNotFoundException(TexJamScaffoldException):
    """Exception for when a scaffold config is not found."""

    def __init__(self):
        super().__init__('Configuration file not found.')


class TexJamScaffoldSourceDirNotFoundException(TexJamScaffoldException):
    """Exception for when a scaffold source directory is not found."""

    def __init__(self, *, source_dir: str):
        self.source_dir = source_dir
        super().__init__(f'Scaffold source directory "{source_dir}" not found.')


class TexJamScaffoldPathAlreadyExistsException(TexJamScaffoldException):
    """Exception for when a scaffold path already exists."""

    def __init__(self, *, path: TempPath):
        self.path = path
        super().__init__(f'Scaffold path "{path.rendered}" already exists.')


class TexJamTemplateException(TexJamException):
    """Exception for TexJam templates."""

    pass


class TexJamTemplateStringException(TexJamTemplateException):
    """Exception for TexJam template strings."""

    def __init__(self, *, template_string: str, cause: TemplateError):
        self.template_string = template_string
        super().__init__(f'Error in Jinja2 template "{template_string}": {cause}')


class TexJamTemplatePathException(TexJamTemplateException):
    """Exception for TexJam template paths."""

    def __init__(self, *, template_path: TempPath, cause: TemplateError):
        self.template_path = template_path
        super().__init__(f'Error in Jinja2 template {template_path}: {cause}')


class TexJamPackageException(TexJamException):
    """Exception for TexJam packages."""

    pass


class TexJamPackageAlreadyExistsException(TexJamPackageException):
    """Exception for when a package already exists."""

    def __init__(self, *, package_name: str):
        self.package_name = package_name
        super().__init__(f'Package {package_name} already exists.')


class TexJamPackageNotFoundException(TexJamPackageException):
    """Exception for when a package is not found."""

    def __init__(self, *, package_name: str):
        self.package_name = package_name
        super().__init__(f'Package {package_name} not found.')
