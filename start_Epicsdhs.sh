#!/bin/bash
#start EpicsDHS in the uv-managed environment (python pinned by pyproject.toml)
cd "$(dirname "$0")"
#build the venv only when missing: exec the venv python directly so a stuck
#uv lock can never block the DHS startup
if [ ! -x .venv/bin/python ]; then
    #managed-python: uv's own CPython has libffi statically linked; the conda
    #(miniforge) python's libffi.so.8 segfaults in libca callback trampolines
    uv sync --managed-python
fi
exec .venv/bin/python EpicsDHS.py
