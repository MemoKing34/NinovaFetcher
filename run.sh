#!/usr/bin/env bash
command -v git && file -d .git && git pull
test -d .venv || python -m venv .venv
./.venv/bin/python3 -m pip install -U pip -r requirements.txt
./.venv/bin/python3 -m ninova_fetcher $@
