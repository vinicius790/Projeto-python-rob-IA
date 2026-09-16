"""Compatibility launcher for the evolved application.

Prefer ``robia serve`` after installing the project.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("robia_ops.main:app", host="127.0.0.1", port=8000)
