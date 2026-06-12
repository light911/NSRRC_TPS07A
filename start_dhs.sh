#!/bin/bash
#start EpicsDHS in the uv-managed environment (python pinned by pyproject.toml)
cd "$(dirname "$0")"
exec uv run python EpicsDHS.py
