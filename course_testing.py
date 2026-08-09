from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from uuid import uuid4


def load_target(test_file: str) -> ModuleType:
    lesson_dir = Path(test_file).resolve().parents[1]
    relative = Path("practice/starter.py") if os.getenv("ASYNCIO_GUID_LEARNER") == "1" else Path("solution/reference.py")
    path = lesson_dir / relative
    name = f"asyncio_guid_target_{lesson_dir.name}_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
