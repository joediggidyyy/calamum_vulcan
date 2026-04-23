"""Runtime dependency satisfaction and bounded self-heal helpers."""

from __future__ import annotations

import importlib
from importlib import metadata
import logging
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Optional
from typing import Sequence


PACKAGE_DISTRIBUTION_NAME = 'calamum_vulcan'
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = PROJECT_ROOT / 'pyproject.toml'
_REQUIREMENT_NAME_PATTERN = re.compile(r'^\s*([A-Za-z0-9_.-]+)')
_REQUIREMENT_IMPORT_MODULES = {
    'pyside6': ('PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'),
    'pyusb': ('usb.backend.libusb1', 'usb.core', 'usb.util'),
}
_RUNTIME_DEPENDENCY_REPAIR_ATTEMPTED = False
_RUNTIME_DEPENDENCY_REPAIR_NOTE = None  # type: Optional[str]


def _normalize_requirement_name(requirement: str) -> str:
    """Return the normalized distribution name from one requirement string."""

    match = _REQUIREMENT_NAME_PATTERN.match(requirement)
    if match is None:
        return requirement.strip().lower()
    return match.group(1).strip().lower()


def _normalize_requirement_text(requirement: str) -> str:
    """Return one comparable requirement string representation."""

    return re.sub(r'\s+', '', requirement).lower()


def _base_requirements(requirements: Optional[Sequence[str]]) -> tuple[str, ...]:
    """Return only the base runtime requirements, excluding extras markers."""

    if not requirements:
        return ()
    normalized = []
    for requirement in requirements:
        text = str(requirement).strip()
        if not text:
            continue
        if 'extra ==' in text.lower():
            continue
        normalized.append(text)
    return tuple(normalized)


def _declared_runtime_requirements() -> tuple[str, ...]:
    """Return the declared runtime dependency set for Calamum Vulcan."""

    if PYPROJECT_PATH.exists():
        try:
            project_data = tomllib.loads(PYPROJECT_PATH.read_text(encoding='utf-8'))
        except (OSError, tomllib.TOMLDecodeError):
            project_data = None
        if project_data is not None:
            dependencies = project_data.get('project', {}).get('dependencies', ())
            return _base_requirements(tuple(str(item) for item in dependencies))
    try:
        installed_requirements = metadata.requires(PACKAGE_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return ()
    return _base_requirements(installed_requirements)


def _installed_distribution_requirements() -> Optional[tuple[str, ...]]:
    """Return the installed Calamum Vulcan base requirements when metadata exists."""

    try:
        installed_requirements = metadata.requires(PACKAGE_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return None
    return _base_requirements(installed_requirements)


def _runtime_dependency_metadata_is_stale(
    declared_requirements: Sequence[str],
) -> bool:
    """Return whether installed distribution metadata has drifted from source truth."""

    installed_requirements = _installed_distribution_requirements()
    if installed_requirements is None:
        return False
    declared_set = {
        _normalize_requirement_text(requirement)
        for requirement in declared_requirements
    }
    installed_set = {
        _normalize_requirement_text(requirement)
        for requirement in installed_requirements
    }
    return declared_set != installed_set


def _import_modules_for_requirement(requirement: str) -> bool:
    """Return whether the runtime modules for one requirement import cleanly."""

    requirement_name = _normalize_requirement_name(requirement)
    module_names = _REQUIREMENT_IMPORT_MODULES.get(
        requirement_name,
        (requirement_name.replace('-', '_'),),
    )
    try:
        for module_name in module_names:
            importlib.import_module(module_name)
    except Exception:
        return False
    return True


def _missing_runtime_requirements(
    declared_requirements: Sequence[str],
) -> tuple[str, ...]:
    """Return the declared requirements whose runtime modules are unavailable."""

    missing_requirements = []
    for requirement in declared_requirements:
        if _import_modules_for_requirement(requirement):
            continue
        missing_requirements.append(requirement)
    return tuple(missing_requirements)


def _resolve_dependency_python_executable() -> Optional[Path]:
    """Resolve the best Python executable to use for runtime dependency repair."""

    executable = Path(sys.executable)
    candidates = [
        executable.with_name('python.exe'),
        executable,
        Path(sys.prefix) / 'Scripts' / 'python.exe',
        Path(sys.prefix) / 'Scripts' / executable.name,
    ]
    seen = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.append(candidate)
        if candidate.exists():
            return candidate
    return None


def _dependency_install_subprocess_kwargs() -> dict[str, object]:
    """Return subprocess options that avoid opening a visible console on Windows."""

    if not sys.platform.startswith('win'):
        return {}
    kwargs = {}  # type: dict[str, object]
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    if creationflags:
        kwargs['creationflags'] = creationflags
    startupinfo_factory = getattr(subprocess, 'STARTUPINFO', None)
    use_show_window = getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)
    hide_window = getattr(subprocess, 'SW_HIDE', 0)
    if startupinfo_factory is not None:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= use_show_window
        startupinfo.wShowWindow = hide_window
        kwargs['startupinfo'] = startupinfo
    return kwargs


def _last_non_empty_line(*values: Optional[str]) -> Optional[str]:
    """Return the last non-empty text line from the provided values."""

    for value in reversed(values):
        if value is None:
            continue
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if lines:
            return lines[-1]
    return None


def _build_dependency_repair_command(
    declared_requirements: Sequence[str],
) -> Optional[list[str]]:
    """Return the bounded pip command used to rehydrate runtime dependencies."""

    executable = _resolve_dependency_python_executable()
    if executable is None:
        return None
    command = [
        str(executable),
        '-m',
        'pip',
        'install',
        '--disable-pip-version-check',
        '--no-input',
    ]
    if PYPROJECT_PATH.exists():
        command.extend(['-e', str(PROJECT_ROOT)])
        return command
    if not declared_requirements:
        return None
    command.extend(declared_requirements)
    return command


def _format_runtime_dependency_gap(
    missing_requirements: Sequence[str],
    metadata_stale: bool,
) -> str:
    """Return one short explanation of the remaining dependency gap."""

    details = []
    if missing_requirements:
        details.append(
            'missing runtime requirements: {requirements}'.format(
                requirements=', '.join(missing_requirements),
            )
        )
    if metadata_stale:
        details.append(
            'installed Calamum Vulcan metadata still does not match pyproject.toml'
        )
    if not details:
        return 'unknown dependency gap'
    return '; '.join(details)


def last_runtime_dependency_repair_note() -> Optional[str]:
    """Return the last runtime dependency repair note recorded in this process."""

    return _RUNTIME_DEPENDENCY_REPAIR_NOTE


def attempt_runtime_dependency_repair(logger: logging.Logger) -> Optional[str]:
    """Attempt one bounded repair of the declared runtime dependency set."""

    global _RUNTIME_DEPENDENCY_REPAIR_ATTEMPTED
    global _RUNTIME_DEPENDENCY_REPAIR_NOTE

    declared_requirements = _declared_runtime_requirements()
    missing_requirements = _missing_runtime_requirements(declared_requirements)
    metadata_stale = _runtime_dependency_metadata_is_stale(declared_requirements)
    if not missing_requirements and not metadata_stale:
        return None

    if _RUNTIME_DEPENDENCY_REPAIR_ATTEMPTED:
        return _RUNTIME_DEPENDENCY_REPAIR_NOTE

    _RUNTIME_DEPENDENCY_REPAIR_ATTEMPTED = True
    command = _build_dependency_repair_command(declared_requirements)
    if command is None:
        _RUNTIME_DEPENDENCY_REPAIR_NOTE = (
            'Automatic runtime dependency repair could not start because no '
            'Python executable or dependency target was resolved for this environment.'
        )
        logger.warning(_RUNTIME_DEPENDENCY_REPAIR_NOTE)
        return _RUNTIME_DEPENDENCY_REPAIR_NOTE

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **_dependency_install_subprocess_kwargs(),
        )
    except Exception as error:
        _RUNTIME_DEPENDENCY_REPAIR_NOTE = (
            'Automatic runtime dependency repair could not start in this '
            'environment: {error}'.format(error=error)
        )
        logger.warning(_RUNTIME_DEPENDENCY_REPAIR_NOTE)
        return _RUNTIME_DEPENDENCY_REPAIR_NOTE

    if completed.returncode != 0:
        detail = _last_non_empty_line(completed.stderr, completed.stdout)
        _RUNTIME_DEPENDENCY_REPAIR_NOTE = (
            'Automatic runtime dependency repair failed in this environment: '
            '{detail}'.format(
                detail=(
                    detail
                    or 'pip exited with code {code}.'.format(
                        code=completed.returncode,
                    )
                ),
            )
        )
        logger.warning(_RUNTIME_DEPENDENCY_REPAIR_NOTE)
        return _RUNTIME_DEPENDENCY_REPAIR_NOTE

    remaining_missing_requirements = _missing_runtime_requirements(declared_requirements)
    remaining_metadata_stale = _runtime_dependency_metadata_is_stale(
        declared_requirements,
    )
    if remaining_missing_requirements or remaining_metadata_stale:
        _RUNTIME_DEPENDENCY_REPAIR_NOTE = (
            'Automatic runtime dependency repair ran, but the declared '
            'runtime dependency set is still incomplete: {detail}'.format(
                detail=_format_runtime_dependency_gap(
                    remaining_missing_requirements,
                    remaining_metadata_stale,
                ),
            )
        )
        logger.warning(_RUNTIME_DEPENDENCY_REPAIR_NOTE)
        return _RUNTIME_DEPENDENCY_REPAIR_NOTE

    if '-e' in command:
        _RUNTIME_DEPENDENCY_REPAIR_NOTE = (
            'Automatic runtime dependency repair refreshed Calamum Vulcan '
            'from the source checkout and satisfied the declared runtime '
            'dependency set for this environment.'
        )
    else:
        _RUNTIME_DEPENDENCY_REPAIR_NOTE = (
            'Automatic runtime dependency repair installed the declared '
            'runtime requirements for this environment.'
        )
    logger.info(_RUNTIME_DEPENDENCY_REPAIR_NOTE)
    return _RUNTIME_DEPENDENCY_REPAIR_NOTE