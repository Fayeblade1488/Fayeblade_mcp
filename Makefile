.PHONY: install run-line run-cl test-line test-cl fmt clean

PY=python3

install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m playwright install chromium

run-line:
	MCP_FRAMING=line HEADLESS=true $(PY) src/venice_browser_mcp.py

run-cl:
	MCP_FRAMING=content-length HEADLESS=true $(PY) src/venice_browser_mcp.py

test-line:
	$(PY) examples/line_host.py

test-cl:
	$(PY) examples/hard_mcp_host.py

fmt:
	@echo "Nothing fancy; this repo is tiny."

test:
	@echo "Running test suite..."
	$(PY) -m pytest

coverage:
	@echo "Running test suite with coverage..."
	$(PY) -m pytest --cov=src

clean:
	rm -rf __pycache__ **/__pycache__ .pytest_cache logs *.log state.json
