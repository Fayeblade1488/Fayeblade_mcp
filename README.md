# Venice Browser MCP Bridge
<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/81bae856-9692-4b48-98a9-c8bd213935a7" />

## What this is:
A tiny, production-minded **browser bridge** that speaks a JSON-RPC-ish protocol over **stdin/stdout**.

## Features
- **Cross-Platform**: Works on Linux, macOS, and Windows.
- **Two Framing Modes**: Supports both `line` (default) and `content-length` framing.
- **Persistent Sessions**: Uses Playwright for real browser automation with optional cookie/session state persistence.
- **Safe I/O**: Hardened against common `asyncio` pitfalls to ensure clean protocol communication.

---

## Quick Start

#### 1. Create an isolated environment (recommended)
```bash
python3 -m venv .venv && source .venv/bin/activate
```

#### 2. Install the package
```bash
# This will also install dependencies like Playwright
pip install .

# Install the required browser
playwright install chromium
```

#### 3. Run the bridge
```bash
# The 'venice' command is now available thanks to the installation
MCP_FRAMING=line HEADLESS=true venice
```

#### 4. In another terminal, run an example host
```bash
python3 examples/line_host.py
```

### Expect output like:
```
Navigate...
{"id":"nav-1","result":{"ok":true,"final_url":"https://example.com/","title":"Example Domain"}}
```

---

## Repo Layout

```plaintext
venice-browser-mcp/
├─ venice/
│  ├─ bridge.py        # Framing, browser logic, and RPC dispatcher
│  ├─ cli.py           # Main entry point for the command-line script
│  └─ config.py        # Environment variable configuration
├─ examples/
│  ├─ line_host.py
│  └─ hard_mcp_host.py
├─ tests/
│  ├─ ... (test files)
├─ docs/
│  ├─ ... (documentation)
├─ pyproject.toml      # Project definition and dependencies
├─ Makefile
├─ .gitignore
├─ LICENSE
└─ README.md
```

---

## Configuration

The bridge is configured via environment variables.

| Variable                 | Meaning                                                                              | Default            |
|-------------------------|--------------------------------------------------------------------------------------|--------------------|
| `MCP_FRAMING`           | `line` or `content-length`                                                           | `line`             |
| `HEADLESS`              | `true` or `false` for Playwright                                                     | `true`             |
| `MCP_STORAGE_STATE`     | Path to `storage_state` JSON for persistent sessions                                 | `state.json`       |
| `NAV_TIMEOUT`           | Navigation timeout ms                                                                | `30000`            |
| `BROWSER`               | Browser name `chromium` \| `firefox` \| `webkit`                                     | `chromium`         |

> **Note:** All logs go to **stderr**. **Never** print non-protocol text to stdout, or you will corrupt the transport.

---

## RPC Methods

- `browser.navigate` — `{ "url": "https://example.com" }`
- `ping` — `{ "echo": "value" }`
- `mcp.shutdown` — No params.

You can add more handlers in `venice/bridge.py` under the `dispatch()` method.

---

## Makefile Targets

- `make install`: Installs project dependencies and the Playwright browser.
- `make run-line`: Runs the bridge in line-framing mode.
- `make run-cl`: Runs the bridge in content-length framing mode.
- `make test-line`: Runs the example host for line mode.
- `make test-cl`: Runs the example host for content-length mode.
- `make test`: Runs the automated test suite with `pytest`.
- `make coverage`: Runs tests and generates a coverage report.
- `make clean`: Removes caches and build artifacts.

---

## Testing

This project includes a comprehensive test suite using `pytest`.

To run the tests:
```bash
# 1) Install development dependencies
pip install -e ".[dev]"

# 2) Run the test suite
make test
```

---

## “Stuck here?” Troubleshooting Lanes

### 1) `json.decoder.JSONDecodeError: Extra data`
**Cause:** You leaked a non-JSON line to stdout (e.g., prints, warnings from other tools).  
**Fix:** Ensure all diagnostics go to **stderr**. In Python: `print(\"dbg\", file=sys.stderr, flush=True)`.

### 2) `Expecting value: line 1 column 1 (char 0)`
**Cause:** Host expected a JSON line but got empty/garbage, usually because the child process printed banners to stdout **before** the JSON.  
**Fix:** Same as above; keep stdout pure protocol. Also verify your **framing modes match** (host vs bridge).

### 3) `playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist`
**Cause:** You forgot to install browsers.  
**Fix:** `playwright install chromium` (or `firefox` / `webkit` if you changed `BROWSER`).