"""Compatibility database initializer.

Prefer ``robia init-db`` after installing the project.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from robia_ops.db import init_db

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
