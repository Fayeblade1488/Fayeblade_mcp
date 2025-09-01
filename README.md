# Venice Browser MCP Bridge
<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/81bae856-9692-4b48-98a9-c8bd213935a7" />


A tiny, production-minded **browser bridge** that speaks a JSON-RPC-ish protocol over **stdin/stdout**. 
It supports two transport framers out of the box:

- `line` — one JSON message per line (default). Simple, friendly, great for prototyping.
- `content-length` — HTTP-like `Content-Length: N` framed messages. Good for strict MCP hosts.

It uses **Playwright** for real browser automation with a single persistent context (optional cookie/session state).

This repo is hardened against the classic `asyncio.StreamWriter(sys.stdout, ...)` footgun by using a robust writer 
implementation that **never logs to stdout**, avoids protocol mismatches, and cleanly flushes per message.

---

## Quick Start

```bash
# 1) Create an isolated env (recommended)
python3 -m venv .venv && source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt
playwright install chromium

# 3) Run the bridge (line framing by default)
make run-line

# In another terminal, run the example host:
make test-line
```

Expect output like:

```
Navigate...
{"id":"nav-1","result":{"ok":true,"final_url":"https://example.com/","title":"Example Domain"}}
```

To exercise **Content-Length** framing:

```bash
make run-cl    # terminal A
make test-cl   # terminal B
```

---

## Repo Layout

```
venice-browser-mcp/
├─ src/
│  ├─ venice_browser_mcp.py             # entrypoint
│  ├─ venice_browser_mcp_core.py        # env plumbing
│  └─ venice_browser_mcp_v23_impl.py    # framing + browser logic (patched)
├─ examples/
│  ├─ line_host.py                      # spawns bridge (line) and sends a request
│  └─ hard_mcp_host.py                  # spawns bridge (content-length) and sends a request
├─ docs/
│  ├─ ARCHITECTURE.md
│  └─ TROUBLESHOOTING.md
├─ Makefile
├─ requirements.txt
├─ .gitignore
├─ LICENSE
└─ README.md
```

---

## Configuration

The bridge is configured via environment variables. Reasonable defaults chosen for newbies.

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
  Opens/uses a single page, navigates, returns `{ ok, status, final_url, title }`.

- `ping` — `{ "echo": "value" }`  
  Returns `{ "echo": "value" }` for quick checks.

- `mcp.shutdown` — No params.  
  Gracefully closes browser & exits main loop.

You can add more handlers in `venice_browser_mcp_v23_impl.py` under `dispatch()`.

---

## Makefile Targets

- `make install` — install Python deps and Playwright browser
- `make run-line` — run bridge in line mode (foreground)
- `make run-cl` — run bridge in content-length mode (foreground)
- `make test-line` — run example host for line mode
- `make test-cl` — run example host for content-length mode
- `make fmt` — basic Python formatting (via `python -m json.tool` checks and whitespace cleanup)
- `make clean` — remove caches/artifacts

---

## “Stuck here?” Troubleshooting Lanes

### 1) Crash: `AssertionError` or `'Protocol' object has no attribute '_drain_helper'`
**Cause:** Incorrect `asyncio.StreamWriter` construction (classic pitfall).  
**Fix:** This repo **does not** use that pattern; it uses a safe writer. Ensure you are running **these** sources and not an unpatched file. Reinstall with `git clean -xfd` or re-extract the zip.

### 2) `json.decoder.JSONDecodeError: Extra data`
**Cause:** You leaked a non-JSON line to stdout (e.g., prints, warnings from other tools).  
**Fix:** Ensure all diagnostics go to **stderr**. In Python: `print(\"dbg\", file=sys.stderr, flush=True)`.

### 3) `Expecting value: line 1 column 1 (char 0)`
**Cause:** Host expected a JSON line but got empty/garbage, usually because the child process printed banners to stdout **before** the JSON.  
**Fix:** Same as above; keep stdout pure protocol. Also verify your **framing modes match** (host vs bridge).

### 4) `playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist`
**Cause:** You forgot to install browsers.  
**Fix:** `playwright install chromium` (or `firefox` / `webkit` if you changed `BROWSER`).

### 5) Headless works, but you need cookie persistence / “logged-in” state
- Set `MCP_STORAGE_STATE=state.json` (default already).
- Log in once with `HEADLESS=false`, then close. Subsequent sessions reuse that state.

### 6) Corporate proxy, weird TTY, or PTY quirks
If the host uses a PTY or non-pipe stdout, line-buffering can glitch. Prefer the included **example hosts** which spawn the bridge with a **pipe** and communicate cleanly.

---

## Security Notes

- This project is a **tooling bridge**. It does not bypass web/app authentication, nor does it ship exploit logic. 
- If you extend it, keep logs on stderr, and sanitize inputs when invoking shell or navigating to user-provided URLs.
- For red-team experiments: keep it abstracted and non-operational; do not automate harmful behaviors.

---

## Sanity Checks

- Both framers verified with the included hosts.
- No stdout logging, atomic flush per message.
- Single Playwright context reused across calls, optional persistence enabled.
- Explicit timeouts on navigation.
