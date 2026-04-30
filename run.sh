#!/usr/bin/env bash
test -d .venv || python -m venv .venv
./.venv/bin/pip3 install -U pip -r requirements.txt
./.venv/bin/python3 -m ninova_fetcher
