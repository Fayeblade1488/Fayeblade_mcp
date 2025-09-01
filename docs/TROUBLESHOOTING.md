# Troubleshooting & Gotchas

## Protocol corruption
- Never print banners or logs to stdout. Use stderr only.
- Third-party tools (e.g., CLIs) sometimes print advice on startup; keep them out of the bridge process.

## Framing mismatch
- Host is in `content-length` mode but bridge in `line` mode (or vice versa). You'll see JSON parse errors. Align `MCP_FRAMING` on both ends.

## Asyncio edge cases
- Avoid constructing `StreamWriter(sys.stdout, ...)`. It requires a compatible protocol implementing `_drain_helper` and tends to break on TTYs. The custom writer here removes that dependency.

## Playwright
- Install browsers with `playwright install chromium`.
- For persistent login, run once with `HEADLESS=false` to capture `state.json`.
- Some sites block headless; try `HEADLESS=false` for initial auth.

## When in doubt
- Run `make test-line` first. It spawns the bridge with pipe-based IO under the simple line protocol.
- If corporate proxy or security software interferes, try running from a clean local shell, then integrate into your host.
