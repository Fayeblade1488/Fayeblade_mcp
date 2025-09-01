PY=python3

install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m playwright install chromium

run:
	$(PY) src/venice_browser_mcp.py

run-hard:
	$(PY) src/venice_browser_mcp.py --framing content-length

run-persist:
	$(PY) src/venice_browser_mcp.py --persist --storage ./cookies.json
