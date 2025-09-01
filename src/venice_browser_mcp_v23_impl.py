import sys
import os
import json
import asyncio
from typing import Any, Dict, Optional, Tuple

# -----------------------------
# Low-noise stderr logging
# -----------------------------
def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# -----------------------------
# Safe async stdout writer
# -----------------------------
class _AsyncStdoutWriter:
    """
    Minimal writer interface for framers:
      - write(bytes|str)
      - await drain()

    Buffers into memory and flushes atomically to stdout (prefers binary buffer).
    Keeps stdout protocol-pure; do not log to stdout.
    """
    def __init__(self, stream):
        self._stream = stream
        self._buf = bytearray()
        self._lock = asyncio.Lock()

    def write(self, data):
        if isinstance(data, (bytes, bytearray)):
            self._buf.extend(data)
        else:
            self._buf.extend(str(data).encode('utf-8', 'replace'))

    async def drain(self):
        async with self._lock:
            if not self._buf:
                return
            b = bytes(self._buf)
            self._buf.clear()
            if hasattr(self._stream, "buffer"):
                self._stream.buffer.write(b)
            else:
                # Fallback (rare on modern Python)
                self._stream.write(b.decode('utf-8', 'replace'))
            self._stream.flush()

# -----------------------------
# Framers
# -----------------------------
class LineFramer:
    def __init__(self, reader: asyncio.StreamReader, writer: _AsyncStdoutWriter):
        self.reader = reader
        self.writer = writer

    async def read_message(self) -> Optional[Dict[str, Any]]:
        line = await self.reader.readline()
        if not line:
            return None
        line = line.decode('utf-8', 'replace').strip()
        if not line:
            return None
        return json.loads(line)

    async def write_message(self, obj: Dict[str, Any]) -> None:
        data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n"
        self.writer.write(data)
        await self.writer.drain()

class ContentLengthFramer:
    def __init__(self, reader: asyncio.StreamReader, writer: _AsyncStdoutWriter):
        self.reader = reader
        self.writer = writer

    async def read_message(self) -> Optional[Dict[str, Any]]:
        # Read headers
        content_length = None
        while True:
            line = await self.reader.readline()
            if not line:
                return None
            line = line.decode('utf-8', 'replace').strip()
            if line == "":
                break
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    raise RuntimeError("Invalid Content-Length header")

        if content_length is None:
            raise RuntimeError("Missing Content-Length header")

        body = await self.reader.readexactly(content_length)
        return json.loads(body.decode('utf-8', 'replace'))

    async def write_message(self, obj: Dict[str, Any]) -> None:
        body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode('utf-8')
        headers = f"Content-Length: {len(body)}\r\n\r\n".encode('ascii')
        self.writer.write(headers + body)
        await self.writer.drain()

# -----------------------------
# Browser (Playwright)
# -----------------------------
class BrowserEnv:
    def __init__(self, headless: bool, storage_state: str, nav_timeout_ms: int, browser_name: str):
        self.headless = headless
        self.storage_state = storage_state
        self.nav_timeout_ms = nav_timeout_ms
        self.browser_name = browser_name
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    async def ensure(self):
        if self._pw is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except Exception as e:
            raise RuntimeError("Playwright is not installed. Run 'pip install -r requirements.txt' and 'playwright install chromium'.") from e
        self._pw = await async_playwright().start()
        launcher = getattr(self._pw, self.browser_name, None)
        if launcher is None:
            raise RuntimeError(f"Unsupported browser '{self.browser_name}'. Use 'chromium', 'firefox', or 'webkit'.")
        self._browser = await launcher.launch(headless=self.headless)
        state = self.storage_state if self.storage_state else None
        self._context = await self._browser.new_context(storage_state=state if os.path.exists(state) else None)
        self._context.set_default_timeout(self.nav_timeout_ms)
        self._page = await self._context.new_page()

    async def close(self):
        try:
            if self._context:
                # Save state if a path is provided
                if self.storage_state:
                    try:
                        await self._context.storage_state(path=self.storage_state)
                    except Exception:
                        pass
            if self._browser:
                await self._browser.close()
        finally:
            if self._pw:
                await self._pw.stop()
        self._pw = self._browser = self._context = self._page = None

    async def navigate(self, url: str) -> Dict[str, Any]:
        await self.ensure()
        assert self._page is not None
        resp = await self._page.goto(url, wait_until="load", timeout=self.nav_timeout_ms)
        # Pull final URL/title regardless of response being None (file or about pages)
        final_url = self._page.url
        title = await self._page.title()
        ok = True
        status = None
        if resp:
            try:
                status = resp.status
                ok = 200 <= status < 400
            except Exception:
                pass
        return {"ok": bool(ok), "status": status, "final_url": final_url, "title": title}

# -----------------------------
# Dispatcher
# -----------------------------
class Dispatcher:
    def __init__(self, browser_env: BrowserEnv):
        self.browser = browser_env

    async def dispatch(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "ping":
            return {"echo": params.get("echo")}
        if method == "mcp.shutdown":
            await self.browser.close()
            # Signal the outer loop to stop by raising a sentinel
            raise _Shutdown()
        if method == "browser.navigate":
            url = params.get("url")
            if not url or not isinstance(url, str):
                raise ValueError("browser.navigate requires a string 'url'")
            return await self.browser.navigate(url)
        raise ValueError(f"Unknown method: {method}")

class _Shutdown(Exception):
    pass

# -----------------------------
# Main loop
# -----------------------------
async def run_main(*, framing: str, headless: bool, storage_state: str, nav_timeout_ms: int, browser_name: str):
    loop = asyncio.get_running_loop()

    # stdin reader (binary)
    reader = asyncio.StreamReader()
    rproto = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: rproto, sys.stdin)

    # stdout writer (safe)
    writer = _AsyncStdoutWriter(sys.stdout)

    if framing == "content-length":
        framer = ContentLengthFramer(reader, writer)
    else:
        framer = LineFramer(reader, writer)

    browser_env = BrowserEnv(headless=headless, storage_state=storage_state, nav_timeout_ms=nav_timeout_ms, browser_name=browser_name)
    dispatcher = Dispatcher(browser_env)

    async def handle_one(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mid = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}
        try:
            result = await dispatcher.dispatch(method, params)
            return {"jsonrpc": "2.0", "id": mid, "result": result}
        except _Shutdown:
            return {"jsonrpc": "2.0", "id": mid, "result": {"ok": True, "shutdown": True}}
        except Exception as e:
            # return an error object; still avoid stdout noise
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}}

    try:
        while True:
            msg = await framer.read_message()
            if msg is None:
                break
            resp = await handle_one(msg)
            if resp is not None:
                await framer.write_message(resp)
            # If shutdown was requested, exit after replying
            if resp and isinstance(resp.get("result"), dict) and resp["result"].get("shutdown"):
                break
    finally:
        try:
            await browser_env.close()
        except Exception:
            pass
