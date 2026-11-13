#!/bin/sh
# Build the site, then finish the grounding map (see tools/ground_map.py).
# Use this instead of a bare `nopekit site build`: the build rewrites the map.
set -e
cd "$(dirname "$0")/.."
: "${PYTHONPATH:?set PYTHONPATH to <nopekit>/src}"
python3 -m nopekit site build
python3 tools/ground_map.py
