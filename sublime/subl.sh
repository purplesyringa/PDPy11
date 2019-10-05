#!/usr/bin/env bash
cd ..
PYTHONPATH="$(pwd)/"
cd "$(dirname "$1")"
python -m pdpy11 --sublime "$1" --lst
