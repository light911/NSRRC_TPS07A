#!/bin/bash
#start EpicsDHS in the uv-managed environment (python pinned by pyproject.toml)
cd "$(dirname "$0")"
#build the venv only when missing: exec the venv python directly so a stuck
#uv lock can never block the DHS startup
if [ ! -x .venv/bin/python ]; then
    uv sync
fi
exec .venv/bin/python EpicsDHS.py
