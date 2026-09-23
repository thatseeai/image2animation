#!/usr/bin/env bash
# source/chuseok.webp -> build/layers/ -> chuseok-robot.svg
set -euo pipefail
cd "$(dirname "$0")"

# 1. split the source into layers and rebuild the background (writes build/layers/)
uv run --with pillow --with numpy --with opencv-python-headless python build/layers.py

# 2. assemble the animated SVG from those layers (writes chuseok-robot.svg)
uv run --with pillow python build/build_svg.py
