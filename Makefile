.PHONY: install run-line run-cl test-line test-cl fmt clean

PY=python3

install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m playwright install chromium

run-line:
	MCP_FRAMING=line HEADLESS=true $(PY) -m venice.cli

run-cl:
	MCP_FRAMING=content-length HEADLESS=true $(PY) -m venice.cli

test-line:
	$(PY) examples/line_host.py

test-cl:
	$(PY) examples/hard_mcp_host.py

fmt:
	@echo "Nothing fancy; this repo is tiny."

test:
	@echo "Running test suite..."
	coverage run -m pytest

coverage:
	@echo "Running test suite with coverage..."
	coverage run -m pytest
	@echo "Combining coverage data..."
	coverage combine
	@echo "Generating coverage report..."
	coverage report -m

clean:
	rm -rf __pycache__ **/__pycache__ .pytest_cache logs *.log state.json
