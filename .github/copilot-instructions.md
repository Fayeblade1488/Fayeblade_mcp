# Copilot Instructions — Venice Browser MCP Bridge

This document defines the precise operational guardrails for GitHub Copilot (or any LLM-based assistant) when interacting with this repository.

## 1. Purpose of This Repo
	•	This repo implements a Browser MCP Bridge that connects Venice.ai (or any MCP-capable host) to a Chromium browser via Playwright.
	•	Core features:
	•	Framing modes: line (newline JSON) or content-length (hard MCP).
	•	Persistence: optional browser session persistence with storage_state (cookies, localStorage).
	•	Methods: browser.navigate, browser.screenshot, browser.query.

Copilot must not hallucinate features beyond these.

⸻

## 2. File Boundaries

Copilot must strictly respect file roles:
	•	src/venice_browser_mcp_v23_impl.py → Full v2.3 implementation. Do not duplicate functionality here. Only modify if explicitly instructed.
	•	src/venice_browser_mcp_core.py → Minimal adapter; only ever call run_main() from v23 impl. Do not add extra logic.
	•	src/venice_browser_mcp.py → CLI wrapper. Allowed to set env vars and call into core. Do not inline the v23 logic here.
	•	examples/ → Minimal toy hosts only. Do not add production logic here.
	•	docs/ARCHITECTURE.md → Architectural overview. Copilot should not drift into API tutorials or usage duplication already in README.md.
	•	README.md → Authoritative source for installation, usage, troubleshooting. Copilot must check this before suggesting usage patterns.

⸻

## 3. Code Style Rules
	•	Language: Python 3.9+ only.
	•	Asynchronous style: always use async/await with Playwright. Do not introduce sync Playwright calls.
	•	Logging: prefer writing to stderr for debugging; never pollute stdout (reserved for MCP messages).
	•	Encoding: all messages are UTF-8 JSON. Copilot must never suggest mixing bytes vs str without explicit .encode()/.decode().
	•	Dependencies: limited to playwright. Do not suggest external libraries for framing or JSON-RPC.

⸻

## 4. Behavior Rules
	•	Framing:
	•	If MCP_FRAMING=line, messages are one JSON object per line.
	•	If MCP_FRAMING=content-length, messages must have exact Content-Length: N\r\n\r\n headers with N = byte length of JSON body.
	•	Persistence:
	•	If MCP_PERSIST_CONTEXT=1, reuse a single BrowserContext and load/save storage state.
	•	Never create multiple persistent contexts.
	•	Storage is always JSON at the path given by MCP_STORAGE_STATE.
	•	Methods contract:
	•	browser.navigate: returns text/html (truncated if > MAX_CONTENT_CHARS), links, meta.
	•	browser.screenshot: returns base64 PNG. Must fail gracefully if > MAX_BASE64_BYTES.
	•	browser.query: returns node text or HTML.
	•	Error handling:
	•	Always return JSON-RPC error envelopes (id, error.code, error.message, optional error.data).
	•	Never crash with raw Python exceptions on stdout.

⸻

## 5. What Copilot Must Avoid
	•	Do not alter the JSON-RPC schema.
	•	Do not replace framing logic with alternative protocols.
	•	Do not introduce non-Playwright browsers or engines unless explicitly asked.
	•	Do not propose unsafe persistence (like saving cookies to git).
	•	Do not touch .gitignore, LICENSE, or requirements.txt unless explicitly requested.

⸻

## 6. Troubleshooting Guidance

Copilot should surface solutions from the README first. Key fixes:
	•	playwright install chromium → if binaries missing.
	•	Switch to --headless 0 → for debugging.
	•	Adjust --nav-timeout-ms or --sel-timeout-ms → for slow sites.
	•	Add --user-agent → if blocked by bot filters.
	•	Use --persist with --storage → to survive login flows.

If Copilot sees errors like Parse/Framing error, it must check framing alignment.
If Copilot sees PlaywrightError, it must suggest timeouts, headless mode, or persistence toggles.

⸻

## 7. Integration Guardrails

When writing host examples (in examples/):
	•	LINE host must flush() after each write.
	•	HARD-MCP host must calculate Content-Length correctly.
	•	Hosts must never print logs to stdout — only JSON.

⸻

## 8. Authority Hierarchy

When Copilot is unsure:
	1.	Check README.md.
	2.	Check docs/ARCHITECTURE.md.
	3.	If still ambiguous, do nothing (don’t invent behavior).

⸻

## 9. Golden Rule

Copilot must always preserve the contract stability:
	•	JSON-RPC envelopes.
	•	Framing modes.
	•	Playwright-backed persistent browser context.

Breaking any of these breaks interoperability.

⸻
