export UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
export PYLINTHOME ?= $(CURDIR)/.pylint.d
UV_RUN = uv run --locked
PYTHON_PATHS = src tests tools
JSCPD = node_modules/.bin/jscpd

.PHONY: check init uv-sync npm-install pyfmt ruff ruff-check pylint jscpd \
	jscpd-py ascii test build

check: ruff-check pylint jscpd ascii test

init: uv-sync npm-install

uv-sync:
	uv sync --locked

npm-install:
	npm ci --cache .npm-cache --no-audit --no-fund

pyfmt: ruff

ruff:
	$(UV_RUN) ruff check --fix $(PYTHON_PATHS)
	$(UV_RUN) ruff format $(PYTHON_PATHS)

ruff-check:
	$(UV_RUN) ruff check $(PYTHON_PATHS)
	$(UV_RUN) ruff format --check $(PYTHON_PATHS)

pylint:
	$(UV_RUN) pylint $(PYTHON_PATHS)

$(JSCPD): package.json package-lock.json
	npm ci --cache .npm-cache --no-audit --no-fund

jscpd: $(JSCPD)
	$(JSCPD) --config .jscpd.json $(PYTHON_PATHS)

jscpd-py: jscpd

ascii:
	$(UV_RUN) python -B tools/check_ascii.py

test:
	$(UV_RUN) python -B -m unittest discover -s tests

build:
	uv build
