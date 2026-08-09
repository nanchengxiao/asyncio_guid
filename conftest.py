import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os


def pytest_addoption(parser):
    parser.addoption(
        "--learner",
        action="store_true",
        help="Run lesson acceptance tests against practice/starter.py instead of solution/reference.py",
    )


def pytest_configure(config):
    if config.getoption("--learner"):
        os.environ["ASYNCIO_GUID_LEARNER"] = "1"
    else:
        os.environ.pop("ASYNCIO_GUID_LEARNER", None)
