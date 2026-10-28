"""Compatibility loading for the historical ``scripts/*.py`` entry points.

Why the scripts do not simply ``from ante.x import *``
------------------------------------------------------
The protected test suites load each script by file path and then replace module
globals on the object they get back (``adapter._run = fake``). A re-export
wrapper would receive the assignment while the real functions kept reading the
package module's globals, so the tests would stop testing anything.

``adopt`` therefore executes the implementation's source inside the script's own
namespace. The code lives once, in ``ante/``; the script is a five-line shim; and
the namespace that tests patch is the namespace the functions read. Running the
script as ``__main__`` still runs the implementation's ``__main__`` block.

``load_script`` is the single replacement for the ``spec_from_file_location``
idiom that scripts used to load one another by path.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from ante.paths import SCRIPTS


def adopt(namespace: dict, module: str) -> None:
    """Run the source of ``module`` (an ``ante.*`` dotted name) in ``namespace``."""
    spec = importlib.util.find_spec(module)
    if spec is None or spec.origin is None:
        raise ImportError(f'cannot locate {module}')
    source = Path(spec.origin).read_text(encoding='utf-8')
    namespace.setdefault('__builtins__', __builtins__)
    exec(compile(source, spec.origin, 'exec'), namespace)


def load_script(filename: str, name: str | None = None) -> ModuleType:
    """Load ``scripts/<filename>`` as a fresh module object, as the scripts did."""
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(name or filename.replace('-', '_')[:-3], path)
    if spec is None or spec.loader is None:
        raise ImportError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_on_path(root: Path) -> None:
    """Make the repository importable without shadowing the standard library."""
    entry = str(root)
    if entry not in sys.path:
        sys.path.append(entry)
