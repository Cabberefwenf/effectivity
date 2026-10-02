PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin
STAMP  := $(VENV)/.installed

.PHONY: test demo mutate

$(STAMP): pyproject.toml
	@$(PYTHON) -m venv $(VENV)
	@$(BIN)/pip install --quiet -e ".[dev]"
	@touch $(STAMP)

test: $(STAMP)
	$(BIN)/python -m pytest

demo: $(STAMP)
	@$(BIN)/python -m effectivity \
		--units examples/units.csv \
		--changes examples/changes.csv \
		--material examples/material.csv \
		--incorporations examples/incorporations.csv

mutate: $(STAMP)
	$(BIN)/python tools/mutate.py
