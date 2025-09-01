# Architecture

The bridge is a single asyncio process that wires a **Framer** to a **Dispatcher**:

```
stdin --[Framer]--> JSON msg --> Dispatcher --> Handler --> result --> [Framer] --> stdout
```

## Framers

- **LineFramer**: newline-delimited JSON. Reads a line, `json.loads`, writes `json.dumps` + `\n`.
- **ContentLengthFramer**: reads HTTP-ish headers (`Content-Length: N`), then reads exactly `N` bytes, parses JSON; writes symmetric headers and body.

Both expect a `writer` that provides:
- `write(bytes|str)`
- `await drain()`

We use a custom writer that accumulates bytes into a buffer and flushes **atomically** to stdout (preferring the binary buffer). This sidesteps fragile `asyncio` `StreamWriter` plumbing across different STDIO types.

## Dispatcher

Maps `method` to async handlers. Included:

- `browser.navigate(params)` → launches or reuses a singleton browser/page and navigates.
- `ping(params)`
- `mcp.shutdown(params)`

## Browser Lifecycle

- Launch once on first call.
- Reuse a **single context** (optionally persistent via `storage_state`). 
- Reuse a **single page** for simplicity. Extend to tab-per-request if needed.
